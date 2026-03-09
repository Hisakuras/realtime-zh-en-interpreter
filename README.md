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
git clone https://github.com/YOUR_USERNAME/simul-interpreter.git
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
