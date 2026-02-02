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
- [x] 内存占用测试 (< 15MB)

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
- [x] 实现音频格式转换（Opus/AAC）- 待 FFmpeg 集成

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
- [x] 静态文件托管配置 - 需用户配置 Web 服务器

### 3.2 Web 展示页面 ✅
- [x] 创建极简 HTML 播放器页面 (`episodes/index.html`)
- [x] 响应式设计（支持移动端）
- [x] 显示节目列表和元数据

### 3.3 前端界面重构 ✅
- [x] 现代化 UI 设计（渐变色彩、卡片布局）
- [x] 模型选择器（LLM: NVIDIA/OpenAI, TTS: Volcengine/OpenAI/Edge-TTS）
- [x] URL 输入框 with 验证
- [x] 实时进度条 with 状态更新
- [x] 结果展示区域（音频播放器、复制链接、下载按钮）
- [x] Toast 通知系统
- [x] 响应式移动端适配
- [x] 历史节目列表 with 播放/下载操作

---

## Phase 4: 代码质量提升 ✅

### 4.1 架构重构 ✅
- [x] 统一 Provider 命名规范（`VolcengineTTSProvider`）
- [x] 修复 TTS Provider 与 LLM Provider 命名不一致问题
- [x] 配置文件支持服务器配置项（host, port）

### 4.2 代码质量改进 ✅
- [x] 添加类型注解（`content_fetcher.py`, `file_manager.py`, `start.py`）
- [x] 移除硬编码路径（`server.py` 使用配置文件）
- [x] 改进错误处理（更具体的异常类型）
- [x] 改进配置加载，支持类型转换

### 4.3 配置系统优化 ✅
- [x] `config.get()` 方法支持类型转换
- [x] 添加服务器配置段（server.host, server.port）
- [x] 解耦 `server.py` 与配置系统

### 4.4 Prompt 系统重构 ✅
- [x] 移除全局单例模式，使用工厂函数
- [x] 添加类型注解和异常类
- [x] 支持配置路径检查和类型安全

### 4.5 LLMProcessor 重构 ✅
- [x] 使用 dataclass 定义结果类型（LLMResult）
- [x] 依赖注入：支持注入 PromptManager
- [x] 不可变配置：初始化后不修改配置
- [x] 添加 LLMError 异常类

### 4.6 TTSGenerator 重构 ✅
- [x] 使用 TypedDict 定义结果类型（TTSResult）
- [x] 使用 dataclass 定义音色信息（TTSVoiceInfo）
- [x] 添加 TTSError 异常类
- [x] 统一的配置管理

---

## Phase 5: 测试与优化 🚧

### 5.1 功能测试 🚧
- [ ] 端到端流程测试（URL → 音频 → RSS）
- [ ] LLM 多厂商兼容性测试
- [ ] 错误处理测试（网络失败、API 限制等）
- [ ] 并发安全性测试

### 5.2 资源优化 🚧
- [ ] 内存占用监控与优化
- [ ] 磁盘 I/O 优化
- [ ] CPU 使用率优化
- [ ] 音频压缩率测试

### 5.3 部署文档 ✅
- [x] 编写部署指南 (README.md)
- [x] 编写使用说明
- [x] 编写故障排查指南
- [x] 编写 API 配置示例

---

## Phase 7: REST API 开发 ✅

### 7.1 API 路由实现 ✅
- [x] POST /api/generate - 创建播客生成任务
- [x] GET /api/progress/{job_id} - 查询任务进度
- [x] GET /api/episodes - 获取节目列表

### 7.2 任务管理 ✅
- [x] JobManager 类管理任务状态
- [x] 任务状态持久化（JSON 文件）
- [x] 进度跟踪和更新

### 7.3 静态文件服务 ✅
- [x] 音频文件 (MP3) 服务
- [x] 前端页面服务
- [x] 正确的 Content-Type 设置

---

## Phase 6: 扩展功能（可选）⏸️

### 6.1 内容源扩展 ⏸️
- [ ] 支持 RSS 源自动抓取
- [ ] 支持邮件订阅内容
- [ ] 支持 Telegram Bot 推送
- [ ] 支持 Web 界面手动提交

