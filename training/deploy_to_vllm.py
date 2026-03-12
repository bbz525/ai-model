"""
将微调后的模型部署到 vLLM
支持加载 LoRA 适配器或合并后的完整模型
"""

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

# ==================== 方式 1: 加载合并后的完整模型 ====================

def load_merged_model():
    """加载已经合并 LoRA 权重的完整模型"""
    model_path = "./finetuned_deepseek_coder_merged"  # 替换为您的模型路径
    
    llm = LLM(
        model=model_path,
        tensor_parallel_size=1,  # GPU 数量
        max_model_len=4096,
        trust_remote_code=True,
    )
    return llm


# ==================== 方式 2: 基础模型 + LoRA 适配器 ====================

def load_base_with_lora():
    """
    加载基础模型并动态应用 LoRA 适配器
    这种方式可以在同一个基础模型上切换不同的 LoRA
    """
    base_model = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
    lora_path = "./finetuned_deepseek_coder"  # LoRA 适配器路径
    
    llm = LLM(
        model=base_model,
        enable_lora=True,  # 启用 LoRA 支持
        max_lora_rank=16,  # LoRA 秩
        tensor_parallel_size=1,
        max_model_len=4096,
        trust_remote_code=True,
    )
    
    return llm, lora_path


# ==================== 推理示例 ====================

def inference_merged_model():
    """使用合并后的模型进行推理"""
    llm = load_merged_model()
    
    sampling_params = SamplingParams(
        temperature=0.7,
        top_p=0.95,
        max_tokens=1024,
    )
    
    prompts = [
        "### Instruction:\n写一个 Python 函数计算斐波那契数列\n\n### Response:\n",
        "### Instruction:\n解释快速排序算法\n\n### Response:\n",
    ]
    
    outputs = llm.generate(prompts, sampling_params)
    
    for output in outputs:
        print(f"Prompt: {output.prompt}")
        print(f"Output: {output.outputs[0].text}")
        print("-" * 50)


def inference_with_lora():
    """使用 LoRA 适配器进行推理"""
    llm, lora_path = load_base_with_lora()
    
    sampling_params = SamplingParams(
        temperature=0.7,
        top_p=0.95,
        max_tokens=1024,
    )
    
    # 创建 LoRA 请求
    lora_request = LoRARequest(
        lora_name="my_finetuned_model",
        lora_int_id=1,  # LoRA 适配器的整数 ID
        lora_local_path=lora_path,
    )
    
    prompts = [
        "### Instruction:\n写一个 Python 函数计算斐波那契数列\n\n### Response:\n",
    ]
    
    # 使用 LoRA 适配器生成
    outputs = llm.generate(
        prompts,
        sampling_params,
        lora_request=lora_request,
    )
    
    for output in outputs:
        print(f"Output with LoRA: {output.outputs[0].text}")


# ==================== vLLM 服务部署 ====================

def start_vllm_server():
    """
    使用命令行启动 vLLM 服务
    合并后的模型：
    python -m vllm.entrypoints.openai.api_server \
        --model ./finetuned_deepseek_coder_merged \
        --trust-remote-code \
        --tensor-parallel-size 1 \
        --max-model-len 4096
    
    带 LoRA 支持的服务：
    python -m vllm.entrypoints.openai.api_server \
        --model deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
        --enable-lora \
        --lora-modules my_lora=./finetuned_deepseek_coder \
        --trust-remote-code \
        --tensor-parallel-size 1
    """
    pass


if __name__ == "__main__":
    print("选择部署方式：")
    print("1. 加载合并后的模型")
    print("2. 基础模型 + LoRA 适配器")
    
    choice = input("请输入选项 (1/2): ").strip()
    
    if choice == "1":
        inference_merged_model()
    elif choice == "2":
        inference_with_lora()
    else:
        print("无效选项")
