"""
Mac 系统上的简化微调脚本
使用对旧版 Transformers 更友好的模型
"""

import torch
import platform

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

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import load_dataset

# ==================== 模型选择 ====================
# 以下模型对旧版 Transformers 更友好，适合 Mac 使用：

# 选项 1: DeepSeek Coder 1.3B (轻量级，兼容性好)
# MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"

# 选项 2: CodeLlama 7B (Meta 的代码模型)
# MODEL_NAME = "codellama/CodeLlama-7b-Instruct-hf"

# 选项 3: Qwen2.5-Coder (阿里代码模型，对中文友好)
# MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

# 选项 4: 如果坚持要用 DeepSeek-Coder-V2，需要升级 Transformers
MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"  # 默认使用兼容版本

OUTPUT_DIR = "./finetuned_model_mac"
MAX_SEQ_LENGTH = 512  # Mac 上使用更短的序列长度

print(f"使用模型: {MODEL_NAME}")

# 1. 加载模型和分词器
print("加载模型...")

try:
    if device == "mps":
        # Apple Silicon - 使用 MPS
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="mps",
            trust_remote_code=True,
        )
    else:
        # Intel Mac - 使用 CPU
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    print("✅ 模型加载成功！")
    
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    print("\n建议:")
    print("1. 升级 Transformers: pip install transformers --upgrade")
    print("2. 使用其他模型（修改 MODEL_NAME）")
    print("3. 检查网络连接和 HuggingFace 访问权限")
    exit(1)

# 2. 配置 LoRA
print("配置 LoRA...")
peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],  # 简化目标模块
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 3. 准备数据集
def format_prompt(example):
    """格式化指令数据"""
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    if input_text:
        prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
    else:
        prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
    
    return {"text": prompt}

# 加载示例数据集
print("加载数据集...")
try:
    dataset = load_dataset("yahma/alpaca-cleaned", split="train[:100]")  # 使用更少样本
    dataset = dataset.map(format_prompt, batched=False)
    print(f"✅ 数据集加载成功，共 {len(dataset)} 条样本")
except Exception as e:
    print(f"❌ 数据集加载失败: {e}")
    exit(1)

# 4. 配置训练参数
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    warmup_steps=10,
    learning_rate=1e-4,
    fp16=False,
    bf16=False,
    logging_steps=5,
    optim="adamw_torch",
    weight_decay=0.001,
    lr_scheduler_type="cosine",
    save_strategy="epoch",
    save_total_limit=1,
    # group_by_length=True,
    dataloader_num_workers=0,
)

# 5. 创建训练器
trainer = SFTTrainer(
    model=model,
    # tokenizer=tokenizer,
    train_dataset=dataset,
    # max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
    # packing=False,
)

# 6. 开始训练
print("\n开始训练...")
print("提示: Mac 上训练较慢，请耐心等待...")

try:
    trainer.train()
    
    # 保存模型
    print(f"\n保存模型到 {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # 合并 LoRA 权重
    print("合并 LoRA 权重...")
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(f"{OUTPUT_DIR}_merged")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}_merged")
    
    print("\n✅ 训练完成！")
    print(f"模型保存在: {OUTPUT_DIR}")
    print(f"合并后的模型保存在: {OUTPUT_DIR}_merged")
    
except Exception as e:
    print(f"\n❌ 训练失败: {e}")
    print("\n可能的原因:")
    print("1. 内存不足 - 尝试减小 MAX_SEQ_LENGTH 或 batch_size")
    print("2. 模型兼容性问题 - 尝试使用其他模型")
    print("3. 依赖版本问题 - 检查 transformers, torch, peft, trl 版本")
