import cv2
import imutils
import time
from typing import Optional, Tuple, Any

from monitor.config import RECONNECT_INTERVAL, FRAME_RESIZE
from monitor.tts.base import AlertLevel


def connect_camera(
    url,
    max_attempts: int = 0,
    voice_announcer: Optional[Any] = None,
) -> Tuple[Optional[cv2.VideoCapture], Any]:
    """
    连接视频源，支持无限重试。
    max_attempts=0 表示无限重试。
    返回 (VideoCapture, first_frame) 或 (None, None)。
    """
    attempt = 0
    while max_attempts == 0 or attempt < max_attempts:
        attempt += 1
        print(f"🔄 正在连接视频源... (第{attempt}次尝试)")
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ret, frame = cap.read()
        if ret and frame is not None:
            print("✅ 视频源连接成功！")
            if voice_announcer and getattr(voice_announcer, "enabled", False):
                voice_announcer.speak_immediate("摄像头连接成功", level=AlertLevel.INFO)
            return cap, frame

        cap.release()
        print(f"❌ 连接失败，{RECONNECT_INTERVAL}秒后重试...")
        time.sleep(RECONNECT_INTERVAL)

    return None, None


def reconnect_camera(
    url,
    max_attempts: int = 0,
    voice_announcer: Optional[Any] = None,
) -> Tuple[Optional[cv2.VideoCapture], Any]:
    """重新连接视频源"""
    print("🔄 视频源断开，开始重连...")
    return connect_camera(url, max_attempts, voice_announcer)
