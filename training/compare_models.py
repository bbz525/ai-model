"""
模型对比脚本
对比微调前后的模型效果
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"


def load_model(model_path, device=DEVICE):
    """加载模型"""
    print(f"加载模型: {model_path}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    
    if device == "mps":
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="mps",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True,
        )
    
    return model, tokenizer


def generate(model, tokenizer, prompt, max_length=512):
    """生成回复"""
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    
    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            temperature=0.7,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    generate_time = time.time() - start_time
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_text = response[len(prompt):].strip()
    
    # 计算生成速度
    tokens_generated = len(outputs[0]) - len(inputs[0])
    tokens_per_sec = tokens_generated / generate_time if generate_time > 0 else 0
    
    return generated_text, generate_time, tokens_per_sec


def compare_models(base_model_path, finetuned_model_path):
    """对比两个模型"""
    print("=" * 70)
    print("模型对比工具")
    print("=" * 70)
    
    # 加载模型
    print("\n加载基础模型...")
    base_model, base_tokenizer = load_model(base_model_path)
    
    print("\n加载微调模型...")
    finetuned_model, finetuned_tokenizer = load_model(finetuned_model_path)
    
    # 测试用例
    test_cases = [
        {
            "name": "代码生成",
            "prompt": "### Instruction:\n写一个 Python 函数计算斐波那契数列\n\n### Response:\n",
        },
        {
            "name": "代码解释",
            "prompt": "### Instruction:\n解释什么是递归函数，并给出示例\n\n### Response:\n",
        },
        {
            "name": "算法实现",
            "prompt": "### Instruction:\n实现快速排序算法\n\n### Response:\n",
        },
    ]
    
    # 运行对比
    for test in test_cases:
        print("\n" + "=" * 70)
        print(f"测试: {test['name']}")
        print("=" * 70)
        print(f"提示: {test['prompt'][:60]}...")
        
        # 基础模型生成
        print("\n【基础模型】")
        base_response, base_time, base_tps = generate(
            base_model, base_tokenizer, test['prompt']
        )
        print(f"生成时间: {base_time:.2f}s")
        print(f"生成速度: {base_tps:.2f} tokens/s")
        print(f"输出:\n{base_response[:300]}...")
        
        # 微调模型生成
        print("\n【微调模型】")
        ft_response, ft_time, ft_tps = generate(
            finetuned_model, finetuned_tokenizer, test['prompt']
        )
        print(f"生成时间: {ft_time:.2f}s")
        print(f"生成速度: {ft_tps:.2f} tokens/s")
        print(f"输出:\n{ft_response[:300]}...")
        
        # 简单分析
        print("\n【对比分析】")
        if len(ft_response) > len(base_response):
            print(f"✅ 微调模型输出更长 ({len(ft_response)} vs {len(base_response)} 字符)")
        elif len(ft_response) < len(base_response):
            print(f"⚠️  微调模型输出更短 ({len(ft_response)} vs {len(base_response)} 字符)")
        else:
            print(f"ℹ️  输出长度相同")
        
        if ft_tps > base_tps:
            print(f"✅ 微调模型生成更快 ({ft_tps:.2f} vs {base_tps:.2f} tokens/s)")
        else:
            print(f"⚠️  微调模型生成较慢 ({ft_tps:.2f} vs {base_tps:.2f} tokens/s)")


def main():
    # 配置模型路径
    BASE_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"  # 原始模型
    FINETUNED_MODEL = "./finetuned_model_mac_merged"          # 微调后的模型
    
    print(f"基础模型: {BASE_MODEL}")
    print(f"微调模型: {FINETUNED_MODEL}")
    
    confirm = input("\n确认开始对比? (y/n): ").strip().lower()
    if confirm == 'y':
        compare_models(BASE_MODEL, FINETUNED_MODEL)
    else:
        print("取消对比")


if __name__ == "__main__":
    main()
