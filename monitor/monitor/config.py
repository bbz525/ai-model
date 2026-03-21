import os
from dotenv import load_dotenv

load_dotenv()

# --- 摄像头配置 ---
CAMERA_URL: str = os.getenv("CAMERA_URL", "http://192.168.1.13:8081")
RECONNECT_INTERVAL: int = int(os.getenv("RECONNECT_INTERVAL", "5"))
MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "0"))

# --- Motion 移动侦测配置 ---
MIN_AREA: int = int(os.getenv("MIN_AREA", "500"))
THRESHOLD: int = int(os.getenv("THRESHOLD", "25"))
FRAME_RESIZE: int = int(os.getenv("FRAME_RESIZE", "500"))

# --- Ollama 配置 ---
OLLAMA_API: str = os.getenv("OLLAMA_API", "http://127.0.0.1:11434/api/generate")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3.5")
DETECT_AFTER_MOTION: float = float(os.getenv("DETECT_AFTER_MOTION", "2"))
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))
OLLAMA_MAX_RETRIES: int = int(os.getenv("OLLAMA_MAX_RETRIES", "2"))

# --- QQ 机器人配置 ---
QQ_BOT_TYPE: str = os.getenv("QQ_BOT_TYPE", "official")
QQ_OFFICIAL_APPID: str = os.getenv("QQ_OFFICIAL_APPID", "")
QQ_OFFICIAL_SECRET: str = os.getenv("QQ_OFFICIAL_SECRET", "")
QQ_OFFICIAL_USER_ID: str = os.getenv("QQ_OFFICIAL_USER_ID", "")
QQ_NAPCAT_API: str = os.getenv("QQ_BOT_API", "http://127.0.0.1:3000")
QQ_NAPCAT_GROUP_ID: str = os.getenv("QQ_GROUP_ID", "")
QQ_ENABLE: bool = os.getenv("QQ_ENABLE", "true").lower() == "true"
QQ_HTTP_PORT: int = int(os.getenv("QQ_HTTP_PORT", "8083"))

# --- TTS 配置 ---
TTS_ENABLE: bool = os.getenv("TTS_ENABLE", "true").lower() == "true"
TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")
TTS_BASE_URL: str = os.getenv("TTS_BASE_URL", "https://www.dmxapi.cn/v1")
TTS_REPEAT: int = int(os.getenv("TTS_REPEAT", "1"))
TTS_QUEUE_SIZE: int = int(os.getenv("TTS_QUEUE_SIZE", "10"))
TTS_MIN_LEVEL: str = os.getenv("TTS_MIN_LEVEL", "info")

# --- AI 检测提示词 ---
DETECTION_PROMPT: str = os.getenv("DETECTION_PROMPT", """
你是一个专业的"婴幼儿安全监控AI"。请分析提供的视频帧或实时画面，重点识别婴儿是否存在危险行为。

【危险行为判定标准】
如果检测到以下情况，请立即标记为"告警"：
1. **试图逃离**：婴儿试图从围栏、床沿、沙发边缘爬出，或者身体前倾试图站起（针对小月龄婴儿）。
2. **危险物品**：婴儿试图抓取非玩具类的物品（如电源插座、热水杯、刀具、药品等）放入嘴中或手中。
3. **跌落风险**：婴儿处于抱持状态但头部后仰或身体失去平衡，即将跌落。
4. **窒息风险**：婴儿试图抓握小颗粒玩具（直径小于3cm的珠子、硬币等）吞食。
5. **异常哭闹**：婴儿处于极度焦躁状态并试图剧烈挣扎（可能意味着要挣脱）。

【输出格式要求】
请按照以下JSON格式输出分析结果：
{
  "status": "safe" | "alert",
  "confidence": 0.0-1.0,
  "detection": "描述具体的动作或物体",
  "risk_level": "low" | "medium" | "critical"
}
""")
