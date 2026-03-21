# 部署指南

本文档详细介绍婴幼儿安全监控系统的多种部署方式。

## 部署前准备

### 系统要求
- **操作系统**: Ubuntu 22.04+ / Debian 11+ / macOS 12+ (推荐 Linux 服务器)
- **Python**: 3.10 或更高版本
- **内存**: 至少 4GB RAM (运行 Ollama 需要额外内存)
- **存储**: 至少 2GB 可用空间
- **网络**: 稳定的互联网连接（访问 API 和下载模型）
- **摄像头**: RTSP 摄像头或 USB 摄像头

### 依赖安装

#### 1. Python 环境
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip git curl wget

# macOS
brew install python@3.10
```

#### 2. 音频支持（可选）
```bash
# Ubuntu/Debian
sudo apt install -y libportaudio2 portaudio19-dev ffmpeg

# macOS
brew install portaudio ffmpeg
```

#### 3. Ollama（本地视觉模型）
```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 启动 Ollama 服务
systemctl --user enable ollama
systemctl --user start ollama

# 下载视觉模型（推荐 qwen3.5，约 7.7GB）
ollama pull qwen3.5

# 验证安装
ollama list
curl http://127.0.0.1:11434/api/tags
```

## 部署方式

### 方式一：手动部署（开发/测试环境）

#### 1. 获取代码
```bash
git clone <repository-url>
cd monitor
```

#### 2. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

#### 3. 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的参数
```

#### 5. 启动系统

**终端 1：启动 QQ 机器人**
```bash
python qq_chat.py
# 或使用包方式
python -m qq_bot.client
```

**终端 2：启动监控程序**
```bash
python img_detect.py
# 或使用包方式
python -m monitor
```

### 方式二：Systemd 服务部署（生产环境）

#### 1. 创建系统用户
```bash
sudo useradd -r -s /bin/false monitor
sudo mkdir -p /opt/monitor
sudo chown -R monitor:monitor /opt/monitor
```

#### 2. 安装应用到系统目录
```bash
sudo cp -r . /opt/monitor/
sudo chown -R monitor:monitor /opt/monitor
cd /opt/monitor
sudo python3 -m venv venv
sudo -u monitor source venv/bin/activate
sudo -u monitor pip install -r requirements.txt
```

#### 3. 创建服务文件

**`/etc/systemd/system/monitor-qqbot.service`**:
```ini
[Unit]
Description=Monitor QQ Bot Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=monitor
Group=monitor
WorkingDirectory=/opt/monitor
Environment="PATH=/opt/monitor/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/monitor/.env
ExecStart=/opt/monitor/venv/bin/python qq_chat.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=monitor-qqbot

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/monitor-detector.service`**:
```ini
[Unit]
Description=Monitor Detector Service
After=network.target monitor-qqbot.service
Wants=network.target

[Service]
Type=simple
User=monitor
Group=monitor
WorkingDirectory=/opt/monitor
Environment="PATH=/opt/monitor/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/monitor/.env
ExecStart=/opt/monitor/venv/bin/python img_detect.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=monitor-detector

[Install]
WantedBy=multi-user.target
```

#### 4. 启用并启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable monitor-qqbot monitor-detector
sudo systemctl start monitor-qqbot monitor-detector

# 查看状态
sudo systemctl status monitor-qqbot monitor-detector

# 查看日志
sudo journalctl -u monitor-qqbot -f
sudo journalctl -u monitor-detector -f
```

### 方式三：Docker 部署（容器化）

#### 1. 创建 Dockerfile
创建 `Dockerfile`（详见下文 Dockerfile 部分）

#### 2. 创建 docker-compose.yml
```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: monitor-ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  qqbot:
    build: .
    container_name: monitor-qqbot
    restart: unless-stopped
    depends_on:
      ollama:
        condition: service_healthy
    ports:
      - "8083:8083"
    volumes:
      - ./.env:/app/.env
      - ./logs:/app/logs
    command: python qq_chat.py
    environment:
      - OLLAMA_API=http://ollama:11434/api/generate

  detector:
    build: .
    container_name: monitor-detector
    restart: unless-stopped
    depends_on:
      - ollama
      - qqbot
    volumes:
      - ./.env:/app/.env
      - ./logs:/app/logs
      - /dev/video0:/dev/video0  # USB 摄像头
      # - /tmp/.X11-unix:/tmp/.X11-unix  # X11 转发（GUI 调试）
    command: python img_detect.py
    devices:
      - /dev/video0:/dev/video0  # USB 摄像头设备
    environment:
      - OLLAMA_API=http://ollama:11434/api/generate
      - DISPLAY=${DISPLAY:-:0}  # X11 显示

