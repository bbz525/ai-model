# DeepSeek-Coder-V2-Lite-Instruct 微调指南

本项目提供了多种微调 DeepSeek-Coder-V2-Lite-Instruct 模型的方法，以及将微调后的模型部署到 vLLM 的方案。

## ⚠️ Mac 用户注意

**Mac 系统（Intel / Apple Silicon）不支持以下工具：**
- ❌ Unsloth（需要 NVIDIA CUDA）
- ❌ bitsandbytes 量化（需要 CUDA）
- ❌ vLLM（需要 CUDA）

**Mac 用户请使用以下文件：**
- `mac_finetune.py` - Mac 优化的微调脚本
- `mac_inference.py` - Mac 上的模型推理（替代 vLLM）
- `mac_setup.sh` - Mac 环境一键设置脚本

## 📁 文件结构

```
training/
├── unsloth_finetune.py       # 使用 Unsloth 高效微调（推荐，仅 CUDA）
├── trl_finetune.py           # 使用 TRL SFTTrainer 微调（仅 CUDA）
├── llamafactory_finetune.sh  # 使用 LlamaFactory 一键微调（仅 CUDA）
├── deploy_to_vllm.py         # 部署微调后的模型到 vLLM（仅 CUDA）
├── mac_finetune.py           # Mac 微调脚本（Intel/Apple Silicon）
├── mac_inference.py          # Mac 模型推理脚本
├── mac_setup.sh              # Mac 环境设置脚本
├── prepare_dataset.py        # 数据集准备工具
├── requirements.txt          # 依赖包
└── README.md                 # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备数据集

使用 `prepare_dataset.py` 创建或转换您的数据集：

```bash
python prepare_dataset.py
```

支持的数据格式：
- 指令格式：`{"instruction": "...", "input": "...", "output": "..."}`
- 对话格式：`{"messages": [{"role": "...", "content": "..."}]}`
- ShareGPT 格式

### 3. 选择微调方式

#### 方式一：Unsloth（推荐）

最快、最省显存的方案：

```bash
python unsloth_finetune.py
```

**优势**：
- 训练速度提升 2-5 倍
- 显存占用减少 50-80%
- 支持长序列训练

#### 方式二：TRL SFTTrainer

更通用的方案：

```bash
python trl_finetune.py
```

**优势**：
- Hugging Face 官方库
- 文档完善，社区活跃
- 支持多种训练策略

#### 方式三：LlamaFactory

一键式微调：

```bash
bash llamafactory_finetune.sh
```

**优势**：
- 配置简单
- 支持多种模型
- 内置多种数据集

## 📊 微调参数说明

### LoRA 参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `r` | LoRA 秩 | 8-64 |
| `lora_alpha` | 缩放参数 | 16-128 |
| `lora_dropout` | Dropout 率 | 0-0.1 |
| `target_modules` | 应用 LoRA 的模块 | q_proj, v_proj 等 |

### 训练参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `learning_rate` | 学习率 | 1e-4 ~ 5e-4 |
| `num_train_epochs` | 训练轮数 | 3-5 |
| `batch_size` | 批次大小 | 根据显存调整 |
| `max_seq_length` | 最大序列长度 | 2048-4096 |

## 🎯 部署到 vLLM

### 加载合并后的模型

```python
from vllm import LLM

llm = LLM(model="./finetuned_deepseek_coder_merged", trust_remote_code=True)
```

### 基础模型 + LoRA 适配器

```python
from vllm import LLM

llm = LLM(
    model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    enable_lora=True,
    trust_remote_code=True
)
```

### 启动 API 服务

```bash
# 合并后的模型
python -m vllm.entrypoints.openai.api_server \
    --model ./finetuned_deepseek_coder_merged \
    --trust-remote-code

# 带 LoRA 支持
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
    --enable-lora \
    --lora-modules my_lora=./finetuned_deepseek_coder \
    --trust-remote-code
```

## 💡 最佳实践

1. **数据质量**：准备高质量、多样化的训练数据
2. **学习率**：从较小的学习率开始（如 2e-4）
3. **验证集**：保留部分数据用于验证，防止过拟合
4. **检查点**：定期保存模型检查点
5. **量化**：如需进一步减小模型，可在微调后进行 FP8/INT8 量化

## 📚 参考资源

- [Unsloth 文档](https://docs.unsloth.ai/)
- [TRL 文档](https://huggingface.co/docs/trl/)
- [LlamaFactory GitHub](https://github.com/hiyouga/LLaMA-Factory)
- [vLLM 文档](https://docs.vllm.ai/)
