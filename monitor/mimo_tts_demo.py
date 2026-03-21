#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiMo-V2-TTS Demo
使用前请设置环境变量：TTS_API_KEY
"""

import os
import time
from typing import Optional

from monitor.tts.base import AlertLevel
from monitor.tts.mimo import MiMoTTSClient, AlertAnnouncer


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
    user_msg = "请用温柔、关心的语气回答"
    assistant_text = "别担心，一切都会好起来的。你要相信自己！"
    print(f"用户消息: {user_msg}")
    print(f"助手回复: {assistant_text}")
    audio_data = tts.synthesize(text=assistant_text, voice="default_zh", user_message=user_msg)
    tts.save_audio(audio_data, "output_with_context.wav")


def demo_alert_basic():
    """基础告警播报示例"""
    print("\n" + "=" * 50)
    print("示例 8: 基础告警播报")
    print("=" * 50)

    tts = MiMoTTSClient()
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

    announcer.alert("系统运行正常", level=AlertLevel.INFO)
    announcer.alert("CPU 使用率超过 80%", level=AlertLevel.WARNING)
    announcer.alert("内存不足", level=AlertLevel.ERROR)
    announcer.alert("网络连接中断", level=AlertLevel.CRITICAL, immediate=True, repeat=3, interval=1.0)

    print("\n等待告警播报完成...")
    time.sleep(15)

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
        time.sleep(0.5)

    while announcer.get_status()["queue_size"] > 0 or announcer.get_status()["is_speaking"]:
        time.sleep(1)

    print("\n所有告警播报完成")
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
    tts.speak_alert(
        "检测到火灾风险",
        level=AlertLevel.CRITICAL,
        custom_style="<style>东北话</style><style>变快</style>",
        custom_voice="default_zh",
        repeat=3,
        save_file="alert_custom.wav",
    )
    print("\n自定义风格告警已生成")


def main():
    """运行所有示例"""
    print("MiMo-V2-TTS 语音合成 Demo")
    print("=" * 50)

    if not os.environ.get("TTS_API_KEY"):
        print("\n错误: 请设置 TTS_API_KEY 环境变量")
        return

    try:
        demo_basic()
        demo_with_style()
        demo_singing()
        demo_streaming()
        demo_english()
        demo_emotion_tags()
        demo_with_context()
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
