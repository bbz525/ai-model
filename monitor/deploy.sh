#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "命令 '$1' 未安装"
        return 1
    fi
    return 0
}

# 显示使用帮助
show_help() {
    cat << EOF
婴幼儿安全监控系统部署脚本

用法: $0 [选项]

选项:
  -h, --help          显示此帮助信息
  -d, --dir DIR       安装目录 (默认: /opt/monitor)
  -u, --user USER     运行用户 (默认: monitor)
  -m, --mode MODE     部署模式: manual, systemd, docker (默认: manual)
  --no-venv           不使用虚拟环境 (直接安装到系统)
  --skip-deps         跳过依赖检查
  --skip-config       跳过配置验证

示例:
  $0                    # 手动部署到当前目录
  $0 -d /opt/monitor    # 部署到指定目录
  $0 -m systemd         # 使用 systemd 服务部署
  $0 -m docker          # 使用 Docker 部署

部署模式说明:
  manual   手动部署，创建虚拟环境，输出启动命令
  systemd  创建系统服务，自动启动
  docker   生成 Docker 配置，不实际部署
EOF
}

# 默认参数
INSTALL_DIR="$(pwd)"
RUN_USER="monitor"
DEPLOY_MODE="manual"
USE_VENV=true
SKIP_DEPS=false
SKIP_CONFIG=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -u|--user)
            RUN_USER="$2"
            shift 2
            ;;
        -m|--mode)
            DEPLOY_MODE="$2"
            shift 2
            ;;
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-config)
            SKIP_CONFIG=true
            shift
            ;;
        *)
            error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主部署函数
deploy_manual() {
    info "开始手动部署..."

    # 检查目录
    if [ ! -d "$INSTALL_DIR" ]; then
        info "创建安装目录: $INSTALL_DIR"
        mkdir -p "$INSTALL_DIR"
    fi

    # 复制文件
    info "复制文件到安装目录..."
    cp -r . "$INSTALL_DIR/"
    cd "$INSTALL_DIR"

    # 创建虚拟环境
    if [ "$USE_VENV" = true ]; then
        info "创建 Python 虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
    fi

    # 安装依赖
    if [ "$SKIP_DEPS" = false ]; then
        info "安装 Python 依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
    fi

    # 验证配置
    if [ "$SKIP_CONFIG" = false ]; then
        info "验证配置文件..."
        if [ -f .env ]; then
            python validate_config.py
        else
            warning "配置文件 .env 不存在，使用示例配置"
            cp .env.example .env
            echo "请编辑 $INSTALL_DIR/.env 文件配置参数"
        fi
    fi

    success "手动部署完成！"

    # 显示启动命令
    echo ""
    info "启动命令:"
    if [ "$USE_VENV" = true ]; then
        echo "  cd $INSTALL_DIR"
        echo "  source venv/bin/activate"
    else
        echo "  cd $INSTALL_DIR"
    fi
    echo "  # 终端1 - QQ机器人:"
    echo "  python qq_chat.py"
    echo "  # 终端2 - 监控程序:"
    echo "  python img_detect.py"
    echo ""
    info "或使用包方式启动:"
    echo "  python -m qq_bot.client  # QQ机器人"
    echo "  python -m monitor        # 监控程序"
}

