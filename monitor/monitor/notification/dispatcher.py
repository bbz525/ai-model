import time
from typing import Optional, Any

from monitor.config import QQ_ENABLE, TTS_ENABLE
from monitor.tts.base import AlertLevel
from monitor.tts.voice import get_risk_alert_level
from monitor.notification.qq import send_qq_message


def trigger_alert(
    abnormal_info: dict,
    image_path: Optional[str] = None,
    voice_announcer: Optional[Any] = None,
) -> None:
    """触发告警：控制台输出 + QQ 推送 + 语音播报"""
    alert_time = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n🚨 【{alert_time}】异常告警")
    print(f"类型：{abnormal_info['type']}")
    print(f"置信度：{abnormal_info['confidence']:.2f}")
    print(f"描述：{abnormal_info['desc']}")

    if QQ_ENABLE:
        qq_message = (
            f"🚨 安防监控异常告警\n"
            f"━━━━━━━━━━━━━━\n"
            f"⏰ 时间：{alert_time}\n"
            f"⚠️ 类型：{abnormal_info['type']}\n"
            f"📊 置信度：{abnormal_info['confidence']:.2%}\n"
            f"📝 描述：{abnormal_info['desc']}\n"
            f"━━━━━━━━━━━━━━"
        )
        send_qq_message(qq_message, image_path)

    if voice_announcer and TTS_ENABLE:
        risk_level = abnormal_info.get("risk_level", "medium")
        alert_level = get_risk_alert_level(risk_level)

        if alert_level == AlertLevel.CRITICAL:
            voice_message = f"紧急告警！检测到{abnormal_info['type']}，请立即处理！"
            immediate = True
        elif alert_level == AlertLevel.ERROR:
            voice_message = f"警告！检测到{abnormal_info['type']}，请注意！"
            immediate = False
        elif alert_level == AlertLevel.WARNING:
            voice_message = f"注意，检测到{abnormal_info['type']}"
            immediate = False
        else:
            voice_message = f"检测到{abnormal_info['type']}"
            immediate = False

        voice_announcer.alert(message=voice_message, level=alert_level, immediate=immediate)
