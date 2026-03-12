"""
Mac 系统上的微调脚本 (Intel / Apple Silicon)
适用于 macOS，支持 CPU 和 MPS (Metal Performance Shaders)
"""

import torch
import platform
import transformers
from packaging import version

# 检查 Transformers 版本
TRANSFORMERS_VERSION = version.parse(transformers.__version__)
MIN_REQUIRED_VERSION = version.parse("4.38.0")

if TRANSFORMERS_VERSION < MIN_REQUIRED_VERSION:
    print(f"⚠️  警告: 当前 Transformers 版本 {TRANSFORMERS_VERSION}")
    print(f"   DeepSeek-Coder-V2 需要版本 >= {MIN_REQUIRED_VERSION}")
    print("   请运行: pip install transformers --upgrade")
    print("")
    response = input("是否继续尝试? (y/n): ").strip().lower()
    if response != 'y':
        exit(1)

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import load_dataset

# 检测 Mac 类型和可用设备
def get_device():
    """检测最佳可用设备"""
    if torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    else:
        return "cpu"  # Intel Mac 或 CPU 模式

device = get_device()
print(f"系统: {platform.system()}")
print(f"处理器: {platform.processor()}")
print(f"使用设备: {device}")

# 配置参数
# 如果 DeepSeek-Coder-V2 加载失败，可以改用 "deepseek-ai/deepseek-coder-1.3b-instruct"（对旧版 Transformers 更友好）
MODEL_NAME = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
# MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"  # 备选方案
OUTPUT_DIR = "./finetuned_deepseek_mac"
MAX_SEQ_LENGTH = 1024  # Mac 上建议减小序列长度以节省内存

# 1. 加载模型和分词器（Mac 优化版本）
print("加载模型...")

# 根据设备选择加载方式
if device == "mps":
    # Apple Silicon - 使用 MPS
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,  # MPS 支持 float16
        device_map="mps",
        trust_remote_code=True,
    )
else:
    # Intel Mac - 使用 CPU，建议加载 8-bit 量化版本节省内存
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 2. 配置 LoRA（参数高效微调）
print("配置 LoRA...")
peft_config = LoraConfig(
    r=8,  # Mac 上建议减小秩以降低内存占用
    lora_alpha=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 3. 准备数据集
def format_chat_template(example):
    """格式化对话数据"""
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": example["instruction"] + (f"\n\n{example['input']}" if example.get("input") else "")},
        {"role": "assistant", "content": example["output"]},
    ]
    
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}

# 加载示例数据集（请替换为您自己的数据）
print("加载数据集...")
dataset = load_dataset("yahma/alpaca-cleaned", split="train[:500]")  # Mac 上使用更少样本
dataset = dataset.map(format_chat_template, remove_columns=dataset.column_names)

# 4. 配置训练参数（Mac 优化）
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,  # Mac 上建议减少轮数
    per_device_train_batch_size=1,  # Mac 上只能使用 batch_size=1
    gradient_accumulation_steps=4,
    warmup_steps=50,
    learning_rate=1e-4,  # Mac 上建议降低学习率
    fp16=False,  # Mac 上不使用 fp16
    bf16=False,
    logging_steps=10,
    optim="adamw_torch",  # Mac 上使用标准 AdamW
    weight_decay=0.001,
    lr_scheduler_type="cosine",
    save_strategy="steps",
    save_steps=200,
    save_total_limit=1,
    group_by_length=True,
    dataloader_num_workers=0,  # Mac 上设为 0 避免多进程问题
)

# 5. 创建训练器
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
    packing=False,
)

# 6. 开始训练
print("开始训练...")
print("提示: Mac 上训练较慢，建议：")
print("  - 使用较小的数据集")
print("  - 减少训练轮数")
print("  - 考虑使用云服务器进行训练")

trainer.train()

# 7. 保存模型
print(f"保存模型到 {OUTPUT_DIR}")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# 8. 合并 LoRA 权重（可选）
print("合并 LoRA 权重...")
merged_model = model.merge_and_unload()
merged_model.save_pretrained(f"{OUTPUT_DIR}_merged")
tokenizer.save_pretrained(f"{OUTPUT_DIR}_merged")

print("训练完成！")
print(f"模型保存在: {OUTPUT_DIR}")
print(f"合并后的模型保存在: {OUTPUT_DIR}_merged")
