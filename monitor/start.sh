#!/bin/bash
set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}婴幼儿安全监控系统 - 快速启动${NC}"
echo "=" * 40

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，请先运行部署脚本或:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "配置文件 .env 不存在，使用示例配置..."
    cp .env.example .env
    echo "请编辑 .env 文件配置必要参数"
    exit 1
fi

# 验证配置
echo "验证配置文件..."
python validate_config.py

# 检查 Ollama 服务
echo "检查 Ollama 服务..."
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "警告: Ollama 服务未运行"
    echo "请启动: ollama serve"
    echo "或安装: curl -fsSL https://ollama.com/install.sh | sh"
fi

# 显示启动选项
echo ""
echo -e "${GREEN}选择启动方式:${NC}"
echo "1. 完整启动 (QQ机器人 + 监控程序)"
echo "2. 仅启动 QQ机器人"
echo "3. 仅启动监控程序"
echo "4. 在后台运行"
echo "5. 退出"
echo ""

read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo "启动完整系统..."
        echo "终端1: QQ机器人 (Ctrl+C 停止)"
        echo "终端2: 监控程序 (Ctrl+C 停止)"
        echo ""
        echo "请打开两个终端分别运行:"
        echo "终端1: source venv/bin/activate && python qq_chat.py"
        echo "终端2: source venv/bin/activate && python img_detect.py"
        ;;
    2)
        echo "启动 QQ机器人..."
        python qq_chat.py
        ;;
    3)
        echo "启动监控程序..."
        python img_detect.py
        ;;
    4)
        echo "在后台运行..."
        nohup python qq_chat.py > qqbot.log 2>&1 &
        echo "QQ机器人已启动 (PID: $!), 日志: qqbot.log"

        sleep 2

        nohup python img_detect.py > detector.log 2>&1 &
        echo "监控程序已启动 (PID: $!), 日志: detector.log"

        echo ""
        echo "查看日志:"
        echo "  tail -f qqbot.log"
        echo "  tail -f detector.log"
        echo "停止服务:"
        echo "  pkill -f \"python.*(qq_chat|img_detect)\""
        ;;
    5)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac