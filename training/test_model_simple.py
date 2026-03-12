"""
简单的模型测试脚本
用于诊断模型输出问题
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
MODEL_PATH = "./finetuned_model_mac_merged"

def test_model():
    print("=" * 60)
    print("模型测试")
    print("=" * 60)
    
    # 加载模型
    print(f"\n1. 加载模型...")
    print(f"路径: {MODEL_PATH}")
    print(f"设备: {DEVICE}")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    
    # 检查 tokenizer
    print(f"\n2. Tokenizer 信息:")
    print(f"   类型: {tokenizer.__class__.__name__}")
    print(f"   EOS token: {tokenizer.eos_token} (id: {tokenizer.eos_token_id})")
    print(f"   PAD token: {tokenizer.pad_token} (id: {tokenizer.pad_token_id})")
    print(f"   BOS token: {tokenizer.bos_token} (id: {tokenizer.bos_token_id})")
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        print("   ⚠️  pad_token 未设置，已设置为 eos_token")
    
    # 加载模型
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
    
    print(f"\n3. 模型信息:")
    print(f"   类型: {model.__class__.__name__}")
    
    # 测试编码和解码
    print(f"\n4. 测试编码解码:")
    test_text = "def hello():"
    encoded = tokenizer.encode(test_text)
    decoded = tokenizer.decode(encoded)
    print(f"   原文: {test_text}")
    print(f"   编码: {encoded}")
    print(f"   解码: {decoded}")
    
    # 测试生成
    print(f"\n5. 测试生成:")
    prompt = "### Instruction:\n写一个 Python 函数计算斐波那契数列\n\n### Response:\n"
    print(f"   提示: {prompt}")
    
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    print(f"   输入 IDs: {inputs['input_ids']}")
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            temperature=0.7,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    print(f"   输出 IDs: {outputs[0]}")
    
    # 多种方式解码
    print(f"\n6. 解码结果:")
    
    # 方式 1: 完整解码
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"   完整解码: {full_text[:200]}...")
    
    # 方式 2: 只解码新生成的部分
    new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
    new_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    print(f"   新生成部分: {new_text[:200]}...")
    
    # 方式 3: 逐个 token 解码
    print(f"\n   逐个 token 解码:")
    for i, token_id in enumerate(new_tokens[:10]):
        token_text = tokenizer.decode([token_id])
        print(f"      Token {i}: id={token_id}, text='{token_text}'")
    
    # 清理特殊字符
    print(f"\n7. 清理后的输出:")
    cleaned = new_text.replace('Ġ', ' ').replace('Ċ', '\n')
    print(f"   {cleaned[:300]}...")

if __name__ == "__main__":
    test_model()
