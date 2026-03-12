"""
模型诊断脚本
检查模型和 tokenizer 是否匹配，以及训练是否正常
"""

import torch
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

def check_model_files(model_path):
    """检查模型文件完整性"""
    print("=" * 60)
    print("1. 检查模型文件")
    print("=" * 60)
    
    required_files = [
        "config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    ]
    
    path = Path(model_path)
    for file in required_files:
        file_path = path / file
        if file_path.exists():
            size = file_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  ✅ {file} ({size:.1f} MB)")
        else:
            print(f"  ❌ {file} (缺失)")
    
    # 检查是否有 LoRA 权重
    adapter_file = path / "adapter_model.safetensors"
    if adapter_file.exists():
        print(f"  ℹ️  发现 LoRA 适配器文件")

def compare_tokenizers(finetuned_path, base_path="deepseek-ai/deepseek-coder-1.3b-instruct"):
    """对比微调模型和原始模型的 tokenizer"""
    print("\n" + "=" * 60)
    print("2. 对比 Tokenizer")
    print("=" * 60)
    
    print(f"\n加载原始模型 tokenizer: {base_path}")
    try:
        base_tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
        print(f"  原始 vocab 大小: {len(base_tokenizer)}")
    except Exception as e:
        print(f"  ❌ 无法加载: {e}")
        return
    
    print(f"\n加载微调模型 tokenizer: {finetuned_path}")
    try:
        finetuned_tokenizer = AutoTokenizer.from_pretrained(finetuned_path, trust_remote_code=True)
        print(f"  微调 vocab 大小: {len(finetuned_tokenizer)}")
    except Exception as e:
        print(f"  ❌ 无法加载: {e}")
        return
    
    # 对比关键 token
    print("\n对比关键 token:")
    tokens_to_check = ["def", "class", "return", "import", "#", "Ġdef"]
    
    for token in tokens_to_check:
        base_id = base_tokenizer.encode(token, add_special_tokens=False)
        ft_id = finetuned_tokenizer.encode(token, add_special_tokens=False)
        
        match = "✅" if base_id == ft_id else "❌"
        print(f"  {match} '{token}': 原始={base_id}, 微调={ft_id}")

def test_generation_quality(model_path):
    """测试生成质量"""
    print("\n" + "=" * 60)
    print("3. 测试生成质量")
    print("=" * 60)
    
    print(f"\n加载模型: {model_path}")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        
        if DEVICE == "mps":
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
        
        print("✅ 模型加载成功")
        
        # 测试 1: 简单文本
        print("\n测试 1: 简单文本生成")
        prompt = "def "
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=20,
                do_sample=False,  # 使用贪婪解码
            )
        
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  提示: '{prompt}'")
        print(f"  生成: '{result}'")
        
        # 检查是否有乱码
        if 'Ġ' in result or 'Ċ' in result or any(ord(c) > 127 for c in result[len(prompt):]):
            print("  ❌ 检测到乱码或编码问题")
        else:
            print("  ✅ 输出正常")
        
        # 测试 2: 检查模型输出分布
        print("\n测试 2: 检查输出 logits")
        inputs = tokenizer("def", return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits[0, -1, :]  # 最后一个位置的 logits
            top5 = torch.topk(logits, 5)
        
        print("  Top 5 预测的 token:")
        for i, (token_id, score) in enumerate(zip(top5.indices, top5.values)):
            token = tokenizer.decode([token_id])
            print(f"    {i+1}. '{token}' (id={token_id}, score={score:.2f})")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def check_training_config(model_path):
    """检查训练配置"""
    print("\n" + "=" * 60)
    print("4. 检查训练配置")
    print("=" * 60)
    
    config_path = Path(model_path) / "config.json"
    if not config_path.exists():
        print("  ❌ 找不到 config.json")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"\n模型配置:")
    print(f"  模型类型: {config.get('_name_or_path', 'N/A')}")
    print(f"  架构: {config.get('architectures', 'N/A')}")
    print(f"  Vocab 大小: {config.get('vocab_size', 'N/A')}")
    print(f"  隐藏层大小: {config.get('hidden_size', 'N/A')}")
    print(f"  层数: {config.get('num_hidden_layers', 'N/A')}")
    
    # 检查是否有 LoRA 配置
    if "lora" in str(config).lower():
        print("  ℹ️  检测到 LoRA 配置")

def main():
    MODEL_PATH = "./finetuned_model_mac_merged"
    BASE_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"
    
    print("=" * 60)
    print("模型诊断工具")
    print("=" * 60)
    print(f"设备: {DEVICE}")
    print(f"微调模型: {MODEL_PATH}")
    print(f"原始模型: {BASE_MODEL}")
    
    check_model_files(MODEL_PATH)
    compare_tokenizers(MODEL_PATH, BASE_MODEL)
    check_training_config(MODEL_PATH)
    test_generation_quality(MODEL_PATH)
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
