"""
使用 Unsloth 对 DeepSeek-Coder-V2-Lite-Instruct 进行高效微调
Unsloth 可以显著提升微调速度并降低显存占用
"""

import torch
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# 配置参数
MODEL_NAME = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
MAX_SEQ_LENGTH = 2048
OUTPUT_DIR = "./finetuned_deepseek_coder"

# 1. 加载模型和分词器（使用 Unsloth 加速）
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=torch.bfloat16,  # 或 torch.float16
    load_in_4bit=True,     # 使用 4-bit 量化加载，节省显存
)

# 2. 添加 LoRA 适配器（参数高效微调）
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                   # LoRA 秩，建议 8-128
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=16,          # LoRA 缩放参数
    lora_dropout=0,         # 建议设为 0，Unsloth 已做优化
    bias="none",
    use_gradient_checkpointing="unsloth",  # 使用 Unsloth 优化的梯度检查点
    random_state=3407,
)

# 3. 准备数据集
# 这里使用示例数据集，您需要替换为自己的数据
# 数据格式应为 {"instruction": "...", "input": "...", "output": "..."}

def format_prompt(example):
    """格式化指令数据为对话格式"""
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    if input_text:
        prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
    else:
        prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
    
    return {"text": prompt}

# 加载您的数据集（示例）
# dataset = load_dataset("json", data_files="your_data.json")
# dataset = dataset.map(format_prompt, batched=False)

# 使用示例数据集演示
dataset = load_dataset("yahma/alpaca-cleaned", split="train[:1000]")
dataset = dataset.map(format_prompt, batched=False)

# 4. 配置训练参数
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_steps=100,
    learning_rate=2e-4,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=10,
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="linear",
    seed=3407,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
)

# 5. 创建训练器
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
)

# 6. 开始训练
print("开始微调...")
trainer.train()

# 7. 保存模型
print(f"保存微调后的模型到 {OUTPUT_DIR}")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# 8. 合并 LoRA 权重到基础模型（可选，便于部署）
print("合并 LoRA 权重...")
model.save_pretrained_merged(
    f"{OUTPUT_DIR}_merged",
    tokenizer,
    save_method="merged_16bit",  # 或 "merged_4bit" 继续量化
)

print("微调完成！")
print(f"LoRA 模型保存在: {OUTPUT_DIR}")
print(f"合并后的模型保存在: {OUTPUT_DIR}_merged")
