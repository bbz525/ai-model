import base64
import json
import urllib.error
import urllib.request
from typing import Optional

import requests

from monitor.config import (
    QQ_BOT_TYPE,
    QQ_ENABLE,
    QQ_HTTP_PORT,
    QQ_NAPCAT_API,
    QQ_NAPCAT_GROUP_ID,
    QQ_OFFICIAL_USER_ID,
)


def send_qq_message_official(message: str, image_path: Optional[str] = None) -> bool:
    """通过本地 qq_chat.py HTTP 接口发送官方机器人单聊消息"""
    payload = {"user_openid": QQ_OFFICIAL_USER_ID, "content": message}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{QQ_HTTP_PORT}/alert",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success"):
                print("✅ QQ消息发送成功")
                return True
            else:
                print(f"⚠️ QQ消息发送失败：{result.get('error', '未知错误')}")
                return False
    except urllib.error.URLError as e:
        print(f"⚠️ 无法连接到机器人服务：{e}")
        print("💡 请确保 qq_chat.py 已启动，或检查 HTTP 接口是否可用")
        return False


def send_qq_message_napcat(message: str, image_path: Optional[str] = None) -> bool:
    """使用 NapCat/go-cqhttp 发送 QQ 群消息"""
    image_data = None
    if image_path:
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except OSError:
            pass

    if image_data:
        payload = {
            "group_id": QQ_NAPCAT_GROUP_ID,
            "message": [
                {"type": "text", "data": {"text": message}},
                {"type": "image", "data": {"file": f"base64://{image_data}"}},
            ],
        }
    else:
        payload = {"group_id": QQ_NAPCAT_GROUP_ID, "message": message}

    try:
        response = requests.post(
            f"{QQ_NAPCAT_API}/send_group_msg", json=payload, timeout=10
        )
        response.raise_for_status()
        print("✅ QQ消息发送成功 (NapCat)")
        return True
    except Exception as e:
        print(f"❌ QQ消息发送失败：{str(e)}")
        return False


def send_qq_message(message: str, image_path: Optional[str] = None) -> bool:
    """根据 QQ_BOT_TYPE 配置选择发送方式"""
    if not QQ_ENABLE:
        return False
    if QQ_BOT_TYPE == "official":
        return send_qq_message_official(message, image_path)
    else:
        return send_qq_message_napcat(message, image_path)
