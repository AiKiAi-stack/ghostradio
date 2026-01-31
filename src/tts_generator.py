"""
TTS 音频生成模块
使用 Provider 架构支持多种 TTS 服务
"""

import os
from typing import Dict, Any, Optional

# 导入 TTS Provider 系统
from .tts_providers import create_tts_provider, TTSProviderFactory


class TTSGenerator:
    """
    TTS 生成器
    
    支持多种 Provider：
    - volcengine: 火山引擎（豆包语音）
    - openai: OpenAI TTS
    - edge-tts: 微软 Edge TTS（免费）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 TTS 生成器
        
        Args:
            config: 配置字典，包含：
                - provider: Provider 名称
                - api_key: API 密钥
                - voice: 音色
                - speed: 语速
                - volume: 音量
                - pitch: 音调
        """
        self.config = config
        
        # 从环境变量获取 API key（如果配置了）
        api_key_env = config.get('api_key_env')
        if api_key_env and not config.get('api_key'):
            config['api_key'] = os.environ.get(api_key_env)
        
        # 创建 Provider
        try:
            self.provider = create_tts_provider(config)
        except ValueError as e:
            print(f"Warning: {e}, falling back to 'edge-tts' provider")
            config['provider'] = 'edge-tts'
            self.provider = create_tts_provider(config)
    
    def generate(self, text: str, output_path: str) -> dict:
        """
        生成音频文件
        
        Args:
            text: 要转换为语音的文本
            output_path: 输出文件路径
            
        Returns:
            dict: {
                'success': bool,
                'file_path': str,
                'duration': float,
                'error': str (if failed)
            }
        """
        try:
            # 使用 Provider 合成语音
            result = self.provider.synthesize(text, output_path)
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'TTS generation error: {str(e)}'
            }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取当前 Provider 信息
        
        Returns:
            dict: Provider 信息
        """
        return {
            'name': self.provider.get_provider_name(),
            'voice': self.provider.voice,
            'available_voices': self.provider.get_voice_list()
        }


# 向后兼容的便捷函数
def get_available_tts_providers() -> list:
    """
    获取所有可用的 TTS Provider 列表
    
    Returns:
        list: Provider 名称列表
    """
    return TTSProviderFactory.get_available_providers()
