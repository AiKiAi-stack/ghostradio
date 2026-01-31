"""
Edge TTS Provider 实现
使用微软 Edge 浏览器的免费 TTS 服务
"""

import os
import asyncio
from typing import Dict, Any
from .base_tts_provider import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """
    Edge TTS Provider (免费)
    
    使用微软 Edge 浏览器的在线 TTS 服务，无需 API key
    """
    
    # 常用中文音色
    AVAILABLE_VOICES = [
        'zh-CN-XiaoxiaoNeural',      # 晓晓 - 年轻女性
        'zh-CN-XiaoyiNeural',        # 小艺 - 年轻女性
        'zh-CN-YunjianNeural',       # 云健 - 男性
        'zh-CN-YunxiNeural',         # 云希 - 男性
        'zh-CN-YunxiaNeural',        # 云夏 - 男性
        'zh-CN-YunyangNeural',       # 云扬 - 男性
        'zh-CN-liaoning-XiaobeiNeural',  # 东北小贝
        'zh-CN-shaanxi-XiaoniNeural',    # 陕西小妮
    ]
    
    def __init__(self, config: Dict[str, Any]):
        config.setdefault('voice', 'zh-CN-XiaoxiaoNeural')
        config.setdefault('speed', 1.0)
        super().__init__(config)
    
    def validate_config(self) -> bool:
        # Edge TTS 不需要 API key
        return True
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        try:
            import edge_tts
            
            voice = kwargs.get('voice', self.voice)
            speed = kwargs.get('speed', self.speed)
            
            # 调整语速参数
            # Edge TTS 使用百分比: +0%, +50%, -50%
            if speed > 1.0:
                rate = f"+{int((speed - 1) * 100)}%"
            elif speed < 1.0:
                rate = f"{int((speed - 1) * 100)}%"
            else:
                rate = "+0%"
            
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(output_path)
            
            # 运行异步函数
            asyncio.run(_synthesize())
            
            # 估算时长
            duration = self.estimate_duration(text) / speed
            
            return {
                'success': True,
                'file_path': output_path,
                'duration': duration,
                'format': 'mp3'
            }
            
        except ImportError:
            return {
                'success': False,
                'error': 'edge-tts not installed. Run: pip install edge-tts'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_voice_list(self) -> list:
        return self.AVAILABLE_VOICES
    
    def get_provider_name(self) -> str:
        return "edge-tts"