### 6.2 音频增强 ⏸️
- [ ] 背景音乐支持
- [ ] 多音色切换
- [ ] 音频后处理（降噪、标准化）
- [ ] 章节标记支持

### 6.3 管理功能 ⏸️
- [ ] 简单的 Web 管理后台
- [ ] 处理状态监控
- [ ] 历史记录查看
- [ ] 重试失败任务

---

## Phase 8: 架构健壮性与自动化 (Upcoming) 🚀

### 8.1 队列与并发安全性 🚧
- [ ] **[Critical] 原子化任务队列**: 将单文件 `queue.txt` 升级为基于目录的任务文件（一任务一 JSON）或 SQLite，解决并发写入导致的任务丢失风险。
- [ ] **任务生命周期管理**: 完善任务状态机，支持任务超时自动清理和僵尸任务检测。

### 8.2 数据持久化与元数据 🚧
- [ ] **集中式元数据索引**: 引入 `episodes.json` 或 SQLite 记录节目详情（原始 URL、Token 消耗、Provider 信息、时长），避免频繁扫描文件系统。
- [ ] **音频时长自动检测**: 集成 `ffprobe` 或 `mutagen` 自动提取生成音频的准确时长，更新 RSS 和 UI 展示。

### 8.3 流程自动化与可靠性 🚧
- [ ] **RSS 自动更新**: 将 `RSSGenerator` 集成到 Worker 完成回调中，实现生成即上线，无需手动运行脚本。
- [ ] **细粒度重试机制**: 为抓取、LLM 和 TTS 步骤添加独立的指数退避重试（Tenacity），提高在不稳定网络下的成功率。
- [ ] **实时进度上报**: Worker 在处理过程中主动更新任务 JSON 的进度字段，提供真正的实时进度条而非"猜测"。

### 8.4 UI/UX 增强 🚧
- [ ] **主动任务取消**: Worker 在执行耗时操作前检查取消标志，支持前端一键终止任务以节省 Token。
- [ ] **输入防抖与去重**: 检查是否有相同 URL 的任务正在处理，防止重复生成。

### 8.5 维护性与观测性 🚧
- [ ] **日志标准化**: 统一使用 `src/logger.py`，移除 Worker 中的 print 调试，集成更详细的上下文追踪。
- [ ] **路径处理统一化**: 全面迁移至 `pathlib.Path`，提高跨平台兼容性。

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

# 4. 服务器配置
server:
  host: "0.0.0.0"
  port: 8080
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
│   ├── rss_generator.py   # RSS Feed 生成
│   └── providers/         # LLM Provider 目录
│       ├── base_provider.py
│       ├── openai_provider.py
│       └── nvidia_provider.py
├── tts_providers/         # TTS Provider 目录
│   ├── base_tts_provider.py
│   ├── edge_tts_provider.py
│   ├── openai_tts_provider.py
│   └── volcengine_provider.py
├── prompts/
│   ├── prompts.yaml       # Prompt 配置文件
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

## 代码改进总结

### 已完成的改进

1. **架构优化**
   - 统一 Provider 命名：`VolcengineProvider` → `VolcengineTTSProvider`
   - 配置文件添加 `server` 配置段

2. **代码质量提升**
   - `content_fetcher.py`: 添加完整类型注解，改进错误处理
   - `file_manager.py`: 添加完整类型注解
   - `start.py`: 添加完整类型注解，改进错误处理

3. **配置系统改进**
   - `config.get()` 方法支持类型转换参数
   - `server.py` 解耦，使用配置文件获取 server.host 和 server.port

4. **类型安全**
   - 所有公共方法添加返回类型注解
   - 变量添加类型注解
   - 异常处理更具体

---

## 下一步工作

1. **立即行动**: 配置 API 密钥并测试端到端流程
2. **短期**: 完成 Phase 5 的测试和优化
3. **中期**: 根据实际使用情况决定是否进入 Phase 6 扩展功能

---

*最后更新: 2026-01-31*
*代码质量改进完成*
