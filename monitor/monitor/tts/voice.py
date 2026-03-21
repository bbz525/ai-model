import io
import time
from typing import Optional, TYPE_CHECKING

from monitor.tts.base import AlertLevel, TTSProvider

try:
    import soundfile as sf
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


def get_risk_alert_level(risk_level_str: str) -> AlertLevel:
    """将风险等级字符串转换为 AlertLevel"""
    risk_map = {
        "low": AlertLevel.INFO,
        "medium": AlertLevel.WARNING,
        "high": AlertLevel.ERROR,
        "critical": AlertLevel.CRITICAL,
    }
    return risk_map.get(risk_level_str.lower(), AlertLevel.WARNING)


class VoiceAnnouncer:
    """图像监控专用语音播报管理器"""

    def __init__(
        self,
        tts_provider: TTSProvider,
        min_level: AlertLevel = AlertLevel.INFO,
        repeat: int = 1,
    ):
        self.tts = tts_provider
        self.enabled = tts_provider.is_available()
        self.min_level = min_level
        self.repeat = repeat

    def _level_priority(self, level: AlertLevel) -> int:
        priorities = {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.ERROR: 3,
            AlertLevel.CRITICAL: 4,
        }
        return priorities.get(level, 0)

    def should_announce(self, level: AlertLevel) -> bool:
        if not self.enabled:
            return False
        return self._level_priority(level) >= self._level_priority(self.min_level)

    def alert(self, message: str, level: AlertLevel = AlertLevel.WARNING, immediate: bool = False):
        """添加语音告警并播放"""
        if not self.should_announce(level):
            return
        try:
            print(f"🔊 语音播报: {message}")
            audio_data = self.tts.speak_alert(message, level=level)
            self._play_audio(audio_data)
        except Exception as e:
            print(f"⚠️ 语音告警失败: {e}")

    def speak_immediate(self, message: str, level: AlertLevel = AlertLevel.INFO):
        """立即播报（阻塞式），用于系统启动等重要提示"""
        if not self.enabled:
            return
        try:
            print(f"🔊 立即播报: {message}")
            audio_data = self.tts.speak_alert(message, level=level)
            self._play_audio(audio_data)
        except Exception as e:
            print(f"⚠️ 立即播报失败: {e}")

    def _play_audio(self, audio_data: bytes, sample_rate: int = 24000):
        """播放 WAV 格式音频字节"""
        if not AUDIO_AVAILABLE:
            filename = f"tts_output_{int(time.time())}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"💾 音频已保存: {filename}")
            except Exception as e:
                print(f"⚠️ 保存音频失败: {e}")
            return

        try:
            audio_io = io.BytesIO(audio_data)
            data, sr = sf.read(audio_io)
            sd.play(data, sr)
            sd.wait()
            print("✅ 音频播放完成")
        except Exception as e:
            print(f"⚠️ 音频播放失败: {e}")
            filename = f"tts_output_{int(time.time())}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"💾 音频已保存: {filename}")
            except Exception:
                pass

    def get_status(self) -> dict:
        return {"enabled": self.enabled}

    def stop(self):
        print("🛑 语音播报器已停止")
