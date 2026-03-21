import cv2
import json
import time
import requests
import base64
import numpy as np
import imutils
import os
import sys
import threading
import queue
import io
from datetime import datetime
from enum import Enum

# 添加父目录到路径，以便导入 mimo_tts_demo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入语音播报模块
try:
    from mimo_tts_demo import MiMoTTSClient, AlertAnnouncer, AlertLevel
    TTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 语音播报模块导入失败: {e}")
    TTS_AVAILABLE = False

# 导入音频播放模块
try:
    import soundfile as sf
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    print("⚠️ 音频播放模块(soundfile/sounddevice)未安装，语音将保存为文件")
    AUDIO_AVAILABLE = False

# ===================== 核心配置 =====================
# 1. 摄像头配置（替换成你的RTSP/本地摄像头）
CAMERA_URL = "http://192.168.1.13:8081"  # 摄像头RTSP
# CAMERA_URL = 0  # 本地USB摄像头用这个

# 1.1 重连配置
RECONNECT_INTERVAL = 5  # 重连间隔（秒）
MAX_RECONNECT_ATTEMPTS = 0  # 最大重连次数（0表示无限重连）

# 2. Motion 移动侦测配置
MIN_AREA = 500  # 最小移动面积（越小越灵敏，建议500-2000）
THRESHOLD = 25  # 像素变化阈值（值越小越灵敏）
FRAME_RESIZE = 500  # 缩放画面提升速度

# 3. Ollama 配置
OLLAMA_API = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen3.5"  # 用qwen-vl就改成这个
DETECT_AFTER_MOTION = 2  # 检测到移动后，延迟2秒再调用模型（避免误触发）
OLLAMA_TIMEOUT = 60  # Ollama调用超时时间（秒），根据模型调整
OLLAMA_MAX_RETRIES = 2  # Ollama调用失败重试次数

# 5. QQ机器人配置 - 方案2: 官方机器人
QQ_BOT_TYPE = "official"
QQ_OFFICIAL_APPID = os.getenv("QQ_OFFICIAL_APPID", "")           # 从环境变量或 .env 文件获取
QQ_OFFICIAL_SECRET = os.getenv("QQ_OFFICIAL_SECRET", "")         # 从环境变量或 .env 文件获取
# 用户ID（user_openid）需要在单聊中给机器人发消息后，从日志中获取
# 例如：ABC8B0C5BF538198C9A52B4B4EEAE0A3
QQ_OFFICIAL_USER_ID = os.getenv("QQ_OFFICIAL_USER_ID", "")

# 方案1: 使用 NapCat/go-cqhttp（备选）
# QQ_BOT_TYPE = "napcat"
# QQ_BOT_API = "http://127.0.0.1:3000"
# QQ_GROUP_ID = "123456789"

QQ_ENABLE = True  # 是否启用QQ告警

# 6. 语音播报配置
TTS_ENABLE = True  # 是否启用语音播报
TTS_ALERT_LEVEL = AlertLevel.INFO if TTS_AVAILABLE else None  # 触发语音播报的最低告警级别（INFO表示所有级别都播报）
TTS_REPEAT = 1  # 语音播报重复次数
TTS_QUEUE_SIZE = 10  # 语音播报队列大小

# 4. 异常检测提示词
PROMPT = """
你是一个专业的“婴幼儿安全监控AI”。请分析提供的视频帧或实时画面，重点识别婴儿是否存在危险行为。

【危险行为判定标准】
如果检测到以下情况，请立即标记为“告警”：
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
"""

