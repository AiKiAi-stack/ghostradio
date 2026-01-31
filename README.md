# GhostRadio

> **平时"装死"，只在有任务时"诈尸"** - 极致省资源的 AI 播客生成器

GhostRadio 是一个为低配置 VPS 设计的播客生成系统。它采用 Serverless-like 架构，平时不占用内存，只在处理任务时启动，完成后立即释放资源。

## 特性

- 🎯 **极致省资源** - 待机时内存占用 < 15MB，工作时 150-300MB
- 🤖 **AI 驱动** - 使用 LLM 自动将文章转换为播客脚本
- 🔊 **多 TTS 支持** - 支持 OpenAI、Azure、Edge-TTS 等多种语音合成服务
- 📱 **标准播客格式** - 生成 RSS Feed，支持任何播客客户端订阅
- ⚙️ **模型中立** - 兼容所有 OpenAI 格式的 API（OpenAI、DeepSeek、Claude 等）
- 🐳 **零常驻进程** - 基于 Cron 调度，无后台服务

## 系统要求

- Python 3.8+
- 1C 1G VPS（最低配置）
- Linux/macOS（Windows 需要 WSL）
- 可选：FFmpeg（用于音频格式转换）

## 快速开始

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd ghostradio
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

复制配置文件模板：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 API 密钥和其他配置：

```yaml
llm:
  provider: "deepseek"
  base_url: "https://api.deepseek.com/v1"
  api_key_env: "LLM_API_KEY"  # 从环境变量读取
  model_name: "deepseek-chat"

tts:
  provider: "openai"
  api_key_env: "TTS_API_KEY"
  voice: "alloy"

podcast:
  title: "我的播客"
  base_url: "https://your-domain.com/podcast"
```

设置环境变量：

```bash
export LLM_API_KEY="your-llm-api-key"
export TTS_API_KEY="your-tts-api-key"
```

### 4. 启动触发器服务器

```bash
python src/server.py
```

服务器将在 `http://localhost:8080` 启动。

### 5. 配置调度器

编辑 crontab：

```bash
crontab -e
```

添加以下行（每 5 分钟检查一次队列）：

```bash
*/5 * * * * cd /path/to/ghostradio && python src/scheduler.py >> logs/cron.log 2>&1
```

### 6. 提交 URL

使用 curl 或任何 HTTP 客户端提交要转换的文章 URL：

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

调度器会在下次运行时自动处理队列中的 URL。

## 项目结构

```
ghostradio/
├── src/
│   ├── server.py          # Webhook 接收器（触发器）
│   ├── worker.py          # 核心处理脚本
│   ├── scheduler.py       # 调度脚本
│   ├── config.py          # 配置管理
│   ├── content_fetcher.py # URL 内容获取
│   ├── llm_processor.py   # LLM 内容处理
│   ├── tts_generator.py   # TTS 音频生成
│   ├── file_manager.py    # 文件生命周期管理
│   └── rss_generator.py   # RSS Feed 生成
├── prompts/
│   └── podcast_host.txt   # 播客主持人提示词
├── episodes/              # 生成的音频文件
├── logs/                  # 日志文件
├── config.example.yaml    # 配置模板
├── requirements.txt       # Python 依赖
└── README.md             # 本文件
```

## 配置说明

### LLM 配置

支持所有 OpenAI 格式的 API：

```yaml
llm:
  provider: "custom"
  base_url: "https://api.deepseek.com/v1"  # 或 OpenAI、Azure 等
  api_key_env: "LLM_API_KEY"
  model_name: "deepseek-chat"
  context_window: 16000
  temperature: 0.7
  prompt_file: "prompts/podcast_host.txt"
```

### TTS 配置

支持多种 TTS 提供商：

```yaml
tts:
  provider: "openai"  # 或 "azure", "edge-tts"
  api_key_env: "TTS_API_KEY"
  voice: "alloy"      # OpenAI: alloy, echo, fable, onyx, nova, shimmer
  speed: 1.0
```

使用 Edge-TTS（免费）：

```yaml
tts:
  provider: "edge-tts"
  voice: "zh-CN-XiaoxiaoNeural"
  speed: 1.0
```

### 资源限制

```yaml
resources:
  max_concurrent_tasks: 1    # 永远为 1，防止内存爆炸
  keep_last_n_episodes: 5    # 只保留最近 5 期
  max_disk_usage_mb: 200     # 最大磁盘使用 200MB
  audio_format: "m4a"        # 音频格式: m4a, ogg, mp3
```

## API 接口

### Webhook 接收器

- **POST** `/webhook` - 提交 URL 到处理队列
  - 请求体: `{"url": "https://example.com/article"}`
  - 响应: `{"success": true, "message": "URL added to queue"}`

- **GET** `/health` - 健康检查
  - 响应: `{"status": "ok", "service": "ghostradio-trigger"}`

## 资源占用

| 状态 | 进程 | 内存占用 | CPU |
|------|------|----------|-----|
| **待机中 (99% 时间)** | server.py | ~15MB | 0% |
| **待机中** | cron | (系统自带) | 0% |
| **工作中 (1% 时间)** | worker.py | ~150MB - 300MB | 100% (nice限制) |

## 故障排查

### 查看日志

```bash
tail -f logs/worker.log
tail -f logs/cron.log
```

### 手动运行 Worker

```bash
python src/worker.py --once
```

### 检查队列

```bash
cat queue.txt
```

### 清理旧文件

```bash
python -c "from src.file_manager import FileManager; from src.config import get_config; fm = FileManager(get_config().get_resources_config()); fm.cleanup()"
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
