"""
快速测试脚本
验证模型是否能正常生成
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
MODEL_PATH = "./finetuned_model_mac_merged"

def test():
    print("加载模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
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
    
    # 测试 1: 简单问题
    print("\n测试 1: 简单问题")
    prompt = "<｜begin▁of▁sentence｜>User: 写一个 Python 函数计算斐波那契数列\n\nAssistant:"
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    result = tokenizer.decode(outputs[0], skip_special_tokens=False)
    result = result.replace('Ġ', ' ').replace('Ċ', '\n')
    
    # 提取 Assistant 的回复
    if "Assistant:" in result:
        answer = result.split("Assistant:")[-1].replace('<|EOT|>', '').strip()
        print(f"回答:\n{answer}")
    else:
        print(f"完整输出:\n{result}")
    
    # 测试 2: 代码解释
    print("\n测试 2: 代码解释")
    prompt2 = "<｜begin▁of▁sentence｜>User: 解释什么是递归函数\n\nAssistant:"
    inputs2 = tokenizer(prompt2, return_tensors="pt").to(DEVICE)
    
    with torch.no_grad():
        outputs2 = model.generate(
            **inputs2,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    result2 = tokenizer.decode(outputs2[0], skip_special_tokens=False)
    result2 = result2.replace('Ġ', ' ').replace('Ċ', '\n')
    
    if "Assistant:" in result2:
        answer2 = result2.split("Assistant:")[-1].replace('<|EOT|>', '').strip()
        print(f"回答:\n{answer2}")
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    test()
