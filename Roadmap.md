# GhostRadio 项目路线图

> 核心理念：**平时"装死"，只在有任务时"诈尸"** - 极致省资源的 Serverless-like 架构

---

## Phase 1: 基础架构搭建 ✅

### 1.1 项目初始化 ✅
- [x] 创建项目目录结构
- [x] 初始化 Git 仓库
- [x] 创建 `.gitignore` 文件（排除音频文件、环境变量等）
- [x] 创建 `requirements.txt` 依赖文件

### 1.2 轻量级触发器 (Trigger) ✅
- [x] 实现 Webhook 接收器（Python http.server）
- [x] 创建 `server.py` - 极简 HTTP 服务
- [x] 实现 URL 队列写入功能 (`queue.txt`)
- [ ] 内存占用测试 (< 15MB) - 待测试

### 1.3 配置文件系统 ✅
- [x] 创建 `config.yaml` 配置文件模板
- [x] 实现 LLM 适配层（支持多厂商 API）
- [x] 实现资源限制配置
- [x] 实现播客信息配置

---

## Phase 2: 核心功能实现 ✅

### 2.1 Worker 处理脚本 ✅
- [x] 创建 `worker.py` - 核心处理逻辑
- [x] 实现队列读取功能
- [x] 实现 URL 内容获取模块 (`content_fetcher.py`)
- [x] 实现 LLM API 调用模块 (`llm_processor.py`)
- [x] 实现音频合成模块 (`tts_generator.py`)
- [ ] 实现音频格式转换（Opus/AAC）- 待 FFmpeg 集成

### 2.2 调度系统 ✅
- [x] 创建 `scheduler.py` 调度脚本
- [x] 实现单任务锁（跨平台文件锁 `file_lock.py`）
- [x] 实现 `nice -n 19` 低优先级运行
- [x] 实现处理完成后自动退出

### 2.3 文件生命周期管理 ✅
- [x] 实现 FIFO 策略（保留最近 5 个文件）
- [x] 实现磁盘空间检查（最大 200MB）
- [x] 实现旧文件自动清理 (`file_manager.py`)

---

## Phase 3: 播客输出系统 ✅

### 3.1 RSS Feed 生成 ✅
- [x] 实现 RSS XML 生成器 (`rss_generator.py`)
- [x] 支持播客元数据（标题、描述、封面）
- [x] 支持音频文件信息（时长、大小、格式）
- [ ] 静态文件托管配置 - 需用户配置 Web 服务器

### 3.2 Web 展示页面 ✅
- [x] 创建极简 HTML 播放器页面 (`episodes/index.html`)
- [x] 响应式设计（支持移动端）
- [x] 显示节目列表和元数据

---

## Phase 4: 测试与优化 🚧

### 4.1 功能测试 🚧
- [ ] 端到端流程测试（URL → 音频 → RSS）
- [ ] LLM 多厂商兼容性测试
- [ ] 错误处理测试（网络失败、API 限制等）
- [ ] 并发安全性测试

### 4.2 资源优化 🚧
- [ ] 内存占用监控与优化
- [ ] 磁盘 I/O 优化
- [ ] CPU 使用率优化
- [ ] 音频压缩率测试

### 4.3 部署文档 ✅
- [x] 编写部署指南 (README.md)
- [x] 编写使用说明
- [x] 编写故障排查指南
- [x] 编写 API 配置示例

---

## Phase 5: 扩展功能（可选）⏸️

### 5.1 内容源扩展 ⏸️
- [ ] 支持 RSS 源自动抓取
- [ ] 支持邮件订阅内容
- [ ] 支持 Telegram Bot 推送
- [ ] 支持 Web 界面手动提交

### 5.2 音频增强 ⏸️
- [ ] 背景音乐支持
- [ ] 多音色切换
- [ ] 音频后处理（降噪、标准化）
- [ ] 章节标记支持

### 5.3 管理功能 ⏸️
- [ ] 简单的 Web 管理后台
- [ ] 处理状态监控
- [ ] 历史记录查看
- [ ] 重试失败任务

---

## 资源预算目标

| **状态** | **进程** | **内存占用** | **CPU** |
|---------|---------|-------------|---------|
| **待机中 (99% 时间)** | `server.py` | ~15MB | 0% |
| **待机中** | `cron` | (系统自带) | 0% |
| **工作中 (1% 时间)** | `worker.py` | ~150MB - 300MB | 100% (nice限制) |

---

## 配置示例

```yaml
# GhostRadio 配置文件

# 1. 模型配置 (兼容所有 OpenAI 格式的 API)
llm:
  provider: "custom"
  base_url: "https://api.deepseek.com/v1"
  api_key_env: "LLM_API_KEY"
  model_name: "deepseek-chat"
  context_window: 16000
  temperature: 0.7
  prompt_file: "prompts/podcast_host.txt"

# 2. 资源限制
resources:
  max_concurrent_tasks: 1
  keep_last_n_episodes: 5
  audio_format: "m4a"

# 3. 播客信息
podcast:
  title: "我的私有频道"
  base_url: "https://你的域名.com/podcast"
```

---

## 技术栈

- **触发器**: Python http.server
- **处理脚本**: Python 3.8+
- **调度**: Linux crontab
- **音频**: FFmpeg (格式转换，可选)
- **TTS**: 各厂商 API (OpenAI, Azure, Edge-TTS 等)
- **Web**: 静态文件 + 可选 Caddy/Nginx

---

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
│   ├── file_lock.py       # 跨平台文件锁
│   └── rss_generator.py   # RSS Feed 生成
├── prompts/
│   └── podcast_host.txt   # 播客主持人提示词
├── episodes/              # 生成的音频文件
│   └── index.html         # Web 展示页面
├── logs/                  # 日志文件
├── config.example.yaml    # 配置模板
├── requirements.txt       # Python 依赖
├── README.md             # 项目文档
└── roadmap.md            # 本文件
```

---

## 下一步工作

当前 Phase 1-3 已完成，Phase 4 进行中。建议：

1. **立即行动**: 配置 API 密钥并测试端到端流程
2. **短期**: 完成 Phase 4 的测试和优化
3. **中期**: 根据实际使用情况决定是否进入 Phase 5 扩展功能

---

*最后更新: 2026-01-31*
