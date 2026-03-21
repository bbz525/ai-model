import cv2
import time
import imutils

from monitor.config import (
    CAMERA_URL,
    MAX_RECONNECT_ATTEMPTS,
    FRAME_RESIZE,
    DETECT_AFTER_MOTION,
)
from monitor.detection.camera import connect_camera, reconnect_camera
from monitor.detection.motion import motion_detection
from monitor.detection.ollama import call_ollama
from monitor.notification.dispatcher import trigger_alert
from monitor.tts.base import AlertLevel
from monitor.tts.voice import VoiceAnnouncer, get_risk_alert_level
from monitor.tts.mimo import MiMoTTSClient
from monitor.config import TTS_ENABLE, TTS_MIN_LEVEL, TTS_REPEAT


def init_voice_announcer():
    if not TTS_ENABLE:
        return None
    try:
        tts = MiMoTTSClient()
        min_level = AlertLevel(TTS_MIN_LEVEL)
        return VoiceAnnouncer(tts, min_level=min_level, repeat=TTS_REPEAT)
    except Exception as e:
        print(f"⚠️ 语音播报初始化失败: {e}")
        return None


if __name__ == "__main__":
    print("🔍 启动 Motion + Ollama 异常检测系统...")

    voice_announcer = init_voice_announcer()
    if voice_announcer and voice_announcer.enabled:
        voice_announcer.speak_immediate("安防监控系统启动", level=AlertLevel.INFO)

    cap, prev_frame = connect_camera(CAMERA_URL, MAX_RECONNECT_ATTEMPTS, voice_announcer)
    if cap is None:
        print("❌ 无法连接视频源，程序退出")
        exit(1)

    prev_frame = imutils.resize(prev_frame, width=FRAME_RESIZE)

    motion_detected = False
    motion_time = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5

    while True:
        ret, curr_frame = cap.read()
        if not ret:
            consecutive_failures += 1
            print(f"❌ 读取视频源失败（连续{consecutive_failures}次）")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                cap.release()
                cap, frame = reconnect_camera(CAMERA_URL, MAX_RECONNECT_ATTEMPTS, voice_announcer)
                if cap is None:
                    print("❌ 重连失败，程序退出")
                    exit(1)
                ret, prev_frame = cap.read()
                if not ret:
                    print("❌ 重连后无法读取帧")
                    cap.release()
                    continue
                prev_frame = imutils.resize(prev_frame, width=FRAME_RESIZE)
                consecutive_failures = 0
                motion_detected = False
                motion_time = 0
                print("✅ 重连成功，恢复检测")
                if voice_announcer and voice_announcer.enabled:
                    voice_announcer.speak_immediate("摄像头重连成功", level=AlertLevel.INFO)
            else:
                time.sleep(0.5)
            continue

        consecutive_failures = 0
        curr_frame_resized = imutils.resize(curr_frame, width=FRAME_RESIZE)

        if not motion_detection(prev_frame, curr_frame_resized):
            motion_detected = False
            prev_frame = curr_frame_resized
            print(f"✅ {time.strftime('%H:%M:%S')} - 无移动")
            time.sleep(0.5)
            continue

        if not motion_detected:
            motion_detected = True
            motion_time = time.time()
            print(f"\n⚠️ {time.strftime('%H:%M:%S')} - 检测到移动，等待{DETECT_AFTER_MOTION}秒...")

        if motion_detected and (time.time() - motion_time) >= DETECT_AFTER_MOTION:
            frame_path = "motion_frame.jpg"
            cv2.imwrite(frame_path, curr_frame)

            result = call_ollama(frame_path)
            print(f"###result {result}\n")

            status = result.get("status", "unknown") if result else "unknown"
            detection = result.get("detection", "").strip() if result else ""

            if result and detection:
                risk_level = result.get("risk_level", "medium")
                if voice_announcer and voice_announcer.enabled:
                    voice_level = get_risk_alert_level(risk_level)
                    voice_announcer.alert(message=detection, level=voice_level, immediate=False)

                if status == "alert":
                    alert_info = {
                        "type": detection,
                        "desc": f"风险等级: {risk_level}, 置信度: {result.get('confidence', 0):.2%}",
                        "confidence": result.get("confidence", 0),
                        "risk_level": risk_level,
                    }
                    trigger_alert(alert_info, frame_path, voice_announcer)
                else:
                    print(f"✅ {time.strftime('%H:%M:%S')} - 状态安全（{status}），已语音播报")
            else:
                print(f"✅ {time.strftime('%H:%M:%S')} - 状态安全（{status}）")

            motion_detected = False

        prev_frame = curr_frame_resized
        time.sleep(0.1)

    cap.release()
    if voice_announcer:
        voice_announcer.stop()
