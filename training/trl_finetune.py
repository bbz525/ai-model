"""
使用 Hugging Face TRL 的 SFTTrainer 进行指令微调
这是更通用的微调方案，不依赖 Unsloth
"""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
from datasets import load_dataset

# 配置参数
MODEL_NAME = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
OUTPUT_DIR = "./finetuned_deepseek_coder_trl"
MAX_SEQ_LENGTH = 2048

# 1. 配置 4-bit 量化（节省显存）
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# 2. 加载模型和分词器
print("加载模型...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# 3. 准备模型用于训练
model = prepare_model_for_kbit_training(model)

# 4. 配置 LoRA
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 5. 准备数据集
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

# 加载数据集（替换为您自己的数据）
dataset = load_dataset("yahma/alpaca-cleaned", split="train[:1000]")
dataset = dataset.map(format_chat_template, remove_columns=dataset.column_names)

# 6. 配置训练参数
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    warmup_ratio=0.03,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    optim="paged_adamw_8bit",
    weight_decay=0.001,
    lr_scheduler_type="cosine",
    save_strategy="epoch",
    save_total_limit=2,
    group_by_length=True,
)

# 7. 创建训练器
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
    packing=False,  # 设为 True 可加速训练短序列
)

# 8. 开始训练
print("开始训练...")
trainer.train()

# 9. 保存模型
print(f"保存模型到 {OUTPUT_DIR}")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("训练完成！")
