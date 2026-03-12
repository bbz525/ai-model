"""
微调模型验证脚本
用于测试微调后模型的性能和效果
"""

import torch
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path

# ==================== 配置 ====================

# 模型路径（根据您的实际情况修改）
MODEL_PATH = "./finetuned_model_mac_merged"  # 合并后的模型
# MODEL_PATH = "./finetuned_model_mac"       # LoRA 适配器模型
# MODEL_PATH = "deepseek-ai/deepseek-coder-1.3b-instruct"  # 原始模型（对比用）

# 测试数据集路径
TEST_DATA_PATH = "./example_code_dataset.jsonl"

# 设备选择
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# ==================== 加载模型 ====================

def load_model(model_path):
    """加载模型和分词器"""
    print(f"加载模型: {model_path}")
    print(f"使用设备: {DEVICE}")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        
        # 确保 pad_token 已设置
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            print(f"设置 pad_token = eos_token: {tokenizer.pad_token}")
        
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
        
        # 打印模型信息
        print(f"模型类型: {model.__class__.__name__}")
        print(f"Tokenizer 类型: {tokenizer.__class__.__name__}")
        print(f"Vocab 大小: {len(tokenizer)}")
        print("✅ 模型加载成功！\n")
        return model, tokenizer
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# ==================== 生成函数 ====================

def generate_response(model, tokenizer, prompt, max_length=1024, temperature=0.7):
    """生成回复 - 使用正确的对话格式"""
    # 确保 pad_token 已设置
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 使用 deepseek-coder 的对话格式
    if "User:" not in prompt:
        # 如果是简单指令，转换为对话格式
        formatted_prompt = f"<｜begin▁of▁sentence｜>User: {prompt}\n\nAssistant:"
    else:
        formatted_prompt = prompt
    
    # 编码输入
    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length
    ).to(DEVICE)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=temperature,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    # 解码输出
    response = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    # 清理特殊编码字符
    response = response.replace('Ġ', ' ').replace('Ċ', '\n')
    
    # 只返回 Assistant 的部分
    if "Assistant:" in response:
        response = response.split("Assistant:")[-1]
    
    # 移除结束标记
    response = response.replace('<|EOT|>', '').strip()
    
    return response


# ==================== 验证方法 ====================

