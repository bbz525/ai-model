import base64
import json
import time
import requests
from typing import Optional

from monitor.config import (
    OLLAMA_API,
    MODEL_NAME,
    OLLAMA_TIMEOUT,
    OLLAMA_MAX_RETRIES,
    DETECTION_PROMPT,
)


def image_to_base64(image_path: str) -> str:
    """图片转 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_ollama(image_path: str, retries: int = OLLAMA_MAX_RETRIES) -> Optional[dict]:
    """调用本地 Ollama 分析图像，支持重试。返回 JSON 字典或 None。"""
    api_url = OLLAMA_API.replace("/generate", "/chat")

    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                print(f"🔄 Ollama第{attempt + 1}次尝试...")

            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": DETECTION_PROMPT,
                        "images": [image_to_base64(image_path)],
                    }
                ],
                "stream": False,
                "format": "json",
            }

            response = requests.post(api_url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()

            response_data = response.json()
            raw_response = response_data.get("message", {}).get("content", "").strip()

            if not raw_response:
                print(f"⚠️ Ollama返回空响应")
                print(f"📄 完整响应：{response_data}")
                return None

            try:
                return json.loads(raw_response)
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON解析失败：{je}")
                print(f"📄 原始响应：{raw_response[:300]}...")
                return None

        except requests.exceptions.Timeout:
            print(f"⏱️ Ollama调用超时（{OLLAMA_TIMEOUT}秒）")
            if attempt < retries:
                print("⏳ 等待3秒后重试...")
                time.sleep(3)
            else:
                print("❌ Ollama调用失败：超过最大重试次数")
                return None
        except Exception as e:
            print(f"❌ Ollama调用失败：{str(e)}")
            if attempt < retries:
                print("⏳ 等待3秒后重试...")
                time.sleep(3)
            else:
                return None