deploy_systemd() {
    info "开始 Systemd 服务部署..."

    # 检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        error "Systemd 部署需要 root 权限"
        echo "请使用 sudo 运行: sudo $0 -m systemd"
        exit 1
    fi

    # 检查安装目录
    if [ "$INSTALL_DIR" = "$(pwd)" ]; then
        INSTALL_DIR="/opt/monitor"
        info "使用默认安装目录: $INSTALL_DIR"
    fi

    # 创建系统用户
    if ! id "$RUN_USER" &>/dev/null; then
        info "创建系统用户: $RUN_USER"
        useradd -r -s /bin/false "$RUN_USER"
    fi

    # 创建目录并设置权限
    info "设置安装目录: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    chown -R "$RUN_USER:$RUN_USER" "$INSTALL_DIR"

    # 复制文件
    info "复制文件..."
    cp -r . "$INSTALL_DIR/"
    cd "$INSTALL_DIR"
    chown -R "$RUN_USER:$RUN_USER" .

    # 创建虚拟环境
    if [ "$USE_VENV" = true ]; then
        info "创建虚拟环境..."
        sudo -u "$RUN_USER" python3 -m venv venv
        sudo -u "$RUN_USER" bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    fi

    # 验证配置
    if [ "$SKIP_CONFIG" = false ]; then
        info "验证配置文件..."
        if [ ! -f .env ]; then
            cp .env.example .env
            chown "$RUN_USER:$RUN_USER" .env
            warning "已创建示例配置文件，请编辑 $INSTALL_DIR/.env"
        fi
        sudo -u "$RUN_USER" bash -c "source venv/bin/activate && python validate_config.py" || {
            warning "配置验证有警告，请检查 .env 文件"
        }
    fi

    # 安装服务文件
    info "安装 Systemd 服务文件..."
    cp monitor-qqbot.service /etc/systemd/system/
    cp monitor-detector.service /etc/systemd/system/

    # 更新服务文件中的路径和用户
    sed -i "s|/opt/monitor|$INSTALL_DIR|g" /etc/systemd/system/monitor-*.service
    sed -i "s|User=monitor|User=$RUN_USER|g" /etc/systemd/system/monitor-*.service
    sed -i "s|Group=monitor|Group=$RUN_USER|g" /etc/systemd/system/monitor-*.service

    # 重新加载 systemd
    info "重新加载 Systemd..."
    systemctl daemon-reload

    # 启用并启动服务
    info "启用服务..."
    systemctl enable monitor-qqbot monitor-detector

    info "启动服务..."
    systemctl start monitor-qqbot monitor-detector

    # 检查服务状态
    info "检查服务状态..."
    sleep 2
    systemctl status monitor-qqbot --no-pager
    echo ""
    systemctl status monitor-detector --no-pager

    success "Systemd 服务部署完成！"

    # 显示管理命令
    echo ""
    info "服务管理命令:"
    echo "  查看状态: sudo systemctl status monitor-qqbot monitor-detector"
    echo "  查看日志: sudo journalctl -u monitor-qqbot -f"
    echo "           sudo journalctl -u monitor-detector -f"
    echo "  重启服务: sudo systemctl restart monitor-qqbot monitor-detector"
    echo "  停止服务: sudo systemctl stop monitor-qqbot monitor-detector"
    echo ""
    info "配置文件位置: $INSTALL_DIR/.env"
    info "日志文件位置: $INSTALL_DIR/logs/"
}

deploy_docker() {
    info "开始 Docker 部署配置..."

    # 检查 Docker
    check_command docker || {
        error "Docker 未安装，请先安装 Docker"
        echo "安装参考: https://docs.docker.com/engine/install/"
        exit 1
    }

    check_command docker-compose || {
        error "docker-compose 未安装"
        echo "安装: sudo apt install docker-compose 或 pip install docker-compose"
        exit 1
    }

    # 验证配置
    if [ "$SKIP_CONFIG" = false ]; then
        info "验证配置文件..."
        if [ ! -f .env ]; then
            cp .env.example .env
            warning "已创建示例配置文件，请编辑 .env"
        fi
        python validate_config.py || {
            warning "配置验证有警告，请检查 .env 文件"
        }
    fi

    # 创建必要的目录
    info "创建日志目录..."
    mkdir -p logs

    # 显示 Docker 命令
    success "Docker 配置完成！"

    echo ""
    info "Docker 命令:"
    echo "  构建镜像: docker-compose build"
    echo "  启动所有服务: docker-compose up -d"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  查看状态: docker-compose ps"
    echo ""
    info "单独启动服务:"
    echo "  仅启动 Ollama: docker-compose up -d ollama"
    echo "  启动 QQ机器人: docker-compose up -d qqbot"
    echo "  启动监控程序: docker-compose up -d detector"
    echo ""
    info "注意事项:"
    echo "  1. 确保 .env 文件已正确配置"
    echo "  2. 如需 USB 摄像头，确保设备权限正确"
    echo "  3. 首次启动会下载 Ollama 镜像，可能需要较长时间"
    echo "  4. 如需修改配置，更新 .env 后重启服务: docker-compose restart"
}

# 主程序
main() {
    echo ""
    info "婴幼儿安全监控系统部署脚本"
    echo "=" * 50

    # 显示部署信息
    echo "部署模式: $DEPLOY_MODE"
    echo "安装目录: $INSTALL_DIR"
    echo "运行用户: $RUN_USER"
    echo "使用虚拟环境: $USE_VENV"
    echo ""

    # 检查基本命令
    info "检查系统要求..."
    check_command python3 || exit 1
    check_command pip3 || exit 1

    # 根据模式部署
    case $DEPLOY_MODE in
        manual)
            deploy_manual
            ;;
        systemd)
            deploy_systemd
            ;;
        docker)
            deploy_docker
            ;;
        *)
            error "未知部署模式: $DEPLOY_MODE"
            show_help
            exit 1
            ;;
    esac

    echo ""
    success "部署流程完成！"
    info "详细文档请参考 DEPLOYMENT.md"
}

# 运行主程序
main "$@"