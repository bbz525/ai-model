"""
Mac 系统上的修复版微调脚本
解决了 tokenizer 和生成问题
"""

import torch
import platform
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import load_dataset

# 检测设备
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"系统: {platform.system()}")
print(f"设备: {device}")

# 配置
MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"
OUTPUT_DIR = "./finetuned_model_mac_v2"
MAX_SEQ_LENGTH = 512

print(f"基础模型: {MODEL_NAME}")

# 1. 加载 tokenizer（先加载以确保一致性）
print("\n1. 加载 Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

# 确保 pad_token 设置正确
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    print(f"设置 pad_token = {tokenizer.pad_token}")

print(f"Vocab 大小: {len(tokenizer)}")
print(f"EOS token: {tokenizer.eos_token}")
print(f"PAD token: {tokenizer.pad_token}")

# 2. 加载模型
print("\n2. 加载模型...")

if device == "mps":
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="mps",
        trust_remote_code=True,
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

print(f"模型类型: {model.__class__.__name__}")

# 3. 配置 LoRA
print("\n3. 配置 LoRA...")
peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],  # 简化，只训练关键层
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# 4. 准备数据集 - 使用正确的格式
def format_prompt(example):
    """格式化数据 - 确保格式与模型训练格式一致"""
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    # 使用与 deepseek-coder 一致的格式
    if input_text:
        text = f"<｜begin▁of▁sentence｜>User: {instruction}\n{input_text}\n\nAssistant: {output}<|EOT|>"
    else:
        text = f"<｜begin▁of▁sentence｜>User: {instruction}\n\nAssistant: {output}<|EOT|>"
    
    return {"text": text}

print("\n4. 加载数据集...")
dataset = load_dataset("yahma/alpaca-cleaned", split="train[:200]")  # 使用更多数据
dataset = dataset.map(format_prompt, batched=False)

# 检查数据格式
print("\n数据示例:")
print(dataset[0]['text'][:200])

# 5. 配置训练参数 - 更保守的设置
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,  # 增加到 2 轮
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    warmup_steps=20,
    learning_rate=5e-5,  # 降低学习率
    fp16=False,
    bf16=False,
    logging_steps=5,
    optim="adamw_torch",
    weight_decay=0.01,
    lr_scheduler_type="linear",  # 使用线性调度
    save_strategy="epoch",
    save_total_limit=1,
    dataloader_num_workers=0,
    remove_unused_columns=False,  # 保留所有列
)

# 6. 创建训练器
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
    dataset_text_field="text",  # 明确指定文本字段
)

# 7. 开始训练
print("\n5. 开始训练...")
print("提示: 训练可能需要一些时间，请耐心等待...")

trainer.train()

# 8. 保存模型
print(f"\n6. 保存模型到 {OUTPUT_DIR}")
trainer.save_model(OUTPUT_DIR)

# 确保 tokenizer 配置正确保存
tokenizer.save_pretrained(OUTPUT_DIR)

# 9. 合并 LoRA 权重
print("\n7. 合并 LoRA 权重...")
merged_model = model.merge_and_unload()
merged_output = f"{OUTPUT_DIR}_merged"
merged_model.save_pretrained(merged_output)
tokenizer.save_pretrained(merged_output)

print(f"\n✅ 训练完成！")
print(f"LoRA 模型: {OUTPUT_DIR}")
print(f"合并模型: {merged_output}")

# 10. 快速测试
print("\n8. 快速测试...")
test_prompt = "User: 写一个 Python 函数计算斐波那契数列\n\nAssistant:"
inputs = tokenizer(test_prompt, return_tensors="pt").to(device)

with torch.no_grad():
    outputs = merged_model.generate(
        **inputs,
        max_new_tokens=100,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )

result = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(f"测试提示: {test_prompt}")
print(f"生成结果: {result[len(test_prompt):].strip()[:200]}...")
