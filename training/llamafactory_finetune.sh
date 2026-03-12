#!/bin/bash
# 使用 LlamaFactory 进行一键微调
# LlamaFactory 封装了复杂的训练流程，适合快速上手

# 安装 LlamaFactory
# pip install llmtuner

# 或者从源码安装
# git clone https://github.com/hiyouga/LLaMA-Factory.git
# cd LLaMA-Factory
# pip install -e ".[torch,metrics]"

# 设置环境变量
export WANDB_DISABLED=true
export CUDA_VISIBLE_DEVICES=0

# 使用 llamafactory-cli 进行训练
# 以下是一个完整的训练配置示例

llamafactory-cli train \
    --stage sft \
    --do_train \
    --model_name_or_path deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
    --dataset alpaca_gpt4_en \
    --template deepseek \
    --finetuning_type lora \
    --lora_target q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj \
    --output_dir ./finetuned_deepseek_llamafactory \
    --overwrite_cache \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --lr_scheduler_type cosine \
    --logging_steps 10 \
    --save_steps 500 \
    --learning_rate 2e-4 \
    --num_train_epochs 3.0 \
    --plot_loss \
    --fp16 \
    --max_length 2048 \
    --use_unsloth True  # 启用 Unsloth 加速

# 参数说明：
# --stage sft: 监督微调阶段
# --finetuning_type lora: 使用 LoRA 微调
# --lora_target: 指定应用 LoRA 的模块
# --template deepseek: 使用 DeepSeek 的对话模板
# --use_unsloth: 启用 Unsloth 加速训练

# 训练完成后，合并 LoRA 权重
llamafactory-cli export \
    --model_name_or_path deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
    --adapter_path ./finetuned_deepseek_llamafactory \
    --template deepseek \
    --finetuning_type lora \
    --export_dir ./finetuned_deepseek_merged \
    --export_size 2 \
    --export_device cpu \
    --export_legacy_format False

echo "LlamaFactory 微调完成！"
