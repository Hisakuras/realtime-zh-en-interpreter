import os
# 避免部分 OpenMP / MKL 重复加载的警告
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import os
import tempfile
import time
import threading
import queue
import io

from flask import Flask, Response, render_template_string

import numpy as np
import sounddevice as sd
import soundfile as sf

from faster_whisper import WhisperModel
from openai import OpenAI

# -------------------- 配置区 --------------------
RATE = 16000
CHUNK = 1024
SLICE_SECONDS = 0.7       # 每段音频长度，想更低延迟可试 0.5
LATENCY_MODE = "low"       # 想更低延迟可试 "fast"，视声卡稳定性而定

ASR_MODEL_SIZE = "small"   # faster-whisper 模型大小: tiny/base/small/medium/large-v3

# OpenAI 配置（从环境变量读取）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.1")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")

if not OPENAI_API_KEY:
    raise RuntimeError("请先设置环境变量 OPENAI_API_KEY 再运行脚本。")

# -------------------- 队列 --------------------
audio_queue = queue.Queue(maxsize=50)
subtitle_queue_obs = queue.Queue(maxsize=50)
subtitle_queue_tk = queue.Queue(maxsize=50)
tts_audio_queue = queue.Queue(maxsize=50)
last_chinese = None

# -------------------- 初始化 ASR（faster-whisper） --------------------
print(f"加载 faster-whisper 模型: {ASR_MODEL_SIZE}")
whisper_model = WhisperModel(
    ASR_MODEL_SIZE,
    device="cpu",      # 有 GPU 可改 "cuda"
    compute_type="int8"
)


def asr_infer(chunk_bytes: bytes) -> str:
    """
    使用 faster-whisper 做中文识别
    """
    audio = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(
        audio,
        language="zh",
        beam_size=5,
        vad_filter=True,
    )
   texts = [seg.text for seg in segments]
    text = "".join(texts).strip()
    return text


# -------------------- 初始化 OpenAI 客户端 --------------------
print("初始化 OpenAI 客户端...")
llm_client = OpenAI(   
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
)

       
def translate_zh2en(text: str) -> str:
    """
    使用 OpenAI Chat 模型把中文翻译成英文
    """
    if not text.strip():
        return ""
    try:
        resp = llm_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional simultaneous interpreter. "
                        "Translate Chinese into natural, fluent spoken English, "
                        "short and concise, suitable for live speech. "
                        "Do not explain, do not add comments. Only output the translation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        en = resp.choices[0].message.content.strip()
        return en
    except Exception as e:
        print("翻译 API 错误：", e)
        return ""
    
        
def tts_play_openai(text: str):
    """
   使用 OpenAI TTS 播放英文语音
    """
    if not text.strip():
        return
    temp_path = None
    try:
       # 1. 创建临时文件 (.wav 格式兼容性最好)
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)  # 关闭文件句柄，让 openai 库接管写入
                
        # 2. 调用 API 并直接流式写入文件
        # [关键修改]
        # - 移除了 .with_raw_response (这就是报错根源)
        # - 使用了 .stream_to_file() (新版 SDK 推荐，稳定且省内存)
        with llm_client.audio.speech.with_streaming_response.create(
            model=OPENAI_TTS_MODEL,
            voice="alloy",
            input=text,
            response_format="wav",
        ) as response:
            # 在 with 块内部调用 stream_to_file
            response.stream_to_file(temp_path)
   
       
        # 3. 从文件读取音频数据
        data, sr = sf.read(temp_path)
    
        # 4. 播放音频
        sd.play(data, sr)
        sd.wait()
        
    except Exception as e:
        print("OpenAI TTS 错误：", e)
        import traceback
        traceback.print_exc()
        
    finally:
        # 5. 清理临时文件，防止磁盘占满
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
            
    
# -------------------- 录音线程（sounddevice） --------------------
def record_thread():
    print(f"录音线程已启动 (Rate={RATE}, Chunk={CHUNK}, Latency={LATENCY_MODE})")
    
    with sd.RawInputStream(
        samplerate=RATE, 
        blocksize=CHUNK,
        dtype="int16",
        channels=1,
        latency=LATENCY_MODE,
    ) as stream:
        while True:
            try:
                # stream.read() 返回 (data, overflow_flag)
                data, _ = stream.read(CHUNK)
                if not isinstance(data, np.ndarray):
                    data = np.frombuffer(data, dtype=np.int16)
                
                chunk_bytes = data.tobytes()
                
                try:
                    audio_queue.put_nowait(chunk_bytes)
                except queue.Full:
                    # 队列满时丢弃最旧数据
                    _ = audio_queue.get_nowait()
                    audio_queue.put_nowait(chunk_bytes)
            except Exception as e:
                print("录音异常：", e)
                time.sleep(0.1)
        
        
