# GhostRadio

> **平时"装死"，只在有任务时"诈尸"** - 极致省资源的 AI 播客生成器

GhostRadio 是一个为低配置 VPS 设计的播客生成系统。它采用 Serverless-like 架构，平时不占用内存，只在处理任务时启动，完成后立即释放资源。

## 特性

- 🎯 **极致省资源** - 待机时内存占用 < 15MB，工作时 150-300MB
- 🤖 **AI 驱动** - 使用 LLM 自动将文章转换为播客脚本
- 🔊 **多 TTS 支持** - 支持火山引擎、OpenAI、Edge-TTS 等多种语音合成服务
- 📱 **现代化 Web 界面** - 模型选择、进度跟踪、在线试听、一键下载
- ⚙️ **模型健康检查** - 自动检测模型可用性，故障自动切换
- 📡 **标准播客格式** - 生成 RSS Feed，支持任何播客客户端订阅
- 🐳 **零常驻进程** - 基于 Cron 调度，无后台服务

## 系统要求

- Python 3.8+
- 1C 1G VPS（最低配置）
- Linux/macOS（Windows 需要 WSL）
- 可选：FFmpeg（用于音频格式转换）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/AiKiAi-stack/ghostradio.git
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

编辑 `config.yaml`，填入你的 API 密钥：

```yaml
# LLM 配置 - 推荐使用 NVIDIA（免费额度高）
llm:
  provider: "nvidia"
  api_key_env: "NVIDIA_API_KEY"
  model_name: "deepseek-ai/deepseek-v3.2"
  base_url: "https://integrate.api.nvidia.com/v1"

# TTS 配置 - 推荐使用火山引擎（中文效果好）
tts:
  provider: "volcengine"
  api_key_env: "VOLCENGINE_TOKEN"
  appid_env: "VOLCENGINE_APPID"
  voice: "zh_female_xiaoxiao"

# 播客信息
podcast:
  title: "我的播客"
  base_url: "https://your-domain.com/podcast"
```

设置环境变量：

```bash
# NVIDIA API Key (推荐)
export NVIDIA_API_KEY="your-nvidia-api-key"

# 或 OpenAI API Key
export OPENAI_API_KEY="your-openai-api-key"

# 火山引擎配置
export VOLCENGINE_TOKEN="your-volcengine-token"
export VOLCENGINE_APPID="your-volcengine-appid"

# TTS API Key (如使用 OpenAI TTS)
export TTS_API_KEY="your-tts-api-key"
```

### 4. 启动服务器

```bash
python start.py server
```

服务器将在 `http://localhost:8080` 启动。

打开浏览器访问 `http://localhost:8080`，你会看到现代化的 Web 界面：
- 选择 LLM 和 TTS 模型
- 输入文章 URL
- 实时查看生成进度
- 在线试听和下载 MP3

### 5. 配置调度器（可选）

如果你希望通过 API 提交任务而不是 Web 界面：

```bash
crontab -e
```

添加以下行（每 5 分钟检查一次队列）：

```bash
*/5 * * * * cd /path/to/ghostradio && python src/scheduler.py >> logs/cron.log 2>&1
```

## 项目结构

```
ghostradio/
├── src/
│   ├── server.py              # Web 服务器和 API
│   ├── worker.py              # 核心处理脚本
│   ├── scheduler.py           # 调度脚本
│   ├── api_routes.py          # API 路由
│   ├── config.py              # 配置管理
│   ├── logger.py              # 结构化日志
│   ├── prompt_manager.py      # Prompt 管理
│   ├── content_fetcher.py     # URL 内容获取
│   ├── llm_processor.py       # LLM 内容处理
│   ├── tts_generator.py       # TTS 音频生成
│   ├── file_manager.py        # 文件生命周期管理
│   ├── file_lock.py           # 跨平台文件锁
│   ├── rss_generator.py       # RSS Feed 生成
│   ├── providers/             # LLM Providers
│   │   ├── base_provider.py
│   │   ├── nvidia_provider.py
│   │   └── openai_provider.py
│   └── tts_providers/         # TTS Providers
│       ├── base_tts_provider.py
│       ├── volcengine_provider.py
│       ├── openai_tts_provider.py
│       └── edge_tts_provider.py
├── prompts/
│   ├── prompts.yaml           # Prompt 配置文件
│   └── podcast_host.txt       # 播客主持人提示词
├── episodes/                  # 生成的音频文件
│   └── index.html             # Web 界面
├── logs/                      # 日志文件
│   ├── ghostradio.log         # 主日志
│   └── jobs/                  # 任务状态
├── config.example.yaml        # 配置模板
├── requirements.txt           # Python 依赖
├── start.py                   # 启动脚本
├── test.py                    # 测试脚本
└── README.md                  # 本文件
```

## 配置说明

### LLM 配置

支持多个 Provider，系统会自动检测可用性并切换：

