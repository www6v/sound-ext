# Realtime-Venus 项目分析报告

> **分析日期**: 2026-11-14  
> **项目地址**: https://github.com/inclusionAI/Realtime-Venus  
> **论文**: [arXiv:2609.13814](https://arxiv.org/pdf/2609.13814)  
> **许可协议**: Apache License 2.0

---

## 1. 项目概述

**Realtime-Venus** 是由 **蚂蚁集团 Venus Team** 与 **清华大学** 联合研发的 **全双工实时交互系统**，支持异步任务委托。核心理念是：**实时看、听、说，同时让后台任务与对话并行进行**。

用户可以与助手实时对话，同时委托它执行后台任务；任务完成后，结果自动回到同一段对话中，由模型用语音播报。

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| **持续视听交互** | Omni 模型持续接收摄像头和麦克风输入，根据场景变化主动发起回应 |
| **全双工对话** | 模型在说话时继续处理用户输入，能区分附和、背景人声和真正的打断 |
| **异步任务委托** | 模型将自然语言任务交给 Harness 执行，实时对话继续进行 |
| **原对话交付结果** | Harness 准备回复内容，前端模型决定发言时机并生成原生语音 |

---

## 2. 项目架构

### 2.1 三大核心组件

```mermaid
graph TB
    subgraph RealtimeVenus["Realtime-Venus 系统架构"]
        direction TB
        
        subgraph Frontend["前端模型层"]
            Omni["<b>Realtime-Venus-Omni</b><br/>9B 参数<br/>───────────<br/>• 音视频流式对话<br/>• 主动感知交互<br/>• 原生语音生成"]
            Audio["<b>Realtime-Venus-Audio</b><br/>9B 参数<br/>───────────<br/>• 语音交互对话<br/>• 全双工语音<br/>• 原生语音生成"]
        end
        
        subgraph Harness["Harness 异步执行引擎"]
            Core["核心运行时<br/>DelegateHarness"]
            Bridge["桥接层<br/>VenusOmniServingHost"]
            Agents["Agent 执行器<br/>Codex / Skills"]
        end
        
        subgraph Backend["外部后端"]
            Codex["Codex<br/>任务执行"]
            Gemini["Gemini<br/>路由/润色"]
        end
    end
    
    Omni --> Bridge
    Audio --> Bridge
    Bridge --> Core
    Core --> Agents
    Agents --> Codex
    Agents --> Gemini
    
    style RealtimeVenus fill:#1a1a2e,stroke:#16213e,color:#fff
    style Frontend fill:#0f3460,stroke:#16213e,color:#fff
    style Harness fill:#533483,stroke:#16213e,color:#fff
    style Backend fill:#2b2d42,stroke:#16213e,color:#fff
    style Omni fill:#4361ee,stroke:#3a0ca3,color:#fff
    style Audio fill:#7209b7,stroke:#3a0ca3,color:#fff
    style Core fill:#f72585,stroke:#b5179e,color:#fff
    style Bridge fill:#4cc9f0,stroke:#4361ee,color:#fff
    style Agents fill:#4895ef,stroke:#4361ee,color:#fff
    style Codex fill:#06d6a0,stroke:#118ab2,color:#fff
    style Gemini fill:#ffd166,stroke:#118ab2,color:#000
```

| 组件 | 职责 | 模型规模 |
|------|------|----------|
| **Realtime-Venus-Omni** | 面向流式音视频的对话模型，支持持续感知、主动交互与原生语音生成 | 9B 参数 |
| **Realtime-Venus-Audio** | 单独训练的语音对话模型，支持音频理解、全双工交互与原生语音生成 | 9B 参数 |
| **Realtime-Venus-Harness** | 两类模型共用的异步执行框架，负责接收委托、推进后台任务，并将结果送回原会话 | 独立包 |

### 2.2 双循环架构

系统采用 **双循环（Two Loops）** 设计：

```mermaid
graph LR
    subgraph InteractionLoop["🔄 交互循环 Interaction Loop"]
        direction TB
        User["👤 用户"]
        Mic["🎤 麦克风<br/>摄像头"]
        Speaker["🔊 扬声器<br/>显示器"]
        Model["前端模型<br/>Omni / Audio"]
        
        User -->|"语音/视频输入"| Mic
        Mic -->|"流式媒体"| Model
        Model -->|"原生语音"| Speaker
        Speaker -->|"听觉/视觉反馈"| User
    end
    
    subgraph CapabilityLoop["⚡ 能力循环 Capability Loop"]
        direction TB
        Delegate["<delegate><br/>任务委托"]
        Harness["Harness<br/>异步执行"]
        Backend["Codex / Gemini<br/>任务处理"]
        Result["<backend><br/>结果返回"]
        
        Delegate -->|"自然语言任务"| Harness
        Harness -->|"路由/执行"| Backend
        Backend -->|"任务结果"| Harness
        Harness -->|"口语化回复"| Result
    end
    
    Model -->|"检测到委托意图"| Delegate
    Result -->|"插入对话边界"| Model
    
    style InteractionLoop fill:#1e3a5f,stroke:#4cc9f0,color:#fff,stroke-width:2px
    style CapabilityLoop fill:#3d1e5f,stroke:#f72585,color:#fff,stroke-width:2px
    style User fill:#06d6a0,stroke:#118ab2,color:#fff
    style Mic fill:#4895ef,stroke:#4361ee,color:#fff
    style Speaker fill:#4895ef,stroke:#4361ee,color:#fff
    style Model fill:#4361ee,stroke:#3a0ca3,color:#fff
    style Delegate fill:#f72585,stroke:#b5179e,color:#fff
    style Harness fill:#7209b7,stroke:#3a0ca3,color:#fff
    style Backend fill:#06d6a0,stroke:#118ab2,color:#fff
    style Result fill:#f72585,stroke:#b5179e,color:#fff
```

- **交互循环（Interaction Loop）**：前端模型处理流式媒体和语音，实时与用户交互
- **能力循环（Capability Loop）**：Harness 异步执行 `<delegate>...</delegate>` 请求，通过 `<backend>...</backend>` 标记将结果返回给前端模型进行语音播报

---

## 3. 目录结构详解

```text
Realtime-Venus/
├── harness/                    # 异步任务执行引擎（独立可发布包）
│   ├── core/                   # 核心运行时
│   │   ├── harness.py          # DelegateHarness - 公共异步门面
│   │   ├── backend.py          # DelegateBackend 协议定义
│   │   ├── session.py          # 双工协议会话管理
│   │   ├── scheduler.py        # 任务调度器
│   │   ├── config.py           # Harness 配置
│   │   ├── models.py           # 数据模型（AudioChunk, VideoFrame 等）
│   │   ├── buffers.py          # 上下文缓冲区
│   │   ├── delivery.py         # 结果交付逻辑
│   │   ├── result_manager.py   # 结果管理
│   │   ├── delegate_parser.py  # <delegate> 协议解析
│   │   ├── speech.py           # 语音处理
│   │   ├── media.py            # 媒体处理
│   │   ├── workspace.py        # 工作空间管理
│   │   └── ...
│   ├── bridge/                 # 模型集成桥接层
│   │   ├── host.py             # VenusOmniServingHost
│   │   ├── serving.py          # 模型服务端口
│   │   ├── runtime.py          # 运行时桥接
│   │   └── ...
│   ├── agents/                 # Agent 执行器
│   │   ├── codex.py            # Codex Agent 提供者
│   │   ├── app_server.py       # 应用服务器连接
│   │   ├── contracts.py        # Agent 合约
│   │   ├── vision.py           # 视觉处理
│   │   ├── media.py            # 媒体处理
│   │   └── ...
│   ├── llm/                    # LLM 后端
│   │   ├── backends.py         # CodexPlannerBackend
│   │   ├── delegate.py         # CodexDirectAndPolish
│   │   ├── gemini.py           # Gemini 后端
│   │   ├── planner.py          # PlannerClient 路由
│   │   └── ...
│   ├── jobs/                   # 任务生命周期管理
│   │   ├── manager.py          # 任务管理器
│   │   ├── models.py           # 任务状态模型
│   │   ├── feedback.py         # 反馈处理
│   │   ├── progress.py         # 进度跟踪
│   │   └── ...
│   ├── config.py               # 配置加载
│   ├── settings.py             # 设置管理
│   ├── factory.py              # Harness 工厂
│   ├── backends.py             # 后端选择
│   ├── skills.py               # 技能注册
│   └── prompts.py              # 提示词
│
├── frontend/                   # 独立推理示例
│   ├── Realtime-Venus-Omni/    # 视听模型推理
│   │   ├── offline_chat.py         # 离线视频对话
│   │   ├── offline_memory_chat.py  # 带长期记忆的离线对话
│   │   ├── duplex_chat.py          # 全双工视频交互（文本提问）
│   │   ├── duplex_speech_in_chat.py # 全双工视频交互（语音提问）
│   │   └── duplex_memory_chat.py   # 带长期记忆的全双工对话
│   └── Realtime-Venus-Audio/   # 音频模型推理
│       ├── audio_offline_chat.py    # 离线音频理解
│       ├── audio_duplex_chat.py     # 全双工音频交互
│       └── case/                    # 示例音频素材
│
├── demos/                      # 浏览器在线演示
│   ├── server/                 # Web 服务
│   │   ├── app.py              # FastAPI 应用主入口
│   │   ├── session.py          # WebAgentSession 会话管理
│   │   ├── resources.py        # 资源管理
│   │   ├── configuration.py    # Web 配置管理
│   │   ├── media.py            # 媒体处理
│   │   ├── backends.py         # 后端配置
│   │   └── cli.py              # 命令行接口
│   ├── model/                  # 模型服务
│   │   ├── server.py           # 模型 HTTP API (端口 8031)
│   │   ├── adapter.py          # 模型适配器
│   │   ├── client.py           # 模型客户端
│   │   ├── decoding.py         # 解码参数
│   │   └── wire.py             # 通信协议
│   ├── launcher/               # 启动器
│   │   ├── cli.py              # CLI 入口
│   │   ├── supervisor.py       # 进程管理
│   │   ├── config.py           # 配置校验
│   │   └── options.py          # 启动选项
│   ├── static/                 # 前端静态资源
│   │   ├── index.html          # 主页面
│   │   ├── app.js              # 前端逻辑
│   │   └── fonts/              # 字体文件
│   ├── settings.py             # 设置持久化
│   ├── deployment.py           # 部署配置
│   ├── install.py              # 安装脚本
│   ├── variants.py             # 模型变体
│   └── requirements.txt        # Demo 依赖
│
├── tests/                      # 测试套件
│   ├── test_download_models.py
│   ├── test_gemini_provider.py
│   ├── test_media_recovery.py
│   ├── test_model_modes.py
│   ├── test_web_configuration.py
│   └── ...
│
├── assets/                     # 资源文件
│   ├── paper-*.svg             # 论文图片
│   ├── experience-*.png        # Demo 截图
│   └── technical_report.pdf    # 技术报告
│
├── config.json                 # 根配置（前端模型 + Web 服务）
├── download_models.py          # 统一模型下载器
├── pyproject.toml              # Harness 包配置
├── requirements.txt            # 共享依赖入口
├── install.sh                  # 安装脚本
├── start.sh                    # 启动脚本
├── README.md                   # 英文说明
├── README_ZH.md                # 中文说明
└── LICENSE                     # Apache 2.0
```

---

## 4. 技术栈

### 4.1 后端技术

| 技术 | 版本/用途 |
|------|-----------|
| **Python** | >= 3.11（Harness）/ 3.10（推理示例） |
| **PyTorch** | 2.4.0（模型推理） |
| **Transformers** | 4.51.3（Hugging Face 模型加载） |
| **FastAPI** | >= 0.115（Web 服务框架） |
| **Uvicorn** | >= 0.30（ASGI 服务器） |
| **httpx** | >= 0.28（HTTP 客户端，含 Gemini 支持） |
| **FFmpeg/av** | >= 12（音视频处理） |
| **Pillow** | >= 10.4（图像处理） |

### 4.2 模型相关

| 组件 | 说明 |
|------|------|
| **模型规模** | 9B 参数（Omni 和 Audio 各自） |
| **精度** | BF16（推理） |
| **注意力机制** | SDPA（Scaled Dot-Product Attention） |
| **语音解码** | minicpmo-utils[tts]==1.0.6 |
| **语音合成** | 原生 TTS 模块（flow.yaml/hift.pt/campplus.onnx） |

### 4.3 外部集成

| 服务 | 用途 |
|------|------|
| **Codex** | 默认任务执行后端（General 模式） |
| **Gemini** | 可选的 Routing/Polish/Multimodal 后端 |
| **Hugging Face Hub** | 模型下载 |
| **ModelScope** | 国内镜像下载 |

---

## 5. 核心模块详解

### 5.1 Harness 异步执行引擎

Harness 是系统的核心创新，实现了 **对话中的异步任务委托**。

#### 工作流程

```mermaid
graph LR
    subgraph Capture["1️⃣ Capture 捕获"]
        C1["协议门控<br/>组装 delegate spans"]
        C2["证据截止<br/>固定 opening tag"]
        C3["注册请求<br/>关联原始会话"]
        C1 --> C2 --> C3
    end
    
    subgraph Dispatch["2️⃣ Dispatch 分发"]
        D1{"路由决策"}
        D2["Multimodal<br/>直接回答"]
        D3["General<br/>Codex 执行"]
        D4["Skill<br/>领域技能"]
        D1 --> D2
        D1 --> D3
        D1 --> D4
    end
    
    subgraph Return["3️⃣ Return 返回"]
        R1["准备口语化回复"]
        R2["检查交付条件"]
        R3["移除协议文本"]
        R4["插入 <backend>"]
        R1 --> R2 --> R3 --> R4
    end
    
    User["👤 用户输入"] --> Capture
    Capture --> Dispatch
    Dispatch --> Return
    Return --> Model["🤖 模型语音输出"]
    
    style Capture fill:#1e3a5f,stroke:#4cc9f0,color:#fff
    style Dispatch fill:#3d1e5f,stroke:#f72585,color:#fff
    style Return fill:#1e5f3a,stroke:#06d6a0,color:#fff
    style User fill:#4895ef,stroke:#4361ee,color:#fff
    style Model fill:#4895ef,stroke:#4361ee,color:#fff
    style D1 fill:#ffd166,stroke:#118ab2,color:#000
```

#### 任务生命周期

```mermaid
stateDiagram-v2
    [*] --> QUEUED: 任务提交
    
    QUEUED --> RUNNING: 开始执行
    
    RUNNING --> COMPLETED: 执行成功
    RUNNING --> FAILED: 执行失败
    
    COMPLETED --> DELIVERING: 准备交付
    DELIVERING --> DELIVERED: 语音播放确认
    
    FAILED --> [*]: 错误处理
    DELIVERED --> [*]: 完成
    
    %% 取消流程
    QUEUED --> CANCELLING: 用户取消
    RUNNING --> CANCELLING: 用户取消
    CANCELLING --> CANCELLED: 取消完成
    CANCELLED --> [*]
    
    note right of QUEUED: 任务已接受，等待执行
    note right of RUNNING: 路由、执行或回复准备中
    note right of COMPLETED: 结果和回复已就绪
    note right of DELIVERING: 等待插入到原对话
    note right of DELIVERED: 交付完成（含语音播放确认）
```

| 状态 | 含义 |
|------|------|
| `QUEUED` | 任务已接受，等待执行 |
| `RUNNING` | 路由、执行或回复准备中 |
| `COMPLETED` | 结果和回复已就绪 |
| `DELIVERING` | 等待插入到原对话 |
| `DELIVERED` | 交付完成（含语音播放确认） |

#### 执行路径

| 路径 | 用途 | 实现 |
|------|------|------|
| **Multimodal / Direct** | 使用现有音视频证据直接回答 | `llm/delegate.py` |
| **General** | 需要工具或多步执行的复杂任务 | `agents/`, `jobs/` |
| **Skill** | 执行已注册的领域技能 | `skills.py` |

#### 核心接口

```mermaid
classDiagram
    class DelegateBackend {
        <<Protocol>>
        +plan(request, candidates) RoutingDecision
        +execute(request, context) BackendResponse
        +oralize(request, source) BackendResponse
        +aclose() void
    }
    
    class DelegateHarness {
        -config: HarnessConfig
        -backend: DelegateBackend
        -scheduler: DelegateScheduler
        -sessions: dict
        +open_session(session_id) void
        +submit_delegate(session_id, query) work_id
        +next_delegate_result(session_id, timeout) DelegateResult
        +ingest_user_audio(session_id, chunk) int
        +ingest_user_video_segment(session_id, segment) int
        +aclose() void
    }
    
    class DuplexProtocolSession {
        -session_id: str
        -config: HarnessConfig
        -backend: DelegateBackend
        +ingest_audio(chunk) int
        +ingest_video(segment) int
        +submit_delegate(query) work_id
    }
    
    class DelegateRequest {
        +query: str
        +session_id: str
        +work_id: str
        +created_at: datetime
    }
    
    class DelegateResult {
        +work_id: str
        +status: str
        +response: BackendResponse
        +artifacts: list
    }
    
    class AudioChunk {
        +data: bytes
        +sample_rate: int
        +timestamp: float
    }
    
    class VideoFrame {
        +data: bytes
        +width: int
        +height: int
        +timestamp: float
    }
    
    DelegateHarness --> DelegateBackend : uses
    DelegateHarness --> DuplexProtocolSession : manages
    DelegateHarness --> DelegateResult : returns
    DuplexProtocolSession --> DelegateRequest : creates
    DuplexProtocolSession --> AudioChunk : ingests
    DuplexProtocolSession --> VideoFrame : ingests
```

```python
# DelegateBackend 协议
class DelegateBackend(Protocol):
    async def plan(request, candidates) -> RoutingDecision: ...
    async def execute(request, context) -> BackendResponse: ...
    async def oralize(request, source) -> BackendResponse: ...
    async def aclose(self) -> None: ...

# DelegateHarness 使用示例
harness = DelegateHarness(backend=backend)
await harness.open_session("demo-session")
work_id = await harness.submit_delegate("demo-session", "创建1-100的平方表")
result = await harness.next_delegate_result("demo-session", timeout_s=180)
```

### 5.2 前端模型服务

#### 模型推理流程

```mermaid
flowchart LR
    subgraph OmniFlow["Omni 模型推理流程"]
        direction TB
        
        subgraph Input["输入"]
            VideoIn["📹 视频流<br/>或离线文件"]
            AudioIn["🎤 音频流<br/>或离线文件"]
            TextIn["💬 文本提问"]
        end
        
        subgraph Processing["处理"]
            FrameSampler["帧采样<br/>1 FPS"]
            AudioEncoder["音频编码器"]
            VideoEncoder["视觉编码器"]
            Fusion["多模态融合<br/>Transformer"]
        end
        
        subgraph Output["输出"]
            TextOut["📝 文本回复"]
            SpeechOut["🔊 原生语音"]
        end
        
        VideoIn --> FrameSampler --> VideoEncoder
        AudioIn --> AudioEncoder
        TextIn --> Fusion
        VideoEncoder --> Fusion
        AudioEncoder --> Fusion
        Fusion --> TextOut
        Fusion --> SpeechOut
    end
    
    subgraph AudioFlow["Audio 模型推理流程"]
        direction TB
        
        AudioOnly["🎤 音频输入"] --> AudioEnc2["音频编码器"]
        AudioEnc2 --> AudioLM["语言模型<br/>全双工/离线"]
        AudioLM --> TextOnly["📝 文本输出"]
        AudioLM --> SpeechOnly["🔊 语音输出<br/>24kHz WAV"]
    end
    
    style OmniFlow fill:#1e3a5f,stroke:#4cc9f0,color:#fff
    style AudioFlow fill:#3d1e5f,stroke:#f72585,color:#fff
    style Input fill:#2d3748,stroke:#718096,color:#fff
    style Processing fill:#553c9a,stroke:#805ad5,color:#fff
    style Output fill:#22543d,stroke:#38a169,color:#fff
```

#### Realtime-Venus-Omni（视听模型）

| 示例 | 模式 | 输入 | 输出 |
|------|------|------|------|
| `offline_chat.py` | 半双工 | 视频 + 文本提问 | 文本 + 语音 |
| `offline_memory_chat.py` | 半双工 + 记忆 | 长视频 + 文本 | 文本 + 语音 |
| `duplex_chat.py` | 全双工 | 流式视频 + 文本注入 | 带字幕视频 |
| `duplex_speech_in_chat.py` | 全双工 | 流式视频（含语音） | 带字幕视频 |
| `duplex_memory_chat.py` | 全双工 + 记忆 | 长视频 + 文本 | 带字幕视频 |

#### Realtime-Venus-Audio（音频模型）

| 示例 | 模式 | 输入 | 输出 |
|------|------|------|------|
| `audio_offline_chat.py` | 离线 | 完整音频 | 文本 |
| `audio_duplex_chat.py` | 全双工 | 流式音频块 | 24kHz WAV |

### 5.3 Web Demo 服务

#### 全双工交互时序图

```mermaid
sequenceDiagram
    actor User as 👤 用户
    participant Browser as 🖥️ 浏览器
    participant Web as 🌐 Web服务<br/>:8032
    participant Model as 🤖 模型服务<br/>:8031
    participant Harness as ⚙️ Harness
    participant Codex as 📦 Codex
    
    User->>Browser: 语音输入 "帮我写个脚本"
    Browser->>Web: WebSocket 音频流
    Web->>Model: 流式音频 + 视频帧
    
    par 交互循环
        Model-->>Web: 文本输出 (检测委托意图)
        Model-->>Web: <delegate>写一个Python脚本...</delegate>
        Web->>Harness: 提交异步任务
    and 能力循环
        Harness->>Codex: 执行任务
        Model-->>Browser: 语音 "好的，我来帮你写"
        Browser-->>User: 🔊 语音播放
    end
    
    Note over User,Codex: 对话继续，任务在后台执行...
    
    User->>Browser: "天气怎么样？"
    Browser->>Web: 音频流
    Web->>Model: 流式输入
    Model-->>Web: "今天晴天"
    Web-->>Browser: 语音
    Browser-->>User: 🔊 语音播放
    
    Codex-->>Harness: 任务完成 (script.py)
    Harness->>Harness: 口语化结果
    Harness-->>Web: <backend>脚本已创建...</backend>
    
    Note over Web: 等待合适的对话边界
    
    Web->>Model: 插入 <backend> 结果
    Model-->>Browser: "脚本已经写好了"
    Browser-->>User: 🔊 语音播报 + 📥 下载链接
```

#### 服务组件职责

| 组件 | 职责 | 端口 |
|------|------|------|
| **Browser** | 采集设备/上传、流式输入、播放语音、显示进度 | - |
| **Web Service** | HTTP/WebSocket、会话管理、组件编排 | 8032 |
| **Session Host** | 媒体输入排序、模型输出消费、反馈调度 | - |
| **Model Service** | 加载权重、流式推理、语音生成 | 8031 |
| **Harness + Codex** | 任务执行、进度跟踪、结果交付 | - |

```mermaid
graph TB
    subgraph Client["🖥️ 客户端"]
        Browser["浏览器<br/>────────<br/>• 设备采集/上传<br/>• 流式输入<br/>• 语音播放<br/>• 任务进度"]
    end
    
    subgraph Services["🖧 服务端"]
        subgraph WebService["Web 服务 · 8032"]
            App["FastAPI 应用<br/>app.py"]
            WS["WebSocket<br/>会话管理"]
            Session["WebAgentSession<br/>session.py"]
        end
        
        subgraph ModelService["模型服务 · 8031"]
            Server["模型 HTTP API<br/>server.py"]
            Adapter["模型适配器<br/>adapter.py"]
            Inference["流式推理<br/>+ 语音生成"]
        end
        
        subgraph HarnessService["Harness 引擎"]
            Harness["DelegateHarness"]
            Codex["Codex Agent"]
            Skills["Skills 技能"]
        end
    end
    
    subgraph External["☁️ 外部服务"]
        CodexAPI["Codex API"]
        GeminiAPI["Gemini API"]
        HF["HuggingFace"]
    end
    
    Browser <-->|"WebSocket<br/>音视频流"| WebService
    Browser -->|"HTTP<br/>文件上传"| WebService
    
    App --> Session
    WS --> Session
    Session --> Adapter
    Session --> Harness
    
    Server --> Adapter
    Adapter --> Inference
    
    Harness --> Codex
    Harness --> Skills
    
    Codex --> CodexAPI
    Skills --> GeminiAPI
    Inference -.->|"加载权重"| HF
    
    style Client fill:#1a365d,stroke:#4299e1,color:#fff
    style Services fill:#2d3748,stroke:#718096,color:#fff
    style WebService fill:#2b6cb0,stroke:#4299e1,color:#fff
    style ModelService fill:#6b46c1,stroke:#805ad5,color:#fff
    style HarnessService fill:#2f855a,stroke:#48bb78,color:#fff
    style External fill:#744210,stroke:#d69e2e,color:#fff
    style Browser fill:#4299e1,stroke:#2b6cb0,color:#fff
```

#### 输入模式

| 模式 | 功能 |
|------|------|
| **Audio · 麦克风** | 实时麦克风输入 |
| **Audio · 音频上传** | WAV/MP3/M4A/FLAC/OGG，最大 200MB |
| **Omni · 摄像头** | 摄像头 + 麦克风实时交互 |
| **Omni · 视频上传** | 本地视频文件，最大 200MB |

---

## 6. 配置系统

### 6.1 两份配置文件

#### 根 `config.json`（Demo 配置）

```json
{
  "model": {
    "type": "video",          // "audio" 或 "video"/"omni"
    "path": "Realtime-Venus-Omni",
    "reference_audio": "",     // 参考音频，空为默认
    "port": 8031,
    "memory_minutes": 40,      // Omni 视频记忆时长
    "length_penalty": 0.8,     // 语音长度惩罚 (0.1-5)
    "timeout_s": 180
  },
  "harness": {
    "config": "harness/config.json"
  },
  "web": {
    "host": "127.0.0.1",
    "port": 8032
  },
  "startup_timeout": 600
}
```

#### `harness/config.json`（Harness 配置）

主要配置组：

| 组 | 控制内容 |
|----|----------|
| `codex` | 执行器、模型、effort、超时 |
| `routing` | General/Auto 模式、Codex/Gemini、路由模型 |
| `responses` / `multimodal` | 独立的 Polish 和多模态提供者 |
| `gemini` | Gemini 模型和 API Key |
| `feedback` | 进度反馈、队列、技能预算 |
| `harness.delegate` | 请求/口语化超时、结果 TTL |
| `harness.result_management` | 静默窗口、队列、播放等待 |
| `harness.buffer` / `runtime` / `workspace` | 上下文保留、并发、存储 |

### 6.2 优先级

```
CLI 参数 > 环境变量 > 配置文件 > 默认值
```

关键环境变量：
- `VENUS_MODEL_TYPE`, `MODEL_PATH`, `AUDIO_MODEL_PATH` / `OMNI_MODEL_PATH`
- `REF_AUDIO`, `VENUS_MODEL_PORT`, `VENUS_MEMORY_MINUTES`
- `VENUS_WEB_HOST`, `VENUS_WEB_PORT`
- `HARNESS_CONFIG`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`

---

## 7. 部署与运行

### 7.1 部署架构

```mermaid
graph TB
    subgraph Server["🖥️ GPU 服务器 (需要 A100)"]
        direction TB
        
        subgraph Processes["进程组"]
            ModelProc["模型进程<br/>:8031<br/>────────<br/>• PyTorch 推理<br/>• 9B 模型加载<br/>• BF16 精度"]
            WebProc["Web 进程<br/>:8032<br/>────────<br/>• FastAPI 服务<br/>• WebSocket<br/>• 会话管理"]
        end
        
        subgraph Storage["存储"]
            ModelWeights["模型权重<br/>Realtime-Venus-Omni/<br/>或 Realtime-Venus-Audio/"]
            Runtime["运行时<br/>runtime/<br/>────────<br/>• logs/<br/>• workspace/"]
            Venv["Python 虚拟环境<br/>runtime/venv/"]
        end
        
        subgraph Config["配置"]
            RootConfig["config.json"]
            HarnessConfig["harness/config.json"]
        end
        
        ModelProc --> ModelWeights
        WebProc --> RootConfig
        RootConfig --> HarnessConfig
        Venv --> ModelProc
        Venv --> WebProc
    end
    
    subgraph Local["💻 本地电脑"]
        direction TB
        Terminal["终端<br/>SSH 隧道"]
        Browser["浏览器<br/>http://localhost:8032"]
        
        Terminal -->|"ssh -N -L 8032:127.0.0.1:8032"| Browser
    end
    
    subgraph Internet["☁️ 互联网"]
        CodexCloud["Codex API"]
        GeminiCloud["Gemini API"]
    end
    
    Browser <-->|"SSH 隧道<br/>localhost:8032"| WebProc
    WebProc --> ModelProc
    ModelProc --> CodexCloud
    ModelProc --> GeminiCloud
    
    style Server fill:#2d3748,stroke:#718096,color:#fff
    style Processes fill:#1a365d,stroke:#4299e1,color:#fff
    style Storage fill:#22543d,stroke:#38a169,color:#fff
    style Config fill:#744210,stroke:#d69e2e,color:#fff
    style Local fill:#553c9a,stroke:#805ad5,color:#fff
    style Internet fill:#2a4365,stroke:#4299e1,color:#fff
    style ModelProc fill:#6b46c1,stroke:#805ad5,color:#fff
    style WebProc fill:#2b6cb0,stroke:#4299e1,color:#fff
```

### 7.2 硬件要求

| 场景 | 最低要求 |
|------|----------|
| 离线推理 | Python 3.10, CUDA GPU, FFmpeg |
| 在线 Demo | **至少 1× NVIDIA A100 GPU** |

### 7.2 安装步骤

```bash
# 1. 安装下载器依赖
python -m pip install 'huggingface_hub>=0.34' 'PyYAML>=6.0'

# 2. 下载模型（选择其一）
python download_models.py --model omni --local-dir .    # 仅 Omni
python download_models.py --model audio --local-dir .   # 仅 Audio
python download_models.py --model all --local-dir .     # 全部

# 3. 安装对应依赖
python -m pip install -r Realtime-Venus-Omni/requirements.txt  # Omni
python -m pip install -r requirements.txt                       # Audio

# 4. Demo 完整安装（Linux）
bash install.sh
```

### 7.3 安装流程

```mermaid
flowchart TD
    Start([开始安装]) --> CheckPython{检查 Python<br/>版本}
    
    CheckPython -->|"< 3.10"| Error1[❌ 需要 Python 3.10+]
    CheckPython -->|">= 3.10"| InstallDeps[安装下载器依赖<br/>pip install huggingface_hub PyYAML]
    
    InstallDeps --> SelectModel{选择模型}
    
    SelectModel -->|Omni| DownloadOmni["download_models.py<br/>--model omni"]
    SelectModel -->|Audio| DownloadAudio["download_models.py<br/>--model audio"]
    SelectModel -->|全部| DownloadAll["download_models.py<br/>--model all"]
    
    DownloadOmni --> InstallOmniDeps["pip install -r<br/>Realtime-Venus-Omni/requirements.txt"]
    DownloadAudio --> InstallAudioDeps["pip install -r<br/>requirements.txt"]
    DownloadAll --> InstallAllDeps["安装所有依赖"]
    
    InstallOmniDeps --> CheckGPU
    InstallAudioDeps --> CheckGPU
    InstallAllDeps --> CheckGPU
    
    CheckGPU{检查 CUDA<br/>GPU} -->|无 GPU| Warning1[⚠️ 仅可离线推理]
    CheckGPU -->|有 GPU| CheckA100{A100?}
    
    CheckA100 -->|是| FullDemo[✅ 可运行完整 Demo]
    CheckA100 -->|否| LimitedDemo[⚠️ 可运行推理示例]
    
    Warning1 --> SelectMode
    FullDemo --> InstallDemo[bash install.sh<br/>安装 Demo 环境]
    LimitedDemo --> SelectMode{选择运行模式}
    
    InstallDemo --> Configure[编辑 config.json<br/>和 harness/config.json]
    Configure --> StartDemo[bash start.sh --config config.json]
    StartDemo --> SSHTunnel[建立 SSH 隧道<br/>ssh -N -L 8032:...]
    SSHTunnel --> OpenBrowser[打开浏览器<br/>http://localhost:8032]
    
    SelectMode -->|离线推理| RunOffline[python frontend/.../offline_chat.py]
    SelectMode -->|在线 Demo| Configure
    
    OpenBrowser --> End([✅ 开始使用])
    RunOffline --> End
    
    style Start fill:#06d6a0,stroke:#118ab2,color:#fff
    style End fill:#06d6a0,stroke:#118ab2,color:#fff
    style Error1 fill:#e63946,stroke:#d62828,color:#fff
    style Warning1 fill:#ffd166,stroke:#118ab2,color:#000
    style LimitedDemo fill:#ffd166,stroke:#118ab2,color:#000
    style FullDemo fill:#06d6a0,stroke:#118ab2,color:#fff
    style CheckPython fill:#457b9d,stroke:#1d3557,color:#fff
    style CheckGPU fill:#457b9d,stroke:#1d3557,color:#fff
    style CheckA100 fill:#457b9d,stroke:#1d3557,color:#fff
    style SelectModel fill:#457b9d,stroke:#1d3557,color:#fff
```

### 7.4 运行方式

#### 离线推理

```bash
# Omni 离线对话
export REALTIME_VENUS_MODEL_PATH=/path/to/Realtime-Venus-Omni
python frontend/Realtime-Venus-Omni/offline_chat.py

# Audio 全双工
python frontend/Realtime-Venus-Audio/audio_duplex_chat.py \
  --model-path /path/to/Realtime-Venus-Audio \
  --audio frontend/Realtime-Venus-Audio/case/case_duplex.wav \
  --output output/duplex_response.wav
```

#### 在线 Demo

```bash
# 启动服务
bash start.sh --config config.json

# 其他命令
bash start.sh --status              # 查看状态
bash start.sh --stop                # 停止服务
bash start.sh --check --no-login    # 预检查
bash start.sh --detach              # 后台启动
```

#### SSH 隧道访问

```bash
# 在本地电脑执行
ssh -N -L 8032:127.0.0.1:8032 user@server
# 然后打开 http://localhost:8032
```

---

## 8. 测试体系

测试文件位于 `tests/` 目录：

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_download_models.py` | 模型下载功能 |
| `test_gemini_provider.py` | Gemini 后端 |
| `test_media_recovery.py` | 媒体恢复 |
| `test_model_modes.py` | 模型模式 |
| `test_progress_opt_in.py` | 进度反馈 |
| `test_spoken_feedback.py` | 语音反馈 |
| `test_web_configuration.py` | Web 配置 |
| `test_workspace_settings.py` | 工作空间设置 |
| `test_deployment_config.py` | 部署配置 |
| `test_codex_login.py` | Codex 登录 |

---

## 9. 关键设计亮点

### 9.1 协议驱动的异步委托

系统使用 XML 风格的协议标记实现对话中的任务委托：

- `<delegate>...</delegate>`：模型输出，标记一个任务委托请求
- `<backend>...</backend>`：Harness 输出，标记返回的任务结果

这种设计让任务委托和结果返回都嵌入在自然对话流中，用户感知上是连续对话。

### 9.2 工作跟踪与交付分离

系统将 **任务完成** 与 **结果播报** 分离跟踪：

- 任务可能在后台完成，但不立即打断对话
- 在合适的输入边界（input boundary）才插入结果
- 播放完成后才标记为 DELIVERED

### 9.3 可插拔的后端架构

`DelegateBackend` 协议支持多种实现：

- **Codex**：默认 General 任务执行器
- **Gemini**：可选的 Routing/Polish/Multimodal 后端
- 可自行实现协议接入其他服务

### 9.4 独立的 Harness 包

Harness 设计为独立可发布的 Python 包：

- 不依赖 Demo、FastAPI 或前端模型权重
- 通过 `pyproject.toml` 独立打包
- 可单独安装用于其他应用

```bash
python -m pip install -e ./harness
```

---

## 10. 依赖关系图

```mermaid
graph TB
    subgraph Config["⚙️ 配置层"]
        RootConfig["config.json<br/>根配置 / Demo 配置"]
        HarnessConfig["harness/config.json<br/>Harness 配置"]
        RootConfig -->|"harness.config 引用"| HarnessConfig
    end
    
    subgraph Backends["🔌 后端层"]
        CodexBE["Codex Agent<br/>默认执行器"]
        GeminiBE["Gemini Backend<br/>可选路由/润色"]
        SkillsBE["Skills Registry<br/>领域技能"]
    end
    
    subgraph Core["🧠 核心层"]
        Harness["DelegateHarness<br/>核心门面"]
        Session["DuplexProtocolSession<br/>会话管理"]
        Scheduler["DelegateScheduler<br/>任务调度"]
        Buffers["ContextBuffers<br/>上下文缓冲"]
        Jobs["JobManager<br/>任务生命周期"]
        Delivery["ResultManager<br/>结果交付"]
        
        Harness --> Session
        Harness --> Scheduler
        Session --> Buffers
        Session --> Jobs
        Jobs --> Delivery
    end
    
    subgraph Bridge["🌉 桥接层"]
        Host["VenusOmniServingHost<br/>模型服务宿主"]
        Serving["VenusOmniServingPort<br/>模型服务端口"]
        Runtime["VenusOmniAgentHarness<br/>运行时组装"]
        
        Host --> Serving
        Runtime --> Host
    end
    
    subgraph Frontend["🎨 前端层"]
        ModelSvc["Omni 模型服务<br/>:8031"]
        WebSvc["Web 服务<br/>:8032"]
        BrowserUI["浏览器 UI<br/>WebSocket"]
    end
    
    HarnessConfig --> CodexBE
    HarnessConfig --> GeminiBE
    HarnessConfig --> SkillsBE
    
    CodexBE --> Harness
    GeminiBE --> Harness
    SkillsBE --> Harness
    
    Runtime --> Harness
    Host --> Harness
    
    ModelSvc --> Serving
    WebSvc --> Host
    BrowserUI <-->|"WebSocket"| WebSvc
    
    style Config fill:#2d3748,stroke:#718096,color:#fff
    style Backends fill:#22543d,stroke:#38a169,color:#fff
    style Core fill:#553c9a,stroke:#805ad5,color:#fff
    style Bridge fill:#744210,stroke:#d69e2e,color:#fff
    style Frontend fill:#2a4365,stroke:#4299e1,color:#fff
```

### 10.1 模块依赖详情

```mermaid
graph LR
    subgraph HarnessCore["harness/core/*"]
        harness_py["harness.py<br/>DelegateHarness"]
        backend_py["backend.py<br/>DelegateBackend Protocol"]
        session_py["session.py<br/>DuplexProtocolSession"]
        models_py["models.py<br/>AudioChunk, VideoFrame"]
    end
    
    subgraph HarnessBridge["harness/bridge/*"]
        host_py["host.py<br/>VenusOmniServingHost"]
        serving_py["serving.py<br/>ServingPort"]
    end
    
    subgraph HarnessAgents["harness/agents/*"]
        codex_py["codex.py<br/>CodexAgentProvider"]
        vision_py["vision.py<br/>视觉处理"]
    end
    
    subgraph HarnessLLM["harness/llm/*"]
        gemini_py["gemini.py<br/>GeminiBackend"]
        planner_py["planner.py<br/>PlannerClient"]
        delegate_py["delegate.py<br/>DirectAndPolish"]
    end
    
    subgraph HarnessJobs["harness/jobs/*"]
        manager_py["manager.py<br/>JobManager"]
        feedback_py["feedback.py<br/>FeedbackHandler"]
    end
    
    harness_py --> backend_py
    harness_py --> session_py
    session_py --> models_py
    
    host_py --> harness_py
    host_py --> serving_py
    
    codex_py --> harness_py
    vision_py --> codex_py
    
    gemini_py --> backend_py
    planner_py --> delegate_py
    
    manager_py --> harness_py
    feedback_py --> manager_py
    
    style HarnessCore fill:#553c9a,stroke:#805ad5,color:#fff
    style HarnessBridge fill:#744210,stroke:#d69e2e,color:#fff
    style HarnessAgents fill:#22543d,stroke:#38a169,color:#fff
    style HarnessLLM fill:#2a4365,stroke:#4299e1,color:#fff
    style HarnessJobs fill:#742a2a,stroke:#e53e3e,color:#fff
```

---

## 11. 文件统计

| 类别 | 数量 |
|------|------|
| Python 源文件 | ~70+ |
| 测试文件 | 10 |
| 配置文件 | 4 (JSON) |
| 文档 (Markdown) | 10+ |
| Shell 脚本 | 2 |

---

## 12. 适用场景

| 场景 | 适合度 | 说明 |
|------|--------|------|
| 实时语音助手 | ★★★★★ | 核心设计目标 |
| 音视频理解 | ★★★★★ | Omni 模型强项 |
| 任务型对话 | ★★★★★ | Harness 异步委托 |
| 长视频交互 | ★★★★☆ | 支持 40 分钟记忆 |
| 纯文本对话 | ★★☆☆☆ | 非主要设计目标 |
| 离线批处理 | ★★★☆☆ | 有示例但非重点 |

---

## 13. 限制与注意事项

1. **硬件要求高**：在线 Demo 需要至少一张 A100 GPU
2. **单会话限制**：当前版本只支持一个活跃对话
3. **网络依赖**：Codex 后端需要网络连接和登录
4. **模型体积大**：9B 参数模型需要较大显存和存储
5. **Gemini 限制**：内联请求超过 20MB 会失败
6. **SSH 隧道**：远程访问需要手动建立 SSH 隧道
7. **Python 版本**：Harness 需要 Python 3.11+，推理示例可用 3.10

---

## 14. 相关资源

| 资源 | 链接 |
|------|------|
| 项目主页 | https://realtime-venus.github.io/ |
| GitHub | https://github.com/inclusionAI/Realtime-Venus |
| Hugging Face | https://huggingface.co/inclusionAI/Realtime-Venus |
| ModelScope | https://www.modelscope.cn/models/inclusionAI/Realtime-Venus |
| 论文 | https://arxiv.org/pdf/2609.13814 |
| Android Demo | [APK 下载](https://github.com/inclusionAI/Realtime-Venus/releases/download/android-beta-0918/Realtime-Venus-0918.apk) |

---

## 15. 引用

```bibtex
@article{zhao2026realtime,
  title={{Realtime-Venus}: A full-duplex interaction system with asynchronous delegation},
  author={{Venus Team(Ant Group), Tsinghua University}},
  journal={arXiv preprint arXiv:2609.13814},
  year={2026}
}
```

---

*本报告由 Claude Opus 5 自动生成，基于项目源码和文档分析。*
