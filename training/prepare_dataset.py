"""
数据集准备工具
将不同格式的数据转换为微调所需的格式
"""

import json
from typing import List, Dict
from datasets import Dataset, DatasetDict


def prepare_instruction_dataset(data: List[Dict], output_file: str):
    """
    准备指令微调数据集
    
    输入格式：
    [
        {
            "instruction": "编写一个 Python 函数...",
            "input": "",  # 可选的额外输入
            "output": "def function(): ..."
        },
        ...
    ]
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"数据集已保存到: {output_file}")


def prepare_chat_dataset(conversations: List[List[Dict]], output_file: str):
    """
    准备对话格式数据集
    
    输入格式：
    [
        [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
        ],
        ...
    ]
    """
    data = []
    for conv in conversations:
        data.append({"messages": conv})
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"对话数据集已保存到: {output_file}")


def prepare_code_dataset(code_pairs: List[Dict], output_file: str):
    """
    准备代码数据集（适合代码生成任务）
    
    输入格式：
    [
        {
            "prompt": "// 编写一个快速排序算法\n",
            "completion": "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    ..."
        },
        ...
    ]
    """
    data = []
    for pair in code_pairs:
        item = {
            "instruction": "完成以下代码",
            "input": pair["prompt"],
            "output": pair["completion"]
        }
        data.append(item)
    
    prepare_instruction_dataset(data, output_file)


def convert_to_sharegpt_format(data: List[Dict], output_file: str):
    """
    转换为 ShareGPT 格式（LlamaFactory 等工具支持）
    
    输入格式：
    [
        {
            "conversations": [
                {"from": "human", "value": "你好"},
                {"from": "gpt", "value": "你好！"}
            ]
        }
    ]
    """
    sharegpt_data = []
    for item in data:
        conversations = []
        for msg in item.get("messages", []):
            from_role = "human" if msg["role"] == "user" else "gpt"
            conversations.append({
                "from": from_role,
                "value": msg["content"]
            })
        sharegpt_data.append({"conversations": conversations})
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)
    
    print(f"ShareGPT 格式数据集已保存到: {output_file}")


# ==================== 示例：创建示例数据集 ====================

def create_example_code_dataset():
    """创建一个示例代码微调数据集"""
    data = [
        {
            "instruction": "编写一个 Python 函数，计算斐波那契数列的第 n 项",
            "input": "",
            "output": "def fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n\n# 或者使用迭代方式\ndef fibonacci_iter(n):\n    if n <= 0:\n        return 0\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b"
        },
        {
            "instruction": "解释什么是递归函数，并给出一个 Python 示例",
            "input": "",
            "output": "递归函数是指在函数定义中调用自身的函数。递归包含两个关键部分：\n1. 基准情况（Base Case）：停止递归的条件\n2. 递归情况（Recursive Case）：函数调用自身的逻辑\n\n示例：计算阶乘\ndef factorial(n):\n    # 基准情况\n    if n == 0 or n == 1:\n        return 1\n    # 递归情况\n    else:\n        return n * factorial(n - 1)\n\n# 使用示例\nprint(factorial(5))  # 输出: 120"
        },
        {
            "instruction": "编写一个函数，检查字符串是否为回文",
            "input": "",
            "output": "def is_palindrome(s):\n    # 检查字符串是否为回文\n    # 忽略大小写和非字母数字字符\n    # 清理字符串：移除非字母数字字符并转为小写\n    cleaned = ''.join(char.lower() for char in s if char.isalnum())\n    \n    # 比较字符串与其反转\n    return cleaned == cleaned[::-1]\n\n# 测试\nprint(is_palindrome('A man, a plan, a canal: Panama'))  # True\nprint(is_palindrome('race a car'))  # False"
        },
    ]
    
    prepare_instruction_dataset(data, "./example_code_dataset.jsonl")


def create_example_chat_dataset():
    """创建一个示例对话数据集"""
    conversations = [
        [
            {"role": "user", "content": "你好，你能帮我写代码吗？"},
            {"role": "assistant", "content": "当然可以！我很乐意帮助你编写代码。请告诉我你需要实现什么功能，或者遇到了什么问题？"}
        ],
        [
            {"role": "user", "content": "Python 中的列表和元组有什么区别？"},
            {"role": "assistant", "content": """Python 中列表（list）和元组（tuple）的主要区别：

1. **可变性**：
   - 列表是可变的（mutable），可以添加、删除、修改元素
   - 元组是不可变的（immutable），创建后不能修改

2. **语法**：
   - 列表使用方括号：`my_list = [1, 2, 3]`
   - 元组使用圆括号：`my_tuple = (1, 2, 3)`

3. **性能**：
   - 元组比列表更轻量，访问速度更快
   - 元组可以作为字典的键，列表不行

4. **使用场景**：
   - 列表：需要频繁修改的数据集合
   - 元组：固定不变的数据，如坐标、配置项等"""}
        ],
    ]
    
    prepare_chat_dataset(conversations, "./example_chat_dataset.jsonl")


if __name__ == "__main__":
    print("创建示例数据集...")
    create_example_code_dataset()
    create_example_chat_dataset()
    print("示例数据集创建完成！")