# ===================== 语音播报管理器 =====================
class VoiceAnnouncer:
    """
    图像监控专用语音播报管理器
    简化版，专注于告警播报
    """

    def __init__(self, enabled=True, min_level=AlertLevel.INFO, repeat=2):
        """
        初始化语音播报器

        Args:
            enabled: 是否启用语音播报
            min_level: 最低播报级别，低于此级别的告警不播报
            repeat: 重复播报次数
        """
        self.enabled = enabled and TTS_AVAILABLE
        self.min_level = min_level
        self.repeat = repeat
        self.tts = None
        self.announcer = None
        self._init_tts()

    def _init_tts(self):
        """初始化 TTS 客户端"""
        if not self.enabled:
            return

        try:
            self.tts = MiMoTTSClient()
            self.announcer = AlertAnnouncer(self.tts)
            print("✅ 语音播报模块初始化成功")
        except Exception as e:
            print(f"❌ 语音播报初始化失败: {e}")
            self.enabled = False

    def _level_priority(self, level):
        """获取级别优先级数值"""
        priorities = {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.ERROR: 3,
            AlertLevel.CRITICAL: 4,
        }
        return priorities.get(level, 0)

    def should_announce(self, level):
        """判断是否应该播报该级别的告警"""
        if not self.enabled or not self.announcer:
            return False
        return self._level_priority(level) >= self._level_priority(self.min_level)

    def alert(self, message, level=AlertLevel.WARNING, immediate=False):
        """
        添加语音告警并播放

        Args:
            message: 告警消息
            level: 告警级别
            immediate: 是否立即播报（打断当前）
        """
        if not self.should_announce(level):
            return

        try:
            # 直接合成并播放，不通过队列
            print(f"🔊 语音播报: {message}")
            audio_data = self.tts.speak_alert(message, level=level)
            self._play_audio(audio_data)
        except Exception as e:
            print(f"⚠️ 语音告警失败: {e}")

    def speak_immediate(self, message, level=AlertLevel.INFO):
        """
        立即播报（不通过队列，阻塞式）
        用于系统启动等重要提示
        """
        if not self.enabled or not self.tts:
            return

        try:
            print(f"🔊 立即播报: {message}")
            audio_data = self.tts.speak_alert(message, level=level)
            # 播放音频
            self._play_audio(audio_data)
        except Exception as e:
            print(f"⚠️ 立即播报失败: {e}")

    def _play_audio(self, audio_data: bytes, sample_rate: int = 24000):
        """
        播放音频数据

        Args:
            audio_data: WAV格式的音频数据
            sample_rate: 采样率
        """
        if not AUDIO_AVAILABLE:
            # 保存为文件
            filename = f"tts_output_{int(time.time())}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"💾 音频已保存: {filename}")
            except Exception as e:
                print(f"⚠️ 保存音频失败: {e}")
            return

        try:
            # 使用 sounddevice 播放
            import io as bio
            audio_io = bio.BytesIO(audio_data)
            data, sr = sf.read(audio_io)
            sd.play(data, sr)
            sd.wait()  # 等待播放完成
            print("✅ 音频播放完成")
        except Exception as e:
            print(f"⚠️ 音频播放失败: {e}")
            # 保存为文件备用
            filename = f"tts_output_{int(time.time())}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"💾 音频已保存: {filename}")
            except:
                pass

    def get_status(self):
        """获取播报器状态"""
        if not self.enabled or not self.announcer:
            return {"enabled": False}
        return self.announcer.get_status()

    def stop(self):
        """停止播报器"""
        if self.announcer:
            self.announcer.stop()
            print("🛑 语音播报器已停止")


# 全局语音播报器实例
voice_announcer = None


def init_voice_announcer():
    """初始化全局语音播报器"""
    global voice_announcer
    if TTS_ENABLE and TTS_AVAILABLE:
        voice_announcer = VoiceAnnouncer(
            enabled=True,
            min_level=TTS_ALERT_LEVEL,
            repeat=TTS_REPEAT
        )
    return voice_announcer


def get_risk_alert_level(risk_level_str):
    """
    将风险等级字符串转换为 AlertLevel

    Args:
        risk_level_str: 'low', 'medium', 'critical' 等

    Returns:
        AlertLevel 枚举值
    """
    risk_map = {
        "low": AlertLevel.INFO,
        "medium": AlertLevel.WARNING,
        "high": AlertLevel.ERROR,
        "critical": AlertLevel.CRITICAL,
    }
    return risk_map.get(risk_level_str.lower(), AlertLevel.WARNING)


