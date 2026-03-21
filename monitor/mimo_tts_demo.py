#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi MiMo-V2-TTS Demo
小米 MiMo-V2-TTS 语音合成示例

功能：
- 非流式语音合成（生成完整音频文件）
- 流式语音合成（实时播放）
- 支持多种风格控制（情绪、方言、语速等）
- 支持多种音色选择

使用前请设置环境变量：
export MIMO_API_KEY="your-api-key"
"""

import os
import base64
from pyexpat import model
import wave
import io
import time
import threading
import queue
from enum import Enum
from typing import Optional, Literal
from datetime import datetime

import numpy as np
import soundfile as sf
from openai import OpenAI


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重/紧急


class MiMoTTSClient:
    """MiMo-V2-TTS 客户端"""

    # 支持的音色
    VOICES = {
        "mimo_default": "MiMo-默认",
        "default_zh": "MiMo-中文女声",
        "default_en": "MiMo-英文女声",
    }

    # 支持的风格标签
    STYLES = {
        "语速": ["变快", "变慢"],
        "情绪": ["开心", "悲伤", "生气"],
        "角色": ["孙悟空", "林黛玉"],
        "风格": ["悄悄话", "夹子音", "台湾腔"],
        "方言": ["东北话", "四川话", "河南话", "粤语"],
        "唱歌": ["唱歌"],
    }

    # 告警级别对应的语音风格配置
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
            api_key: API Key，如果不提供则从环境变量 MIMO_API_KEY 获取
        """
        self.api_key = api_key or os.environ.get("MIMO_API_KEY")
        if not self.api_key:
            raise ValueError("请提供 API Key 或设置 MIMO_API_KEY 环境变量")

        # 从环境变量读取 API 密钥和基础 URL
        tts_api_key = os.getenv("TTS_API_KEY")
        tts_base_url = os.getenv("TTS_BASE_URL", "https://www.dmxapi.cn/v1")

        if not tts_api_key:
            raise ValueError("请设置 TTS_API_KEY 环境变量")

        self.client = OpenAI(
            api_key=tts_api_key,
            base_url=tts_base_url,
        )

    def synthesize(
        self,
        text: str,
        voice: Literal["mimo_default", "default_zh", "default_en"] = "mimo_default",
        format: Literal["wav", "mp3"] = "wav",
        user_message: Optional[str] = None,
    ) -> bytes:
        """
        非流式语音合成

        Args:
            text: 要合成的文本（支持 <style>标签</style> 风格控制）
            voice: 音色选择
            format: 音频格式
            user_message: 可选的用户消息，可调整语音合成的语气与风格

        Returns:
            音频数据的 bytes
        """
        messages = []

        # 可选的用户消息
        if user_message:
            messages.append({
                "role": "user",
                "content": user_message
            })

        # 语音合成的目标文本必须放在 assistant 角色的消息中
        messages.append({
            "role": "assistant",
            "content": text
        })

        completion = self.client.chat.completions.create(
            model="mimo-v2-tts",
            messages=messages,
            audio={
                "format": format,
                "voice": voice
            }
        )

        message = completion.choices[0].message
        audio_data = base64.b64decode(message.audio.data)

        return audio_data

    def synthesize_streaming(
        self,
        text: str,
        voice: Literal["mimo_default", "default_zh", "default_en"] = "mimo_default",
        user_message: Optional[str] = None,
    ):
        """
        流式语音合成（生成器，yield 音频 chunks）

        Args:
            text: 要合成的文本
            voice: 音色选择
            user_message: 可选的用户消息

        Yields:
            numpy.ndarray: 音频数据 chunks (float32, -1.0 ~ 1.0)
        """
        messages = []

        if user_message:
            messages.append({
                "role": "user",
                "content": user_message
            })

        messages.append({
            "role": "assistant",
            "content": text
        })

        completion = self.client.chat.completions.create(
            model="mimo-v2-tts",
            messages=messages,
            audio={
                "format": "pcm16",  # 流式调用必须使用 pcm16
                "voice": voice
            },
            stream=True
        )

        for chunk in completion:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            audio = getattr(delta, "audio", None)

            if audio is not None and isinstance(audio, dict):
                pcm_bytes = base64.b64decode(audio["data"])
                # 将 PCM16 转换为 float32 (-1.0 ~ 1.0)
                np_pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                yield np_pcm

    def save_audio(self, audio_data: bytes, filename: str, sample_rate: int = 24000):
        """
        保存音频数据到文件

        Args:
            audio_data: 音频数据 bytes
            filename: 输出文件名
            sample_rate: 采样率
        """
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"音频已保存到: {filename}")

    def save_pcm_to_wav(self, audio_chunks: list, filename: str, sample_rate: int = 24000):
        """
        将 PCM chunks 保存为 WAV 文件

        Args:
            audio_chunks: numpy.ndarray chunks 列表
            filename: 输出文件名
            sample_rate: 采样率
        """
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
        """
        语音播报告警信息

        Args:
            message: 告警消息内容
            level: 告警级别
            custom_style: 自定义风格标签（覆盖默认配置）
            custom_voice: 自定义音色（覆盖默认配置）
            repeat: 重复播报次数（覆盖默认配置）
            save_file: 保存音频文件路径（可选）

        Returns:
            音频数据 bytes
        """
        # 获取级别配置
        config = self.ALERT_STYLES.get(level, self.ALERT_STYLES[AlertLevel.INFO])

        # 应用自定义配置
        style = custom_style if custom_style is not None else config["style"]
        voice = custom_voice if custom_voice is not None else config["voice"]
        repeat_count = repeat if repeat is not None else config["repeat"]

        # 构建播报文本
        prefix = config["prefix"]
        text = f"{style}{prefix}{message}"

        print(f"[{level.value.upper()}] 语音播报: {prefix}{message} (重复{repeat_count}次)")

        # 合成语音
        audio_data = self.synthesize(text, voice=voice)

        # 保存文件（如果需要）
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
        """
        流式语音播报告警信息（实时播放）

        Args:
            message: 告警消息内容
            level: 告警级别
            custom_style: 自定义风格标签
            custom_voice: 自定义音色

        Yields:
            numpy.ndarray: 音频数据 chunks
        """
        config = self.ALERT_STYLES.get(level, self.ALERT_STYLES[AlertLevel.INFO])
        style = custom_style if custom_style is not None else config["style"]
        voice = custom_voice if custom_voice is not None else config["voice"]
        prefix = config["prefix"]
        text = f"{style}{prefix}{message}"

        print(f"[{level.value.upper()}] 流式播报: {prefix}{message}")

        yield from self.synthesize_streaming(text, voice=voice)


