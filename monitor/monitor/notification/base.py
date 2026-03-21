from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    """告警通知渠道协议"""

    def send(self, message: str, image_path: Optional[str] = None) -> bool:
        """发送告警消息，返回是否成功"""
        ...

    def is_enabled(self) -> bool:
        """返回该通知渠道是否已启用"""
        ...