def verify_basic_generation(model, tokenizer):
    """基础生成能力验证"""
    print("=" * 50)
    print("测试 1: 基础生成能力")
    print("=" * 50)
    
    test_prompts = [
        "写一个 Python 函数计算斐波那契数列",
        "解释什么是递归函数",
        "编写一个函数，检查字符串是否为回文",
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n测试 {i}:")
        print(f"提示: {prompt}")
        
        response = generate_response(model, tokenizer, prompt)
        
        print(f"生成结果:\n{response[:300]}...")
        print("-" * 50)


def verify_with_test_data(model, tokenizer, test_data_path):
    """使用测试数据集验证"""
    print("\n" + "=" * 50)
    print("测试 2: 测试数据集验证")
    print("=" * 50)
    
    if not Path(test_data_path).exists():
        print(f"❌ 测试数据文件不存在: {test_data_path}")
        return
    
    # 加载测试数据
    test_data = []
    with open(test_data_path, 'r', encoding='utf-8') as f:
        for line in f:
            test_data.append(json.loads(line))
    
    print(f"加载了 {len(test_data)} 条测试数据\n")
    
    # 测试前 3 条
    for i, item in enumerate(test_data[:3], 1):
        instruction = item.get("instruction", "")
        input_text = item.get("input", "")
        expected_output = item.get("output", "")
        
        # 构建提示
        if input_text:
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n"
        else:
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n"
        
        print(f"测试 {i}:")
        print(f"指令: {instruction[:50]}...")
        
        response = generate_response(model, tokenizer, prompt)
        generated_output = response[len(prompt):].strip()
        
        print(f"期望输出: {expected_output[:100]}...")
        print(f"实际输出: {generated_output[:100]}...")
        
        # 简单相似度检查
        similarity = len(set(generated_output.split()) & set(expected_output.split())) / max(len(set(expected_output.split())), 1)
        print(f"关键词相似度: {similarity:.2%}")
        print("-" * 50)


def verify_code_completion(model, tokenizer):
    """代码补全能力验证"""
    print("\n" + "=" * 50)
    print("测试 3: 代码补全能力")
    print("=" * 50)
    
    code_prompts = [
        {
            "name": "函数补全",
            "prompt": "### Instruction:\n完成以下 Python 函数\n\n### Input:\ndef factorial(n):\n    # 计算阶乘\n    \n\n### Response:\n",
        },
        {
            "name": "类定义",
            "prompt": "### Instruction:\n编写一个表示矩形的 Python 类\n\n### Response:\n",
        },
        {
            "name": "算法实现",
            "prompt": "### Instruction:\n实现二分查找算法\n\n### Response:\n",
        },
    ]
    
    for test in code_prompts:
        print(f"\n{test['name']}:")
        print(f"提示: {test['prompt'][:80]}...")
        
        response = generate_response(model, tokenizer, test['prompt'], max_length=512)
        generated_code = response[len(test['prompt']):].strip()
        
        print(f"生成代码:\n{generated_code}")
        print("-" * 50)


def verify_consistency(model, tokenizer):
    """验证生成一致性"""
    print("\n" + "=" * 50)
    print("测试 4: 生成一致性")
    print("=" * 50)
    
    prompt = "### Instruction:\n写一个 Python 函数计算两个数的和\n\n### Response:\n"
    
    print(f"提示: {prompt}")
    print("生成 3 次，检查一致性:\n")
    
    responses = []
    for i in range(3):
        response = generate_response(model, tokenizer, prompt, temperature=0.1)  # 低温度增加一致性
        generated = response[len(prompt):].strip()
        responses.append(generated)
        print(f"第 {i+1} 次: {generated[:100]}...")
    
    # 检查一致性
    if len(set(responses)) == 1:
        print("\n✅ 完全一致")
    elif len(set([r[:50] for r in responses])) == 1:
        print("\n⚠️  开头一致，后面有差异")
    else:
        print("\n⚠️  存在明显差异（temperature 较高时正常）")


def interactive_test(model, tokenizer):
    """交互式测试"""
    print("\n" + "=" * 50)
    print("测试 5: 交互式测试")
    print("=" * 50)
    print("输入你的问题，或输入 'exit' 退出\n")
    
    while True:
        user_input = input("你的问题: ").strip()
        if user_input.lower() == 'exit':
            break
        
        print("生成中...")
        response = generate_response(model, tokenizer, user_input)
        
        print(f"回答:\n{response}\n")


# ==================== 主函数 ====================

def main():
    print("=" * 60)
    print("微调模型验证工具")
    print("=" * 60)
    
    # 加载模型
    model, tokenizer = load_model(MODEL_PATH)
    if model is None:
        return
    
    # 运行各项验证
    while True:
        print("\n请选择验证项目:")
        print("1. 基础生成能力验证")
        print("2. 测试数据集验证")
        print("3. 代码补全能力验证")
        print("4. 生成一致性验证")
        print("5. 交互式测试")
        print("6. 运行全部测试")
        print("0. 退出")
        
        choice = input("\n输入选项 (0-6): ").strip()
        
        if choice == '1':
            verify_basic_generation(model, tokenizer)
        elif choice == '2':
            verify_with_test_data(model, tokenizer, TEST_DATA_PATH)
        elif choice == '3':
            verify_code_completion(model, tokenizer)
        elif choice == '4':
            verify_consistency(model, tokenizer)
        elif choice == '5':
            interactive_test(model, tokenizer)
        elif choice == '6':
            verify_basic_generation(model, tokenizer)
            verify_with_test_data(model, tokenizer, TEST_DATA_PATH)
            verify_code_completion(model, tokenizer)
            verify_consistency(model, tokenizer)
        elif choice == '0':
            print("退出验证")
            break
        else:
            print("无效选项")


if __name__ == "__main__":
    main()