def extract_voice_message(detection: str, risk_level: str) -> str:
    """
    从检测描述中提取关键信息，生成简洁的语音消息

    Args:
        detection: 原始检测描述
        risk_level: 风险等级

    Returns:
        简洁的语音消息（控制在20字以内，确保能完整播报）
    """
    # 根据风险等级确定前缀
    prefix_map = {
        "low": "检测到",
        "medium": "注意，",
        "high": "警告，",
        "critical": "紧急，",
    }
    prefix = prefix_map.get(risk_level.lower(), "检测到")

    # 提取关键对象（婴儿、成人、儿童等）
    if "婴儿" in detection or "宝宝" in detection:
        return f"{prefix}婴儿"
    if "儿童" in detection or "小孩" in detection:
        return f"{prefix}儿童"

    # 检测危险行为
    if "逃离" in detection or "爬出" in detection:
        return f"{prefix}逃离行为"
    if "危险物品" in detection or "电源" in detection or "热水" in detection:
        return f"{prefix}危险物品"
    if "跌落" in detection:
        return f"{prefix}跌落风险"
    if "窒息" in detection:
        return f"{prefix}窒息风险"

    # 默认简化播报
    if "成人" in detection or "男性" in detection or "女性" in detection:
        return f"{prefix}成人活动"

    # 最简播报
    return f"{prefix}画面变化"


