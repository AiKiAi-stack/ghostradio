"""
TTS Provider 工厂类
用于创建和管理不同的 TTS Provider
"""

from typing import Dict, Any
from .base_tts_provider import TTSProvider


class TTSProviderFactory:
    """TTS Provider 工厂"""
    
    _providers: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str, provider_class):
        """注册 Provider"""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> TTSProvider:
        """创建 Provider 实例"""
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown TTS provider: '{provider_name}'. "
                f"Available: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """获取所有可用的 Provider 名称"""
        return list(cls._providers.keys())
    
    @classmethod
    def auto_register(cls):
        """自动注册内置 Provider"""
        if cls._providers:
            return
        
        try:
            from .volcengine_provider import VolcengineTTSProvider
            cls.register('volcengine', VolcengineTTSProvider)
        except ImportError as e:
            print(f"Warning: Failed to register Volcengine provider: {e}")
        
        try:
            from .openai_tts_provider import OpenAITTSProvider
            cls.register('openai', OpenAITTSProvider)
        except ImportError as e:
            print(f"Warning: Failed to register OpenAI TTS provider: {e}")
        
        try:
            from .edge_tts_provider import EdgeTTSProvider
            cls.register('edge-tts', EdgeTTSProvider)
        except ImportError as e:
            print(f"Warning: Failed to register Edge TTS provider: {e}")


# 自动注册
TTSProviderFactory.auto_register()


def create_tts_provider(config: Dict[str, Any]) -> TTSProvider:
    """便捷函数：创建 TTS Provider"""
    provider_name = config.get('provider', 'edge-tts')
    return TTSProviderFactory.create(provider_name, config)
