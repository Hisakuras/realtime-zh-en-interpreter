# realtime-zh-en-interpreter
Real-time Chinese speech → English speech interpreter using Whisper + LLM + TTS

# 🎙️ Simul-Interpreter: Real-time AI Live Translator for OBS

> **专为直播设计的实时同声传译工具**。将中文直播实时翻译成英文字幕和语音，无缝集成 OBS，低延迟，高可用。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-green.svg)](https://platform.openai.com/)

## ✨ 核心特性

- 🚀 **超低延迟流式处理**：采用切片缓冲机制 (默认 0.7s)，实现近乎实时的听译体验。
- 🌏 **中译英专用优化**：针对中文直播场景优化，自动识别语音并翻译为流畅英文。
- 🔊 **双向输出**：
  - **视觉**：提供本地 HTTP 服务 (`/overlay`)，生成精美的字幕页面，可直接作为 **OBS 浏览器源**。
  - **听觉**：集成 OpenAI TTS，实时朗读翻译结果。
- 🧠 **强大内核**：
  - **ASR**: 本地运行 `faster-whisper` (Small 模型)，保护隐私且速度快。
  - **LLM**: 调用 OpenAI GPT-4o/GPT-5.1 进行高质量上下文翻译。
  - **TTS**: OpenAI 原生语音合成，声音自然逼真。
- 🛠️ **易于扩展**：纯 Python 实现，架构清晰，欢迎贡献者加入优化。

## 🎯 应用场景

- **游戏直播**：中文主播玩单机游戏，实时翻译剧情和对话给海外观众。
- **技术分享**：中文技术会议/教程，实时生成英文字幕。
- **跨国会议**：辅助理解英文内容或输出中文观点。

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保你的系统已安装：
- **Python 3.9+**
- **FFmpeg** (音频处理必备)
  - **macOS**: `brew install ffmpeg`
  - **Windows**: 下载二进制包并添加到 PATH
  - **Linux**: `sudo apt-get install ffmpeg`

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/hisakuras/simul-interpreter.git
cd simul-interpreter

# 创建虚拟环境
python3 -m venv venv

# 激活环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt


# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 OpenAI API Key
# macOS/Linux 使用 nano 或 vim:
nano .env
# Windows 使用记事本打开 .env 编辑
⚠️ 注意：请确保 .env 文件中 OPENAI_API_KEY 已正确填写，否则程序无法启动。

python simul_interpreter_openai.py
启动成功后，终端会显示：
OBS Overlay: http://localhost:5000/overlay
Stream Data: http://localhost:5000/stream

5. 集成 OBS (关键步骤)
打开 OBS Studio。
在“来源”面板点击 +，选择 浏览器 (Browser)。
名称设为 Live Translation。
在 URL 栏输入：http://localhost:5000/overlay
设置宽度 (Width): 1920, 高度 (Height): 1080 (根据你的分辨率调整)。
勾选 控制音频 (Control audio via OBS) (如果你需要听到 TTS 声音通过推流流出)。
点击确定，将字幕层拖动到画面底部。
现在，对着麦克风说中文，你将看到实时英文字幕出现在 OBS 中！

🏗️ 技术架构
Audio Input: SoundDevice (低延迟录音, 16kHz)
ASR: Faster-Whisper (Local GPU/CPU inference)
Translation: OpenAI Chat Completions API (Streaming)
TTS: OpenAI Audio API
Frontend: Simple HTML/JS served by Flask

🤝 贡献指南 (Contributing)
本项目处于早期阶段，非常需要社区大神的帮助！以下方向急需优化：
性能优化：进一步降低端到端延迟 (目前 ~1.5s)。
多语言支持：不仅限于中译英，支持更多语言对。
说话人区分：集成 Speaker Diarization，区分主播和嘉宾。
GUI 界面：开发一个简单的配置界面，替代修改 .env 文件。
Windows 兼容：完善 Windows 下的音频驱动兼容性测试。

如何贡献：
Fork 本仓库。
创建你的特性分支 (git checkout -b feature/AmazingFeature)。
提交更改 (git commit -m 'Add some AmazingFeature')。
推送到分支 (git push origin feature/AmazingFeature)。
开启 Pull Request。
⚠️ 注意事项
API 费用：本项目调用 OpenAI 收费接口，请注意控制 Token 用量。
网络环境：确保你的网络可以稳定访问 OpenAI API。
麦克风权限：首次运行时请允许终端/Python 访问麦克风。
📄 许可证
本项目采用 MIT License 开源。
🙏 致谢
OpenAI 提供的强大模型。
faster-whisper 团队的高效推理引擎。
所有为此项目做出贡献的开发者。
Made with ❤️ for streamers and content creators.

---

### 🛠️ 最后一步：检查主代码 (`simul_interpreter_openai.py`)

为了确保别人下载后能直接跑（读取 `.env` 文件），请检查你的 `simul_interpreter_openai.py` 文件头部是否包含以下代码。如果没有，请**替换或添加**到文件最开头：

```python
import os
import sys
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# --- 配置读取部分 (替换你原来硬编码的部分) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ 错误：未在 .env 文件中找到 OPENAI_API_KEY。")
    print("   请执行: cp .env.example .env 并填入你的密钥。")
    sys.exit(1)

# 从环境变量获取，如果没有则使用默认值
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# ... 下面保持你原有的代码逻辑不变 ...
# 初始化客户端时使用变量
from openai import OpenAI
llm_client = OpenAI(api_key=OPENAI_API_KEY)

🚀 立即执行上传
做完以上所有“复制粘贴”后，在终端执行以下命令即可完成上传：
# 1. 添加所有新文件
git add .

# 2. 检查状态 (确认没有 .env 文件被添加)
git status

# 3. 提交
git commit -m "Feat: Complete open source release with docs and config templates"

# 4. 推送 (如果还没关联远程仓库，请先运行 git remote add origin ...)
git push