class AlertAnnouncer:
    """
    告警播报管理器
    支持告警队列、优先级管理、定时播报等功能
    """

    def __init__(self, tts_client: MiMoTTSClient):
        """
        初始化告警播报器

        Args:
            tts_client: MiMoTTSClient 实例
        """
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
        """获取告警优先级（数字越小优先级越高）"""
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
        """
        添加告警到播报队列

        Args:
            message: 告警消息
            level: 告警级别
            immediate: 是否立即打断当前播报
            repeat: 重复播报次数
            interval: 重复播报间隔（秒）
        """
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

        # 记录历史
        with self._lock:
            self.alert_history.append(alert_item)
            if len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)

        if immediate and self.is_speaking:
            # 紧急告警：清空队列，立即播报
            self._clear_queue()
            print(f"[紧急打断] 收到紧急告警，立即播报")

        # 添加到优先级队列
        self.alert_queue.put((priority, timestamp.timestamp(), alert_item))
        print(f"[队列] 告警已添加: [{level.value}] {message}")

        # 启动工作线程
        self._ensure_worker()

    def _clear_queue(self):
        """清空告警队列"""
        while not self.alert_queue.empty():
            try:
                self.alert_queue.get_nowait()
            except queue.Empty:
                break

    def _ensure_worker(self):
        """确保工作线程在运行"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._process_alerts, daemon=True)
            self._worker_thread.start()

    def _process_alerts(self):
        """处理告警队列的工作线程"""
        while not self._stop_event.is_set():
            try:
                # 获取队列中的告警（阻塞等待）
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
        """播报单个告警"""
        message = alert_item["message"]
        level = alert_item["level"]
        repeat = alert_item.get("repeat")
        interval = alert_item.get("interval", 0)

        # 确定重复次数
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
        """停止播报"""
        self._stop_event.set()
        self._clear_queue()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        print("[播报器] 已停止")

    def get_status(self) -> dict:
        """获取当前状态"""
        with self._lock:
            return {
                "is_speaking": self.is_speaking,
                "queue_size": self.alert_queue.qsize(),
                "current_alert": self.current_alert,
                "history_count": len(self.alert_history),
            }

    def get_history(self, level: Optional[AlertLevel] = None) -> list:
        """获取告警历史"""
        with self._lock:
            if level:
                return [a for a in self.alert_history if a["level"] == level]
            return self.alert_history.copy()

    def clear_history(self):
        """清空历史记录"""
        with self._lock:
            self.alert_history.clear()
            print("[历史] 已清空告警历史")


def demo_basic():
    """基础示例：简单的语音合成"""
    print("=" * 50)
    print("示例 1: 基础语音合成")
    print("=" * 50)

    tts = MiMoTTSClient()

    text = "你好，我是小米 MiMo 语音合成助手，很高兴为你服务！"
    print(f"合成文本: {text}")

    audio_data = tts.synthesize(text, voice="default_zh")
    tts.save_audio(audio_data, "output_basic.wav")


def demo_with_style():
    """风格控制示例"""
    print("\n" + "=" * 50)
    print("示例 2: 风格控制")
    print("=" * 50)

    tts = MiMoTTSClient()

    # 不同风格的示例
    examples = [
        ("<style>开心</style>明天就是周五了，真开心！", "output_happy.wav"),
        ("<style>东北话</style>哎呀妈呀，这天儿也忒冷了吧！", "output_dongbei.wav"),
        ("<style>粤语</style>呢个真係好正啊！食过一次就唔会忘记！", "output_cantonese.wav"),
        ("<style>四川话</style>这个火锅巴适得板，好安逸哦！", "output_sichuan.wav"),
        ("<style>悄悄话</style>我跟你说个秘密，你不要告诉别人哦。", "output_whisper.wav"),
    ]

    for text, filename in examples:
        print(f"\n合成: {text}")
        audio_data = tts.synthesize(text, voice="default_zh")
        tts.save_audio(audio_data, filename)


def demo_singing():
    """唱歌示例"""
    print("\n" + "=" * 50)
    print("示例 3: 歌声合成")
    print("=" * 50)

    tts = MiMoTTSClient()

    # 注意：唱歌风格必须在目标文本最开头仅添加 <style>唱歌</style> 标签
    lyrics = "<style>唱歌</style>原谅我这一生不羁放纵爱自由，也会怕有一天会跌倒。"
    print(f"合成歌词: {lyrics}")

    audio_data = tts.synthesize(lyrics, voice="default_zh")
    tts.save_audio(audio_data, "output_singing.wav")


def demo_streaming():
    """流式合成示例"""
    print("\n" + "=" * 50)
    print("示例 4: 流式语音合成")
    print("=" * 50)

    tts = MiMoTTSClient()

    text = "这是一个流式语音合成的示例，音频会分块返回。"
    print(f"合成文本: {text}")

    chunks = []
    for i, chunk in enumerate(tts.synthesize_streaming(text, voice="default_zh")):
        chunks.append(chunk)
        print(f"  收到音频块 {i+1}, 大小: {len(chunk)} 采样点")

    tts.save_pcm_to_wav(chunks, "output_streaming.wav")


def demo_english():
    """英文语音合成示例"""
    print("\n" + "=" * 50)
    print("示例 5: 英文语音合成")
    print("=" * 50)

    tts = MiMoTTSClient()

    text = "Hello, this is MiMo text-to-speech system. I can speak natural English."
    print(f"合成文本: {text}")

    audio_data = tts.synthesize(text, voice="default_en")
    tts.save_audio(audio_data, "output_english.wav")


def demo_emotion_tags():
    """音频标签细粒度控制示例"""
    print("\n" + "=" * 50)
    print("示例 6: 音频标签细粒度控制")
    print("=" * 50)

    tts = MiMoTTSClient()

    examples = [
        ("（紧张，深呼吸）呼……冷静，冷静。不就是一个面试吗……", "output_nervous.wav"),
        ("（极其疲惫，有气无力）师傅……到地方了叫我一声……", "output_tired.wav"),
        ("（提高音量喊话）大姐！这鱼新鲜着呢！早上刚捞上来的！", "output_loud.wav"),
    ]

    for text, filename in examples:
        print(f"\n合成: {text}")
        audio_data = tts.synthesize(text, voice="default_zh")
        tts.save_audio(audio_data, filename)


def demo_with_context():
    """带上下文的语音合成"""
    print("\n" + "=" * 50)
    print("示例 7: 带上下文的语音合成")
    print("=" * 50)

    tts = MiMoTTSClient()

    # 用户消息可以调整语音合成的语气
    user_msg = "请用温柔、关心的语气回答"
    assistant_text = "别担心，一切都会好起来的。你要相信自己！"

    print(f"用户消息: {user_msg}")
    print(f"助手回复: {assistant_text}")

    audio_data = tts.synthesize(
        text=assistant_text,
        voice="default_zh",
        user_message=user_msg
    )
    tts.save_audio(audio_data, "output_with_context.wav")


def demo_alert_basic():
    """基础告警播报示例"""
    print("\n" + "=" * 50)
    print("示例 8: 基础告警播报")
    print("=" * 50)

    tts = MiMoTTSClient()

    # 不同级别的告警
    alerts = [
        (AlertLevel.INFO, "系统启动完成"),
        (AlertLevel.WARNING, "磁盘空间不足，请及时清理"),
        (AlertLevel.ERROR, "数据库连接失败"),
        (AlertLevel.CRITICAL, "服务器宕机，请立即处理"),
    ]

    for level, message in alerts:
        print(f"\n--- {level.value.upper()} ---")
        tts.speak_alert(message, level=level, save_file=f"alert_{level.value}.wav")


def demo_alert_announcer():
    """告警播报管理器示例"""
    print("\n" + "=" * 50)
    print("示例 9: 告警播报管理器（队列管理）")
    print("=" * 50)

    tts = MiMoTTSClient()
    announcer = AlertAnnouncer(tts)

    # 添加各种级别的告警到队列
    announcer.alert("系统运行正常", level=AlertLevel.INFO)
    announcer.alert("CPU 使用率超过 80%", level=AlertLevel.WARNING)
    announcer.alert("内存不足", level=AlertLevel.ERROR)

    # 紧急告警：立即打断其他播报
    announcer.alert(
        "网络连接中断",
        level=AlertLevel.CRITICAL,
        immediate=True,
        repeat=3,
        interval=1.0
    )

    # 等待播报完成
    print("\n等待告警播报完成...")
    time.sleep(15)

    # 查看状态和历史
    status = announcer.get_status()
    print(f"\n播报器状态: {status}")

    history = announcer.get_history()
    print(f"\n告警历史记录数: {len(history)}")

    announcer.stop()


def demo_alert_system_monitor():
    """系统监控告警示例"""
    print("\n" + "=" * 50)
    print("示例 10: 系统监控告警场景")
    print("=" * 50)

    tts = MiMoTTSClient()
    announcer = AlertAnnouncer(tts)

    # 模拟系统监控场景
    scenarios = [
        ("服务启动", AlertLevel.INFO),
        ("检测到异常登录尝试", AlertLevel.WARNING),
        ("备份任务完成", AlertLevel.INFO),
        ("数据库主从同步延迟超过 10 秒", AlertLevel.ERROR),
        ("核心服务无响应", AlertLevel.CRITICAL),
    ]

    print("模拟系统监控告警场景...")
    for message, level in scenarios:
        announcer.alert(message, level=level)
        time.sleep(0.5)  # 模拟告警产生间隔

    # 等待所有告警播报完成
    while announcer.get_status()["queue_size"] > 0 or announcer.get_status()["is_speaking"]:
        time.sleep(1)

    print("\n所有告警播报完成")

    # 查看历史
    for level in AlertLevel:
        count = len(announcer.get_history(level))
        print(f"  {level.value}: {count} 条")

    announcer.stop()


def demo_alert_custom_style():
    """自定义告警风格示例"""
    print("\n" + "=" * 50)
    print("示例 11: 自定义告警播报风格")
    print("=" * 50)

    tts = MiMoTTSClient()

    # 使用自定义风格
    tts.speak_alert(
        "检测到火灾风险",
        level=AlertLevel.CRITICAL,
        custom_style="<style>东北话</style><style>变快</style>",
        custom_voice="default_zh",
        repeat=3,
        save_file="alert_custom.wav"
    )

    print("\n自定义风格告警已生成")


def main():
    """运行所有示例"""
    print("MiMo-V2-TTS 语音合成 Demo")
    print("=" * 50)

    # 检查 API Key
    if not os.environ.get("MIMO_API_KEY"):
        print("\n错误: 请设置 MIMO_API_KEY 环境变量")
        print("示例: export MIMO_API_KEY='your-api-key'")
        return

    try:
        # 运行基础示例
        demo_basic()
        demo_with_style()
        demo_singing()
        demo_streaming()
        demo_english()
        demo_emotion_tags()
        demo_with_context()

        # 运行告警播报示例
        demo_alert_basic()
        demo_alert_announcer()
        demo_alert_system_monitor()
        demo_alert_custom_style()

        print("\n" + "=" * 50)
        print("所有示例运行完成！")
        print("生成的音频文件保存在当前目录")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        raise


if __name__ == "__main__":
    main()