volumes:
  ollama_data:
```

#### 3. 构建和运行
```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式四：使用预构建脚本

创建部署脚本 `deploy.sh`:
```bash
#!/bin/bash
set -e

echo "开始部署婴幼儿安全监控系统..."

# 1. 检查系统要求
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3 未安装"
    exit 1
fi

# 2. 创建目录
INSTALL_DIR="/opt/monitor"
echo "安装到: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R $USER:$USER "$INSTALL_DIR"

# 3. 复制文件
cp -r . "$INSTALL_DIR/"
cd "$INSTALL_DIR"

# 4. 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 5. 安装依赖
echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. 配置
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 $INSTALL_DIR/.env 配置文件"
fi

echo "部署完成！"
echo "启动命令:"
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo "  python qq_chat.py  # 终端1"
echo "  python img_detect.py  # 终端2"
```

## Dockerfile

创建 `Dockerfile` 用于容器化部署：

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libportaudio2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 默认命令
CMD ["python", "img_detect.py"]
```

## 配置验证脚本

创建 `validate_config.py` 验证配置：

```python
#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def validate_config():
    errors = []

    # 检查必需配置
    required = ['CAMERA_URL', 'OLLAMA_API', 'MODEL_NAME']
    for key in required:
        if not os.getenv(key):
            errors.append(f"必需配置缺失: {key}")

    # 检查 QQ 配置
    qq_type = os.getenv('QQ_BOT_TYPE', 'official')
    if qq_type == 'official':
        if not os.getenv('QQ_OFFICIAL_APPID') or not os.getenv('QQ_OFFICIAL_SECRET'):
            errors.append("官方机器人模式需要 QQ_OFFICIAL_APPID 和 QQ_OFFICIAL_SECRET")
    elif qq_type == 'napcat':
        if not os.getenv('QQ_BOT_API'):
            errors.append("NapCat 模式需要 QQ_BOT_API")

    # 检查 TTS 配置
    if os.getenv('TTS_ENABLE', 'true').lower() == 'true':
        if not os.getenv('TTS_API_KEY'):
            errors.append("启用 TTS 需要 TTS_API_KEY")

    return errors

if __name__ == '__main__':
    errors = validate_config()
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("配置验证通过")
```

## 监控和维护

### 日志管理
- 日志文件位置: `logs/` 目录（如果启用文件日志）
- Systemd 日志: `journalctl -u monitor-*`
- Docker 日志: `docker-compose logs`

### 性能监控
```bash
# 查看进程状态
top -p $(pgrep -f "python.*(qq_chat|img_detect)")

# 查看内存使用
ps aux | grep python | grep -v grep

# 查看网络连接
ss -tunlp | grep python
```

### 故障排除
1. **摄像头连接失败**: 检查 `CAMERA_URL`，确保网络可达
2. **Ollama 调用失败**: 验证 Ollama 服务状态和模型下载
3. **QQ 消息发送失败**: 检查机器人进程和用户会话
4. **TTS 播放失败**: 确认音频设备和 API 密钥

### 备份和恢复
```bash
# 备份配置
tar -czf monitor-backup-$(date +%Y%m%d).tar.gz \
    .env \
    logs/ \
    config/

# 恢复配置
tar -xzf monitor-backup-YYYYMMDD.tar.gz
```

## 安全注意事项

1. **API 密钥安全**: 不要提交 `.env` 文件到版本控制
2. **网络隔离**: 生产环境应使用内网摄像头流
3. **权限最小化**: 使用非 root 用户运行服务
4. **日志轮转**: 配置日志轮转避免磁盘满
5. **定期更新**: 更新依赖包和安全补丁

## 升级指南

```bash
# 1. 备份当前配置
cp .env .env.backup

# 2. 获取最新代码
git pull origin main

# 3. 更新依赖
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. 重启服务
sudo systemctl restart monitor-qqbot monitor-detector
```

## 支持与反馈

- 问题报告: GitHub Issues
- 文档更新: 提交 Pull Request
- 紧急支持: 查看系统日志和错误信息