# -------------------- ASR + 翻译线程 --------------------
def translation_thread():
    global last_chinese
    buffer = b""
    # int16 每个样本 2 字节
    slice_size = int(RATE * 2 * SLICE_SECONDS)
    overlap_bytes = int(RATE * 2 * 0.2)
                    
    print("ASR/翻译线程已启动")
    while True:
        byte_chunk = audio_queue.get()
        buffer += byte_chunk
                    
        if len(buffer) >= slice_size:
            try:
                chinese = asr_infer(buffer)
            except Exception as e:
                print("ASR 错误：", e)
                buffer = b""
                continue
        
            # 保留重叠部分，减少句子被截断
            if len(buffer) > overlap_bytes:
                buffer = buffer[-overlap_bytes:]
            else:
                buffer = b""
    
            chinese = (chinese or "").strip() 
            if not chinese:
                continue
            if chinese == last_chinese:
                continue
            last_chinese = chinese
        

        
            english = translate_zh2en(chinese)
            if not english:
                continue
                
            # 分发到各个队列
            for q in (subtitle_queue_obs, subtitle_queue_tk, tts_audio_queue):
                try:
                    q.put_nowait(english)
                except queue.Full:
                    try:
                        _ = q.get_nowait() 
                        q.put_nowait(english)   
                    except queue.Empty:
                        pass
    
            
# -------------------- TTS 播放线程 --------------------
def tts_producer_consumer():
    print("TTS 线程已启动（OpenAI TTS）")
    while True:
        text = tts_audio_queue.get()
        if not text:
            continue
        tts_play_openai(text)
                
                
# -------------------- Flask + OBS Overlay --------------------
app = Flask(__name__)
                
OVERLAY_HTML = r"""
<!doctype html>
<html>
 <head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
   html,body { margin:0; padding:0; background: transparent; }
   .subtitle {
     font-family: Arial, Helvetica, sans-serif;
     font-size: 36px;
     color: white;
     text-shadow: 2px 2px 4px rgba(0,0,0,0.7);
     padding: 10px;
   }
 </style>
 </head>
 <body>         
  <div id="box" class="subtitle"></div>
  <script>
   var evtSource = new EventSource('/stream');
   evtSource.onmessage = function(e) {
     document.getElementById('box').innerText = e.data;
   }
  </script>
 </body>
</html>
"""
  
   
@app.route("/overlay")
def overlay_page():
    return render_template_string(OVERLAY_HTML)
     
     
@app.route("/stream")
def sse_stream():
    def event_stream():
        while True:
            try:
                text = subtitle_queue_obs.get()
                yield f"data: {text}\n\n"
            except GeneratorExit:
                break
            except Exception as e:
                print("SSE 异常：", e)
                time.sleep(0.1)
 
    return Response(event_stream(), mimetype="text/event-stream")
   
  
# -------------------- Tk 字幕窗口 --------------------
try:
    import tkinter as tk
    
    USE_TK = True
except Exception:
    USE_TK = False   
    
def tk_thread():   
    if not USE_TK:
        return
                
    root = tk.Tk()
    root.title("同声传译 — 实时字幕")
    root.geometry("800x120")
    label = tk.Label(root, text="", font=("Arial", 28), bg="black", fg="white")
    label.pack(fill="both", expand=True)
 
    def poll():
        try:
            while not subtitle_queue_tk.empty():
                txt = subtitle_queue_tk.get_nowait()
                label.config(text=txt)
        except Exception:
            pass
        root.after(100, poll)

    root.after(100, poll)
    root.mainloop()
   

# -------------------- 启动入口 --------------------
if __name__ == "__main__":
    # 启动线程
    threading.Thread(target=record_thread, daemon=True).start()
    threading.Thread(target=translation_thread, daemon=True).start()
    threading.Thread(target=tts_producer_consumer, daemon=True).start()
    if USE_TK:
        threading.Thread(target=tk_thread, daemon=True).start()
 
    print("服务启动：")
    print(" - OBS Overlay:  http://localhost:5000/overlay")
    print(" - OpenAI Chat 模型:", OPENAI_CHAT_MODEL)
    print(" - OpenAI TTS 模型:", OPENAI_TTS_MODEL)
    print(f" - 录音延迟模式: {LATENCY_MODE}")
    print(f" - 切片长度: {SLICE_SECONDS}s")
            
    app.run(host="0.0.0.0", port=5000, threaded=True)

    
    
