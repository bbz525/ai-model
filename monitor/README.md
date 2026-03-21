# 婴幼儿安全监控系统

基于计算机视觉和本地大语言模型的婴幼儿安全监控系统，实时检测摄像头画面中的危险行为（如逃离、危险物品接触、跌落风险等），并通过QQ机器人和TTS语音进行告警。

## 功能特性

- **实时监控**：通过OpenCV连接RTSP/USB摄像头，实时分析视频流
- **智能检测**：结合运动检测（背景差分）和本地Ollama视觉模型（Qwen3.5），准确识别危险行为
- **多通道告警**：
  - QQ官方机器人/QQ群消息推送
  - TTS语音播报（MiMo-V2-TTS API）
  - 控制台实时日志
- **模块化架构**：清晰的包结构，便于扩展和维护
- **配置驱动**：全部参数通过环境变量控制，无需修改代码

## 快速开始

### 环境要求

- Python 3.10+
- [Ollama](https://ollama.com/)（运行本地视觉模型）
- 摄像头（RTSP流或USB摄像头）
- QQ Open Platform账号（如需使用官方机器人）

### 安装

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd monitor
   ```

2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 安装音频播放依赖（可选）：
   ```bash
   # macOS
   brew install portaudio
   # Ubuntu/Debian
   sudo apt-get install libportaudio2 portaudio19-dev
   ```

### 配置

1. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```

2. 编辑`.env`文件，设置必要的参数：
   - `CAMERA_URL`：摄像头流地址（RTSP URL或`0`表示USB摄像头）
   - `OLLAMA_API`：本地Ollama API地址（默认`http://127.0.0.1:11434/api/generate`）
   - `MODEL_NAME`：Ollama中的视觉模型名称（如`qwen3.5`）
   - `TTS_API_KEY`：MiMo TTS API密钥（如需语音告警）
   - QQ机器人相关配置（选择官方或NapCat模式）

### 运行

系统有两个独立组件：

#### 1. 运行QQ机器人（如需官方机器人模式）

```bash
python qq_chat.py
```

#### 2. 运行主监控程序

```bash
python img_detect.py
```

## 项目结构

```
monitor/
├── monitor/              # 核心模块包
│   ├── config.py        # 配置加载（从.env读取）
│   ├── detection/       # 检测相关
│   │   ├── camera.py   # 摄像头连接/重连
│   │   ├── motion.py   # 运动检测算法
│   │   └── ollama.py   # Ollama API调用
│   ├── notification/    # 通知相关
│   │   ├── qq.py       # QQ消息发送
│   │   ├── dispatcher.py # 告警分发器
│   │   └── base.py     # 通知基类
│   └── tts/            # 语音合成
│       ├── base.py     # AlertLevel/TTSProvider协议
│       ├── mimo.py     # MiMo TTS客户端
│       └── voice.py    # 语音播报管理器
├── qq_bot/             # QQ机器人服务
│   └── client.py       # botpy客户端+HTTP接口
├── img_detect.py       # 主程序入口（精简版）
├── qq_chat.py          # QQ机器人入口（精简版）
├── mimo_tts_demo.py    # TTS演示脚本
├── respApi.py          # OpenAI API测试脚本
├── requirements.txt    # Python依赖
├── .env.example        # 环境变量模板
└── CLAUDE.md          # Claude Code助手指南
```

## 配置详解

### 摄像头配置
- `CAMERA_URL`：摄像头流地址（RTSP格式如`rtsp://username:password@ip:port/stream`或`0`为USB摄像头）
- `RECONNECT_INTERVAL`：重连间隔（秒）
- `MAX_RECONNECT_ATTEMPTS`：最大重试次数（`0`表示无限重试）

### 运动检测调优
- `MIN_AREA`：最小移动区域（越小越灵敏，默认500）
- `THRESHOLD`：像素变化阈值（值越小越灵敏，默认25）
- `FRAME_RESIZE`：帧缩放宽度（降低分辨率提升性能，默认500）

### Ollama配置
- `MODEL_NAME`：视觉模型名称（支持`qwen3.5`、`qwen-vl`等）
- `DETECT_AFTER_MOTION`：检测到移动后的延迟时间（秒，避免误触发）
- `OLLAMA_TIMEOUT`：API调用超时（秒）
- `OLLAMA_MAX_RETRIES`：失败重试次数

### QQ机器人模式

#### 方案1：官方机器人（推荐）
需要QQ Open Platform开发者账号，支持单聊消息推送：
- `QQ_BOT_TYPE=official`
- 设置`QQ_OFFICIAL_APPID`、`QQ_OFFICIAL_SECRET`
- 用户首次给机器人发消息后，从日志获取`QQ_OFFICIAL_USER_ID`

#### 方案2：NapCat/go-cqhttp（备用）
使用第三方QQ客户端，支持群消息：
- `QQ_BOT_TYPE=napcat`
- 设置`QQ_BOT_API`（NapCat HTTP接口地址）
- 设置`QQ_GROUP_ID`（目标群号）

### TTS语音配置
- `TTS_API_KEY`：MiMo-V2-TTS API密钥
- `TTS_BASE_URL`：API地址（默认`https://www.dmxapi.cn/v1`）
- `TTS_ENABLE`：是否启用语音告警
- `TTS_MIN_LEVEL`：最低播报级别（`info`/`warning`/`error`/`critical`）
- `TTS_REPEAT`：重复播报次数

## 工作原理

1. **连接摄像头**：通过OpenCV连接视频流，支持断线重连
2. **运动检测**：对比连续帧的像素差异，识别画面变化
3. **AI分析**：检测到移动后，捕获当前帧并发送给本地Ollama模型
4. **危险评估**：Ollama根据预设提示词分析画面，返回JSON格式结果（状态、置信度、风险等级）
5. **告警分发**：根据风险等级，触发不同渠道的告警：
   - 控制台实时日志
   - QQ消息推送（图文）
   - TTS语音播报（不同语调、重复次数）

## 扩展开发

### 添加新的检测类型
修改`DETECTION_PROMPT`环境变量中的提示词，调整危险行为判定标准。

### 集成其他通知渠道
继承`monitor.notification.base.NotificationProvider`协议，实现新的通知类。

### 更换TTS提供商
实现`monitor.tts.base.TTSProvider`协议，创建新的TTS客户端。

## 故障排除

### 摄像头连接失败
- 检查`CAMERA_URL`格式是否正确
- 确认网络可达性和权限
- 尝试使用`0`（USB摄像头）测试

### Ollama调用失败
- 确认Ollama服务正在运行：`ollama serve`
- 检查模型是否已下载：`ollama list`
- 验证API地址：`curl http://127.0.0.1:11434/api/tags`

### QQ消息发送失败
- 官方模式：检查`qq_chat.py`是否运行，用户是否已激活会话
- NapCat模式：确认NapCat/go-cqhttp服务已启动
- 检查环境变量配置是否正确

### 语音播报失败
- 确认`TTS_API_KEY`有效
- 检查音频设备是否可用（或切换为文件输出模式）
- 安装`portaudio`系统依赖

## 许可证

[MIT License](LICENSE)

## 部署文档

详细部署指南请参考 [DEPLOYMENT.md](DEPLOYMENT.md)，包含：
- 系统要求和依赖安装
- 多种部署方式：手动、Systemd服务、Docker容器
- 配置验证和故障排除
- 监控和维护指南

快速检查清单: [CHECKLIST.md](CHECKLIST.md)

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交Issue和Pull Request。