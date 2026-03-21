#!/usr/bin/env python3
"""
配置验证脚本
用于验证 .env 配置文件是否完整有效
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def validate_config():
    """验证配置文件"""
    errors = []
    warnings = []

    # 检查必需配置
    required = ['CAMERA_URL', 'OLLAMA_API', 'MODEL_NAME']
    for key in required:
        value = os.getenv(key)
        if not value:
            errors.append(f"必需配置缺失: {key}")
        elif key == 'CAMERA_URL' and value == 'your_camera_url_here':
            warnings.append(f"{key} 仍为默认值，请修改为实际摄像头地址")

    # 检查 QQ 配置
    qq_type = os.getenv('QQ_BOT_TYPE', 'official')
    if qq_type == 'official':
        if not os.getenv('QQ_OFFICIAL_APPID') or os.getenv('QQ_OFFICIAL_APPID') == 'your_qq_appid_here':
            errors.append("官方机器人模式需要有效的 QQ_OFFICIAL_APPID")
        if not os.getenv('QQ_OFFICIAL_SECRET') or os.getenv('QQ_OFFICIAL_SECRET') == 'your_qq_secret_here':
            errors.append("官方机器人模式需要有效的 QQ_OFFICIAL_SECRET")
        if not os.getenv('QQ_OFFICIAL_USER_ID') or os.getenv('QQ_OFFICIAL_USER_ID') == 'your_qq_user_openid_here':
            warnings.append("QQ_OFFICIAL_USER_ID 未设置或为默认值，用户首次发消息后从日志获取")
    elif qq_type == 'napcat':
        if not os.getenv('QQ_BOT_API'):
            errors.append("NapCat 模式需要 QQ_BOT_API")
        if not os.getenv('QQ_GROUP_ID'):
            warnings.append("NapCat 模式推荐设置 QQ_GROUP_ID 用于群消息")
    else:
        errors.append(f"未知的 QQ_BOT_TYPE: {qq_type}，应为 'official' 或 'napcat'")

    # 检查 TTS 配置
    tts_enable = os.getenv('TTS_ENABLE', 'true').lower()
    if tts_enable in ('true', '1', 'yes'):
        tts_key = os.getenv('TTS_API_KEY')
        if not tts_key or tts_key == 'your_tts_api_key_here':
            errors.append("启用 TTS 需要有效的 TTS_API_KEY")
        tts_url = os.getenv('TTS_BASE_URL', 'https://www.dmxapi.cn/v1')
        if not tts_url.startswith('http'):
            warnings.append(f"TTS_BASE_URL 格式可能无效: {tts_url}")

    # 检查运动检测参数
    try:
        min_area = int(os.getenv('MIN_AREA', '500'))
        if min_area < 10:
            warnings.append(f"MIN_AREA={min_area} 过小可能导致误报")
    except ValueError:
        errors.append("MIN_AREA 必须是整数")

    try:
        threshold = int(os.getenv('THRESHOLD', '25'))
        if threshold < 5 or threshold > 255:
            warnings.append(f"THRESHOLD={threshold} 可能不合适 (建议 5-255)")
    except ValueError:
        errors.append("THRESHOLD 必须是整数")

    # 检查 Ollama 配置
    ollama_api = os.getenv('OLLAMA_API', 'http://127.0.0.1:11434/api/generate')
    if not ollama_api.startswith('http'):
        errors.append(f"OLLAMA_API 格式无效: {ollama_api}")

    return errors, warnings

def main():
    """主函数"""
    print("正在验证配置文件...")
    print("=" * 50)

    errors, warnings = validate_config()

    if warnings:
        print("警告:")
        for warning in warnings:
            print(f"  ⚠  {warning}")
        print()

    if errors:
        print("错误:")
        for error in errors:
            print(f"  ✗ {error}")
        print("\n配置验证失败！请修复上述错误。")
        sys.exit(1)
    else:
        print("✓ 配置验证通过")

        # 显示关键配置摘要
        print("\n配置摘要:")
        print(f"  摄像头地址: {os.getenv('CAMERA_URL', '未设置')}")
        print(f"  Ollama API: {os.getenv('OLLAMA_API', '未设置')}")
        print(f"  模型名称: {os.getenv('MODEL_NAME', '未设置')}")
        print(f"  QQ 模式: {os.getenv('QQ_BOT_TYPE', 'official')}")

        tts_enabled = os.getenv('TTS_ENABLE', 'true').lower() in ('true', '1', 'yes')
        print(f"  TTS 启用: {'是' if tts_enabled else '否'}")

        if warnings:
            print("\n注意: 有警告信息，请检查是否需要处理")
        else:
            print("\n所有配置检查完成，可以启动系统。")

        sys.exit(0)

if __name__ == '__main__':
    main()