```yaml
llm:
  provider: "nvidia"              # nvidia, openai
  api_key_env: "NVIDIA_API_KEY"   # 环境变量名
  model_name: "deepseek-ai/deepseek-v3.2"
  base_url: "https://integrate.api.nvidia.com/v1"
  temperature: 0.7
  max_tokens: 4096
```

备选模型（自动切换）：
- `nvidia` - NVIDIA API（推荐，免费额度高）
- `openai` - OpenAI API（GPT-4/GPT-3.5）

### TTS 配置

```yaml
tts:
  provider: "volcengine"          # volcengine, openai, edge-tts
  api_key_env: "VOLCENGINE_TOKEN"
  voice: "zh_female_xiaoxiao"     # 音色选择
  speed: 1.0                      # 语速
  volume: 1.0                     # 音量
  pitch: 1.0                      # 音调
```

备选模型（自动切换）：
- `volcengine` - 火山引擎（推荐，中文效果好）
- `openai` - OpenAI TTS
- `edge-tts` - 微软 Edge（免费，无需 API Key）

### 资源限制

```yaml
resources:
  max_concurrent_tasks: 1         # 永远为 1，防止内存爆炸
  keep_last_n_episodes: 5         # 只保留最近 5 期
  max_disk_usage_mb: 200          # 最大磁盘使用 200MB
  audio_format: "mp3"             # 音频格式
```

## API 接口

### Web 界面

访问 `http://localhost:8080` 使用现代化 Web 界面：
- 模型选择（LLM + TTS）
- URL 输入和验证
- 实时进度条
- 在线试听
- 一键下载
- 历史节目管理

### REST API

#### 创建生成任务

```bash
POST /api/generate
Content-Type: application/json

{
  "url": "https://example.com/article",
  "llm_model": "nvidia",
  "tts_model": "volcengine"
}
```

响应：
```json
{
  "success": true,
  "job_id": "a1b2c3d4",
  "status": "queued",
  "progress": 5
}
```

#### 查询任务进度

```bash
GET /api/progress/{job_id}
```

响应：
```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",
  "progress": 50,
  "message": "正在生成音频...",
  "stage": "tts_generating",
  "elapsed_time": 45.2,
  "timeout_warning": null
}
```

#### 取消任务

```bash
POST /api/cancel/{job_id}
```

#### 获取节目列表

```bash
GET /api/episodes
```

#### Webhook（传统方式）

```bash
POST /webhook
Content-Type: application/json

{"url": "https://example.com/article"}
```

#### 健康检查

```bash
GET /health
```

## 模型健康检查

系统会自动检测模型可用性：

1. **启动检测**：Worker 启动时检测配置的模型
2. **故障切换**：如果当前模型不可用，自动切换到备选模型
3. **日志记录**：所有健康检查结果记录到日志

健康检查包括：
- API 连接测试
- 认证验证
- 简单推理测试

## 日志系统

结构化日志记录在 `logs/ghostradio.log`：

```bash
# 查看实时日志
tail -f logs/ghostradio.log

# 查看任务日志
ls logs/jobs/
```

日志包含：
- 任务生命周期（开始、进度、完成、错误）
- API 请求记录
- 模型健康检查结果
- 超时警告

## 资源占用

| 状态 | 进程 | 内存占用 | CPU |
|------|------|----------|-----|
| **待机中 (99% 时间)** | server.py | ~15MB | 0% |
| **待机中** | cron | (系统自带) | 0% |
| **工作中 (1% 时间)** | worker.py | ~150MB - 300MB | 100% (nice限制) |

## 故障排查

### 查看日志

```bash
# 主日志
tail -f logs/ghostradio.log

# 特定任务日志
cat logs/jobs/a1b2c3d4.json
```

### 手动运行 Worker

```bash
python src/worker.py --once
```

### 检查模型健康

```bash
python -c "from src.providers import ProviderFactory; print(ProviderFactory.get_available_providers())"
```

### 测试 NVIDIA API

```bash
python test_nvidia.py
```

### 检查队列

```bash
cat queue.txt
```

### 清理旧文件

```bash
python -c "from src.file_manager import FileManager; from src.config import get_config; fm = FileManager(get_config().get_resources_config()); print(fm.cleanup())"
```

## 常见问题

### Q: 模型连接失败怎么办？

A: 系统会自动切换到备选模型。你也可以在配置中指定多个备选模型。

### Q: 生成进度卡住怎么办？

A: 
1. 查看日志 `tail -f logs/ghostradio.log`
2. 检查模型 API 是否正常
3. 在 Web 界面点击"取消"按钮中断任务
4. 重新提交任务

### Q: 如何切换模型？

A: 在 Web 界面的"模型配置"区域选择其他模型，或在 `config.yaml` 中修改配置。

### Q: 支持哪些文章链接？

A: 支持任何公开可访问的网页链接。系统会自动提取正文内容。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
