#!/usr/bin/env python3
"""
测试火山引擎播客 TTS 新实现
用于验证 WebSocket 协议是否正常工作
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.tts_providers.volcengine_provider import VolcengineTTSProvider


def test_volcengine_tts():
    """测试火山引擎 TTS 基础功能"""

    print("=" * 60)
    print("测试火山引擎播客 TTS API (WebSocket)")
    print("=" * 60)

    appid = os.getenv("VOLCENGINE_APPID")
    token = os.getenv("VOLCENGINE_TOKEN")

    if not appid or not token:
        print("\n❌ 错误: 请设置环境变量")
        print("  export VOLCENGINE_APPID='your-appid'")
        print("  export VOLCENGINE_TOKEN='your-access-token'")
        return False

    print(f"\n✅ AppID: {appid[:8]}...")
    print(f"✅ Token: {token[:8]}...")

    config = {
        "appid": appid,
        "api_key": token,
        "voice": "zh_female_xiaoxiao",
        "speed": 1.0,
        "encoding": "mp3",
    }

    try:
        print("\n📡 初始化 Provider...")
        provider = VolcengineTTSProvider(config)
        print(f"✅ Provider 名称: {provider.get_provider_name()}")

        test_text = "你好，这是一个测试。火山引擎播客 TTS API 正在工作。"
        output_path = "test_output.mp3"

        print(f"\n🎙️ 测试文本: {test_text}")
        print(f"📁 输出路径: {output_path}")
        print("\n⏳ 开始合成（这可能需要几秒钟）...")

        result = provider.synthesize(test_text, output_path)

        if result["success"]:
            print("\n✅ 合成成功!")
            print(f"  文件: {result['file_path']}")
            print(f"  时长: {result.get('duration', 0):.2f} 秒")
            print(f"  大小: {result.get('size', 0)} 字节")
            print(f"  格式: {result.get('format', 'unknown')}")

            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"\n✅ 文件验证: {output_path} ({file_size} 字节)")
                return True
            else:
                print(f"\n❌ 错误: 文件未创建")
                return False
        else:
            print(f"\n❌ 合成失败: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"\n❌ 异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_volcengine_tts()
    sys.exit(0 if success else 1)
