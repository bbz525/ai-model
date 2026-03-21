import os
import base64
import queue
import threading
import time
from typing import Optional, Literal

import numpy as np
import soundfile as sf
from openai import OpenAI

from monitor.tts.base import AlertLevel


class MiMoTTSClient:
    """MiMo-V2-TTS 客户端"""

    VOICES = {
        "mimo_default": "MiMo-默认",
        "default_zh": "MiMo-中文女声",
        "default_en": "MiMo-英文女声",
    }

    STYLES = {
        "语速": ["变快", "变慢"],
        "情绪": ["开心", "悲伤", "生气"],
        "角色": ["孙悟空", "林黛玉"],
        "风格": ["悄悄话", "夹子音", "台湾腔"],
        "方言": ["东北话", "四川话", "河南话", "粤语"],
        "唱歌": ["唱歌"],
    }

    ALERT_STYLES = {
        AlertLevel.INFO: {
            "prefix": "提示：",
            "style": "",
            "voice": "default_zh",
            "repeat": 1,
        },
        AlertLevel.WARNING: {
            "prefix": "警告：",
            "style": "<style>变快</style>",
            "voice": "default_zh",
            "repeat": 1,
        },
        AlertLevel.ERROR: {
            "prefix": "错误：",
            "style": "<style>生气</style>",
            "voice": "default_zh",
            "repeat": 2,
        },
        AlertLevel.CRITICAL: {
            "prefix": "紧急告警：",
            "style": "<style>变快</style><style>生气</style>",
            "voice": "default_zh",
            "repeat": 3,
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 TTS 客户端

        Args:
            api_key: 优先使用此参数，否则从 TTS_API_KEY 环境变量读取
        """
        resolved_key = api_key or os.getenv("TTS_API_KEY")
        if not resolved_key:
            raise ValueError("请提供 api_key 参数或设置 TTS_API_KEY 环境变量")

        base_url = os.getenv("TTS_BASE_URL", "https://www.dmxapi.cn/v1")
        self.client = OpenAI(api_key=resolved_key, base_url=base_url)

    def is_available(self) -> bool:
        return self.client is not None

    def synthesize(
        self,
        text: str,
        voice: Literal["mimo_default", "default_zh", "default_en"] = "mimo_default",
        format: Literal["wav", "mp3"] = "wav",
        user_message: Optional[str] = None,
    ) -> bytes:
        """非流式语音合成，返回音频字节"""
        messages = []
        if user_message:
            messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": text})

        completion = self.client.chat.completions.create(
            model="mimo-v2-tts",
            messages=messages,
            audio={"format": format, "voice": voice},
        )
        return base64.b64decode(completion.choices[0].message.audio.data)

    def synthesize_streaming(
        self,
        text: str,
        voice: Literal["mimo_default", "default_zh", "default_en"] = "mimo_default",
        user_message: Optional[str] = None,
    ):
        """流式语音合成，yield numpy.ndarray 音频 chunks (float32)"""
        messages = []
        if user_message:
            messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": text})

        completion = self.client.chat.completions.create(
            model="mimo-v2-tts",
            messages=messages,
            audio={"format": "pcm16", "voice": voice},
            stream=True,
        )
        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            audio = getattr(delta, "audio", None)
            if audio is not None and isinstance(audio, dict):
                pcm_bytes = base64.b64decode(audio["data"])
                yield np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    def save_audio(self, audio_data: bytes, filename: str, sample_rate: int = 24000):
        """保存音频字节到文件"""
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"音频已保存到: {filename}")

    def save_pcm_to_wav(self, audio_chunks: list, filename: str, sample_rate: int = 24000):
        """将 PCM chunks 保存为 WAV 文件"""
        if not audio_chunks:
            print("没有音频数据")
            return
        collected_audio = np.concatenate(audio_chunks)
        sf.write(filename, collected_audio, samplerate=sample_rate)
        print(f"音频已保存到: {filename}")

    def speak_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        custom_style: Optional[str] = None,
        custom_voice: Optional[str] = None,
        repeat: Optional[int] = None,
        save_file: Optional[str] = None,
    ) -> bytes:
        """语音播报告警信息，返回 WAV 音频字节"""
        config = self.ALERT_STYLES.get(level, self.ALERT_STYLES[AlertLevel.INFO])
        style = custom_style if custom_style is not None else config["style"]
        voice = custom_voice if custom_voice is not None else config["voice"]
        repeat_count = repeat if repeat is not None else config["repeat"]
        prefix = config["prefix"]
        text = f"{style}{prefix}{message}"

        print(f"[{level.value.upper()}] 语音播报: {prefix}{message} (重复{repeat_count}次)")
        audio_data = self.synthesize(text, voice=voice)

        if save_file:
            self.save_audio(audio_data, save_file)

        return audio_data

    def speak_alert_streaming(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        custom_style: Optional[str] = None,
        custom_voice: Optional[str] = None,
    ):
        """流式语音播报告警信息，yield numpy.ndarray 音频 chunks"""
        config = self.ALERT_STYLES.get(level, self.ALERT_STYLES[AlertLevel.INFO])
        style = custom_style if custom_style is not None else config["style"]
        voice = custom_voice if custom_voice is not None else config["voice"]
        prefix = config["prefix"]
        text = f"{style}{prefix}{message}"

        print(f"[{level.value.upper()}] 流式播报: {prefix}{message}")
        yield from self.synthesize_streaming(text, voice=voice)


class AlertAnnouncer:
    """告警播报管理器，支持告警队列、优先级管理"""

    def __init__(self, tts_client: MiMoTTSClient):
        self.tts = tts_client
        self.alert_queue = queue.PriorityQueue()
        self.is_speaking = False
        self.current_alert = None
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._lock = threading.Lock()
        self.alert_history = []
        self.max_history = 100

    def _get_priority(self, level: AlertLevel) -> int:
        priorities = {
            AlertLevel.CRITICAL: 1,
            AlertLevel.ERROR: 2,
            AlertLevel.WARNING: 3,
            AlertLevel.INFO: 4,
        }
        return priorities.get(level, 5)

    def alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        immediate: bool = False,
        repeat: Optional[int] = None,
        interval: float = 0,
    ):
        """添加告警到播报队列"""
        from datetime import datetime

        timestamp = datetime.now()
        priority = self._get_priority(level)

        alert_item = {
            "message": message,
            "level": level,
            "timestamp": timestamp,
            "repeat": repeat,
            "interval": interval,
            "repeat_count": 0,
        }

        with self._lock:
            self.alert_history.append(alert_item)
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)

        if immediate and self.is_speaking:
            self._clear_queue()
            print("[紧急打断] 收到紧急告警，立即播报")

        self.alert_queue.put((priority, timestamp.timestamp(), alert_item))
        print(f"[队列] 告警已添加: [{level.value}] {message}")
        self._ensure_worker()

    def _clear_queue(self):
        while not self.alert_queue.empty():
            try:
                self.alert_queue.get_nowait()
            except queue.Empty:
                break

    def _ensure_worker(self):
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._process_alerts, daemon=True)
            self._worker_thread.start()

    def _process_alerts(self):
        while not self._stop_event.is_set():
            try:
                priority, _, alert_item = self.alert_queue.get(timeout=1)
                with self._lock:
                    self.is_speaking = True
                    self.current_alert = alert_item
                try:
                    self._speak_alert_item(alert_item)
                finally:
                    with self._lock:
                        self.is_speaking = False
                        self.current_alert = None
                self.alert_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[错误] 播报异常: {e}")

    def _speak_alert_item(self, alert_item: dict):
        message = alert_item["message"]
        level = alert_item["level"]
        repeat = alert_item.get("repeat")
        interval = alert_item.get("interval", 0)

        if repeat is None:
            repeat = self.tts.ALERT_STYLES[level]["repeat"]

        for i in range(repeat):
            try:
                print(f"[播报 {i+1}/{repeat}] {message}")
                self.tts.speak_alert(message, level=level)
                if i < repeat - 1 and interval > 0:
                    time.sleep(interval)
            except Exception as e:
                print(f"[错误] 播报失败: {e}")

    def stop(self):
        self._stop_event.set()
        self._clear_queue()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        print("[播报器] 已停止")

    def get_status(self) -> dict:
        with self._lock:
            return {
                "is_speaking": self.is_speaking,
                "queue_size": self.alert_queue.qsize(),
                "current_alert": self.current_alert,
                "history_count": len(self.alert_history),
            }

    def get_history(self, level: Optional[AlertLevel] = None) -> list:
        with self._lock:
            if level:
                return [a for a in self.alert_history if a["level"] == level]
            return self.alert_history.copy()

    def clear_history(self):
        with self._lock:
            self.alert_history.clear()
            print("[历史] 已清空告警历史")
