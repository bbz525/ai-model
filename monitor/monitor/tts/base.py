from enum import Enum
from typing import Protocol, runtime_checkable


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@runtime_checkable
class TTSProvider(Protocol):
    """TTS 提供者协议：任何实现此接口的类均可用于语音播报"""

    def speak_alert(
        self,
        message: str,
        level: "AlertLevel" = AlertLevel.INFO,
        **kwargs,
    ) -> bytes:
        """合成告警语音，返回 WAV 格式音频字节"""
        ...

    def is_available(self) -> bool:
        """返回该 TTS 提供者是否已就绪"""
        ...
