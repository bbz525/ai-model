# 部署检查清单

## 部署前检查

### ✅ 系统要求
- [ ] 操作系统: Ubuntu 22.04+/Debian 11+/macOS 12+
- [ ] Python 3.10+ 已安装 (`python3 --version`)
- [ ] 至少 4GB RAM 可用
- [ ] 至少 2GB 磁盘空间
- [ ] 网络连接正常

### ✅ 摄像头准备
- [ ] 确定摄像头类型: RTSP / USB
- [ ] RTSP 摄像头: 获取流地址 (rtsp://...)
- [ ] USB 摄像头: 确认设备路径 (`/dev/video0`)
- [ ] 测试摄像头连接:
  ```bash
  # RTSP 测试
  ffplay rtsp://your_camera_url

  # USB 摄像头测试
  ffplay /dev/video0
  ```

### ✅ 依赖安装
- [ ] 系统依赖:
  ```bash
  # Ubuntu/Debian
  sudo apt install python3-pip python3-venv git curl wget

  # 音频支持 (可选)
  sudo apt install libportaudio2 portaudio19-dev ffmpeg
  ```

### ✅ Ollama 设置
- [ ] 安装 Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
- [ ] 启动服务: `systemctl --user start ollama`
- [ ] 下载模型: `ollama pull qwen3.5` (约 7.7GB)
- [ ] 验证:
  ```bash
  ollama list
  curl http://127.0.0.1:11434/api/tags
  ```

## 配置步骤

### ✅ 获取代码
```bash
git clone <repository-url>
cd monitor
```

### ✅ 配置文件
- [ ] 复制配置模板: `cp .env.example .env`
- [ ] 编辑 `.env` 文件，设置以下关键参数:

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `CAMERA_URL` | 摄像头地址 | `rtsp://admin:password@192.168.1.100:554` 或 `0` (USB) |
| `OLLAMA_API` | Ollama API | `http://127.0.0.1:11434/api/generate` |
| `MODEL_NAME` | 视觉模型 | `qwen3.5` |
| `QQ_BOT_TYPE` | QQ机器人模式 | `official` 或 `napcat` |
| `QQ_OFFICIAL_APPID` | 官方APPID | (QQ开放平台获取) |
| `QQ_OFFICIAL_SECRET` | 官方SECRET | (QQ开放平台获取) |
| `TTS_API_KEY` | TTS API密钥 | (MiMo TTS 获取) |

### ✅ 验证配置
```bash
python validate_config.py
```
- [ ] 无错误输出
- [ ] 警告信息已检查

## 部署方式选择

### 方式一: 手动部署 (推荐测试)
- [ ] 创建虚拟环境: `python3 -m venv venv`
- [ ] 激活环境: `source venv/bin/activate`
- [ ] 安装依赖: `pip install -r requirements.txt`
- [ ] 运行验证: `python validate_config.py`

**启动:**
- 终端1: `python qq_chat.py`
- 终端2: `python img_detect.py`

### 方式二: Systemd 服务 (生产环境)
- [ ] 运行部署脚本: `sudo ./deploy.sh -m systemd`
- [ ] 检查服务状态:
  ```bash
  sudo systemctl status monitor-qqbot monitor-detector
  ```
- [ ] 查看日志:
  ```bash
  sudo journalctl -u monitor-qqbot -f
  sudo journalctl -u monitor-detector -f
  ```

### 方式三: Docker 部署
- [ ] 安装 Docker 和 docker-compose
- [ ] 运行部署脚本: `./deploy.sh -m docker`
- [ ] 构建镜像: `docker-compose build`
- [ ] 启动服务: `docker-compose up -d`
- [ ] 验证运行: `docker-compose ps`

## 部署后验证

### ✅ 功能测试
1. **摄像头连接**
   - [ ] 监控程序启动无报错
   - [ ] 控制台显示帧率信息

2. **运动检测**
   - [ ] 在摄像头前移动，触发运动检测
   - [ ] 控制台显示 "检测到移动" 日志

3. **AI 分析**
   - [ ] 运动后触发 Ollama 调用
   - [ ] 控制台显示 AI 分析结果

4. **QQ 通知**
   - [ ] 触发告警后收到 QQ 消息
   - [ ] 消息包含截图和文字描述

5. **TTS 语音** (如启用)
   - [ ] 触发告警后听到语音播报
   - [ ] 不同告警级别有不同语调

### ✅ 性能监控
- [ ] CPU 使用率正常 (<80%)
- [ ] 内存使用稳定
- [ ] 网络连接正常
- [ ] 日志无错误信息

## 故障排除

### ❌ 摄像头连接失败
- 检查 `CAMERA_URL` 格式
- 确认网络可达性
- 测试: `ffplay <camera_url>`

### ❌ Ollama 调用失败
- 确认 Ollama 服务运行: `systemctl --user status ollama`
- 检查模型是否下载: `ollama list`
- 测试 API: `curl http://127.0.0.1:11434/api/tags`

### ❌ QQ 消息发送失败
- 检查 QQ 机器人进程是否运行
- 确认配置文件正确
- 查看 QQ 机器人日志

### ❌ TTS 播放失败
- 确认 API 密钥有效
- 检查音频设备
- 查看 TTS 模块日志

## 维护任务

### 日常维护
- [ ] 检查日志文件
- [ ] 监控系统资源
- [ ] 备份配置文件

### 定期更新
- [ ] 更新 Python 包: `pip install -r requirements.txt --upgrade`
- [ ] 更新 Ollama 模型: `ollama pull qwen3.5`
- [ ] 检查安全更新

### 备份恢复
- [ ] 备份 `.env` 配置文件
- [ ] 备份自定义配置
- [ ] 定期测试恢复流程

## 紧急情况

### 系统宕机
1. 检查服务状态: `systemctl status monitor-*`
2. 查看最新日志: `journalctl -u monitor-* --since "5 minutes ago"`
3. 重启服务: `systemctl restart monitor-qqbot monitor-detector`

### 摄像头故障
1. 切换到备用摄像头 (修改 `CAMERA_URL`)
2. 检查网络连接
3. 重启摄像头设备

### 性能问题
1. 降低帧率: 增加 `DETECT_AFTER_MOTION` 值
2. 降低分辨率: 减小 `FRAME_RESIZE`
3. 优化检测参数: 调整 `MIN_AREA`, `THRESHOLD`

---

**部署完成标志**: 所有 ✅ 项目已检查，功能测试通过。

**支持**: 遇到问题请参考:
- `README.md` - 项目概述和快速开始
- `DEPLOYMENT.md` - 详细部署指南
- GitHub Issues - 问题报告