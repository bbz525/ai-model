#!/bin/bash
# Mac 系统环境设置脚本

echo "=== Mac 微调环境设置 ==="
echo ""

# 检测 Mac 类型
if [[ $(uname -m) == "arm64" ]]; then
    echo "检测到 Apple Silicon Mac (M1/M2/M3)"
    DEVICE="mps"
else
    echo "检测到 Intel Mac"
    DEVICE="cpu"
fi

echo ""
echo "=== 安装 PyTorch ==="
# Apple Silicon Mac
if [[ $DEVICE == "mps" ]]; then
    echo "为 Apple Silicon 安装 PyTorch..."
    pip install torch torchvision torchaudio
else
    # Intel Mac
    echo "为 Intel Mac 安装 PyTorch..."
    pip install torch torchvision torchaudio
fi

echo ""
echo "=== 安装其他依赖 ==="
pip install transformers>=4.40.0
pip install datasets>=2.14.0
pip install accelerate>=0.25.0
pip install peft>=0.8.0
pip install trl>=0.8.0
pip install optimum>=1.16.0
pip install sentencepiece>=0.1.99
pip install protobuf>=3.20.0

echo ""
echo "=== 验证安装 ==="
python3 << EOF
import torch
print(f"PyTorch 版本: {torch.__version__}")
print(f"MPS 可用: {torch.backends.mps.is_available()}")
if torch.backends.mps.is_available():
    print("✅ 可以使用 Apple Silicon GPU 加速")
else:
    print("⚠️  使用 CPU 模式（训练较慢）")
EOF

echo ""
echo "=== 安装完成 ==="
echo "提示: Mac 上不支持以下工具："
echo "  - Unsloth (需要 CUDA)"
echo "  - bitsandbytes 量化 (需要 CUDA)"
echo "  - vLLM (需要 CUDA)"
echo ""
echo "使用方式:"
echo "  1. 准备数据: python prepare_dataset.py"
echo "  2. 开始训练: python mac_finetune.py"
echo "  3. 模型推理: python mac_inference.py"
