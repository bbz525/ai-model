"""
Mac 系统上的模型推理脚本
使用 Transformers 直接推理（替代 vLLM）
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 配置
MODEL_PATH = "./finetuned_deepseek_mac_merged"  # 或微调后的模型路径
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

def load_model():
    """加载模型"""
    print(f"使用设备: {DEVICE}")
    print("加载模型...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    
    if DEVICE == "mps":
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="mps",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True,
        )
    
    return model, tokenizer

def generate_response(model, tokenizer, prompt, max_length=1024):
    """生成回复"""
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            temperature=0.7,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

def chat_mode(model, tokenizer):
    """交互式聊天模式"""
    print("\n=== 交互式聊天模式 ===")
    print("输入 'exit' 退出\n")
    
    while True:
        user_input = input("你: ").strip()
        if user_input.lower() == "exit":
            break
        
        # 格式化提示
        prompt = f"### Instruction:\n{user_input}\n\n### Response:\n"
        
        response = generate_response(model, tokenizer, prompt)
        # 提取回复部分
        response_text = response[len(prompt):].strip()
        
        print(f"AI: {response_text}\n")

def main():
    model, tokenizer = load_model()
    
    # 示例推理
    test_prompts = [
        "### Instruction:\n写一个 Python 函数计算斐波那契数列\n\n### Response:\n",
        "### Instruction:\n解释什么是递归函数\n\n### Response:\n",
    ]
    
    print("\n=== 示例推理 ===")
    for prompt in test_prompts:
        print(f"提示: {prompt}")
        response = generate_response(model, tokenizer, prompt)
        print(f"回复: {response[len(prompt):].strip()}")
        print("-" * 50)
    
    # 进入交互模式
    chat_mode(model, tokenizer)

if __name__ == "__main__":
    main()