# ===================== Motion 移动侦测函数 =====================
def motion_detection(prev_frame, curr_frame):
    """对比两帧画面，检测是否有移动"""
    # 灰度化 + 高斯模糊（降噪）
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    curr_gray = cv2.GaussianBlur(curr_gray, (21, 21), 0)

    # 计算帧差 + 二值化
    frame_delta = cv2.absdiff(prev_gray, curr_gray)
    thresh = cv2.threshold(frame_delta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    # 查找轮廓
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # 判断是否有有效移动
    has_motion = False
    for c in cnts:
        if cv2.contourArea(c) > MIN_AREA:
            has_motion = True
            break
    return has_motion

# ===================== Ollama 调用函数 =====================
def image_to_base64(image_path):
    """图片转base64（Ollama要求）"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def call_ollama(image_path, retries=OLLAMA_MAX_RETRIES):
    """调用本地Ollama分析异常，支持重试"""
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                print(f"🔄 Ollama第{attempt + 1}次尝试...")
            
            # Qwen 3.5 使用 messages 格式（Ollama chat API）
            payload = {
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": PROMPT,
                        "images": [image_to_base64(image_path)]
                    }
                ],
                "stream": False,
                "format": "json"  # 要求返回JSON格式
            }
            
            # 使用 /api/chat 端点
            api_url = OLLAMA_API.replace("/generate", "/chat")
            response = requests.post(api_url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            raw_response = response_data.get("message", {}).get("content", "").strip()
            
            # 调试：打印原始响应
            if not raw_response:
                print(f"⚠️ Ollama返回空响应")
                print(f"📄 完整响应：{response_data}")
                return None
            
            # 尝试解析JSON
            try:
                result = json.loads(raw_response)
                return result
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON解析失败：{je}")
                print(f"📄 原始响应：{raw_response[:300]}...")  # 打印前300字符
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Ollama调用超时（{OLLAMA_TIMEOUT}秒）")
            if attempt < retries:
                print(f"⏳ 等待3秒后重试...")
                time.sleep(3)
            else:
                print(f"❌ Ollama调用失败：超过最大重试次数")
                return None
        except Exception as e:
            print(f"❌ Ollama调用失败：{str(e)}")
            if attempt < retries:
                print(f"⏳ 等待3秒后重试...")
                time.sleep(3)
            else:
                return None

# ===================== QQ官方机器人 Access Token 获取 =====================
def get_qq_official_token():
    """获取QQ官方机器人 Access Token"""
    try:
        response = requests.post(
            "https://bots.qq.com/app/getAppAccessToken",
            json={
                "appId": QQ_OFFICIAL_APPID,
                "clientSecret": QQ_OFFICIAL_SECRET
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"❌ 获取QQ官方Token失败：{str(e)}")
        return None


def get_qq_user_info(user_id):
    """获取指定用户的信息"""
    try:
        token = get_qq_official_token()
        if not token:
            return None
        
        headers = {
            "Authorization": f"QQBot {token}",
            "Content-Type": "application/json"
        }
        
        # 获取用户信息
        response = requests.get(
            f"https://api.sgroup.qq.com/v2/users/{user_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"❌ 获取用户信息失败：{str(e)}")
        return None




# ===================== QQ机器人告警函数 =====================
def send_qq_message_napcat(message, image_path=None):
    """使用 NapCat/go-cqhttp 发送QQ群消息"""
    try:
        # 如果有图片，先上传图片
        image_data = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # 构造消息
        if image_data:
            # 图文消息
            payload = {
                "group_id": QQ_GROUP_ID,
                "message": [
                    {"type": "text", "data": {"text": message}},
                    {"type": "image", "data": {"file": f"base64://{image_data}"}}
                ]
            }
        else:
            # 纯文本
            payload = {
                "group_id": QQ_GROUP_ID,
                "message": message
            }
        
        response = requests.post(
            f"{QQ_BOT_API}/send_group_msg",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        print(f"✅ QQ消息发送成功 (NapCat)")
        return True
    except Exception as e:
        print(f"❌ QQ消息发送失败：{str(e)}")
        return False


def send_qq_message_official(message, image_path=None):
    """使用 QQ官方机器人 API 发送单聊消息（通过本地 HTTP 接口调用 qq_chat.py）"""
    try:
        # 调用本地机器人服务的 HTTP 接口
        # 需要先启动 qq_chat.py，它会监听告警
        import urllib.request
        
        payload = {
            "user_openid": QQ_OFFICIAL_USER_ID,
            "content": message
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:8083/alert',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('success'):
                    print(f"✅ QQ消息发送成功")
                    return True
                else:
                    print(f"⚠️ QQ消息发送失败：{result.get('error', '未知错误')}")
                    return False
        except urllib.error.URLError as e:
            print(f"⚠️ 无法连接到机器人服务：{e}")
            print(f"💡 请确保 qq_chat.py 已启动，或检查 HTTP 接口是否可用")
            return False
            
    except Exception as e:
        print(f"❌ QQ消息发送失败：{str(e)}")
        return False


def send_qq_message(message, image_path=None):
    """发送QQ群消息，根据配置选择发送方式"""
    if not QQ_ENABLE:
        return
    
    if QQ_BOT_TYPE == "official":
        return send_qq_message_official(message, image_path)
    else:
        return send_qq_message_napcat(message, image_path)


# ===================== 告警函数 =====================
def trigger_alert(abnormal_info, image_path=None):
    """触发告警（控制台 + QQ机器人 + 语音播报）"""
    # 1. 控制台输出
    alert_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🚨 【{alert_time}】异常告警")
    print(f"类型：{abnormal_info['type']}")
    print(f"置信度：{abnormal_info['confidence']:.2f}")
    print(f"描述：{abnormal_info['desc']}")

    # 2. QQ机器人推送
    if QQ_ENABLE:
        qq_message = f"""🚨 安防监控异常告警
━━━━━━━━━━━━━━
⏰ 时间：{alert_time}
⚠️ 类型：{abnormal_info['type']}
📊 置信度：{abnormal_info['confidence']:.2%}
📝 描述：{abnormal_info['desc']}
━━━━━━━━━━━━━━"""
        send_qq_message(qq_message, image_path)

    # 3. 语音播报
    global voice_announcer
    if voice_announcer and TTS_ENABLE:
        # 构建语音告警消息
        risk_level = abnormal_info.get('risk_level', 'medium')
        alert_level = get_risk_alert_level(risk_level)

        # 根据风险等级构建不同的语音消息
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

        voice_announcer.alert(
            message=voice_message,
            level=alert_level,
            immediate=immediate
        )

# ===================== 视频源连接函数 =====================
def connect_camera(url, max_attempts=0):
    """
    连接视频源，支持重试
    max_attempts: 最大重试次数，0表示无限重试
    """
    attempt = 0
    while max_attempts == 0 or attempt < max_attempts:
        attempt += 1
        print(f"🔄 正在连接视频源... (第{attempt}次尝试)")
        cap = cv2.VideoCapture(url)
        
        # 设置缓冲区大小为1，降低延迟
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # 测试读取一帧
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✅ 视频源连接成功！")
            # 语音播报连接成功
            global voice_announcer
            if voice_announcer and voice_announcer.enabled:
                voice_announcer.speak_immediate("摄像头连接成功", level=AlertLevel.INFO)
            return cap, frame
        
        cap.release()
        print(f"❌ 连接失败，{RECONNECT_INTERVAL}秒后重试...")
        time.sleep(RECONNECT_INTERVAL)
    
    return None, None


def reconnect_camera(url, max_attempts=0):
    """重新连接视频源"""
    print("🔄 视频源断开，开始重连...")
    return connect_camera(url, max_attempts)


# ===================== 主程序 =====================
if __name__ == "__main__":
    print("🔍 启动 Motion + Ollama 异常检测系统...")

    # 初始化语音播报
    init_voice_announcer()
    if voice_announcer and voice_announcer.enabled:
        voice_announcer.speak_immediate("安防监控系统启动", level=AlertLevel.INFO)

    # 初始连接
    cap, prev_frame = connect_camera(CAMERA_URL, MAX_RECONNECT_ATTEMPTS)
    if cap is None:
        print("❌ 无法连接视频源，程序退出")
        exit(1)
    
    prev_frame = imutils.resize(prev_frame, width=FRAME_RESIZE)

    motion_detected = False  # 移动标记
    motion_time = 0  # 检测到移动的时间
    consecutive_failures = 0  # 连续读取失败次数
    MAX_CONSECUTIVE_FAILURES = 5  # 触发重连的连续失败阈值

    
    while True:
        # 读取当前帧
        ret, curr_frame = cap.read()
        if not ret:
            consecutive_failures += 1
            print(f"❌ 读取视频源失败（连续{consecutive_failures}次）")
            
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                # 释放旧连接
                cap.release()
                
                # 尝试重连
                cap, frame = reconnect_camera(CAMERA_URL, MAX_RECONNECT_ATTEMPTS)
                if cap is None:
                    print("❌ 重连失败，程序退出")
                    exit(1)
                
                # 重置状态
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
                # 语音播报重连成功
                if voice_announcer and voice_announcer.enabled:
                    voice_announcer.speak_immediate("摄像头重连成功", level=AlertLevel.INFO)
            else:
                time.sleep(0.5)
            continue
        
        # 读取成功，重置失败计数
        consecutive_failures = 0
        curr_frame_resized = imutils.resize(curr_frame, width=FRAME_RESIZE)

        # 1. 检测移动
        if not motion_detection(prev_frame, curr_frame_resized):
            motion_detected = False
            prev_frame = curr_frame_resized
            print(f"✅ {time.strftime('%H:%M:%S')} - 无移动")
            time.sleep(0.5)
            continue

        # 2. 检测到移动，记录时间
        if not motion_detected:
            motion_detected = True
            motion_time = time.time()
            print(f"\n⚠️ {time.strftime('%H:%M:%S')} - 检测到移动，等待{DETECT_AFTER_MOTION}秒...")

        # 3. 延迟后调用Ollama分析
        if motion_detected and (time.time() - motion_time) >= DETECT_AFTER_MOTION:
            # 保存当前帧（用于分析）
            frame_path = "motion_frame.jpg"
            cv2.imwrite(frame_path, curr_frame)  # 保存原始分辨率画面
            
            # 调用Ollama分析异常
            result = call_ollama(frame_path)
            print(f'###result {result}\n')
            
            # 解析新的响应格式
            status = result.get('status', 'unknown') if result else 'unknown'
            detection = result.get("detection", "").strip()

            if result and detection:
                # 有检测内容，进行语音播报
                risk_level = result.get('risk_level', 'medium')

                # 构建语音消息（播报完整 detection 原文）
                if voice_announcer and voice_announcer.enabled:
                    voice_level = get_risk_alert_level(risk_level)
                    voice_announcer.alert(message=detection, level=voice_level, immediate=False)

                # 如果是告警状态，额外触发告警通知（QQ等）
                if status == "alert":
                    alert_info = {
                        "type": detection,
                        "desc": f"风险等级: {risk_level}, 置信度: {result.get('confidence', 0):.2%}",
                        "confidence": result.get("confidence", 0),
                        "risk_level": risk_level
                    }
                    trigger_alert(alert_info, frame_path)  # 传入图片路径，QQ会收到图文告警
                else:
                    print(f"✅ {time.strftime('%H:%M:%S')} - 状态安全（{status}），已语音播报")
            else:
                print(f"✅ {time.strftime('%H:%M:%S')} - 状态安全（{status}）")
            
            # 重置标记
            motion_detected = False

        # 4. 更新前一帧
        prev_frame = curr_frame_resized
        time.sleep(0.1)  # 降低CPU占用

    cap.release()

    # 停止语音播报器
    if voice_announcer:
        voice_announcer.stop()
