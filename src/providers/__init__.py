"""
Provider 工厂类
用于创建和管理不同的 LLM Provider
"""

from typing import Dict, Any, Optional
from .base_provider import BaseProvider


class ProviderFactory:
    """
    Provider 工厂
    
    根据配置自动创建对应的 Provider 实例
    """
    
    # 注册的 Provider 类
    _providers: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str, provider_class):
        """
        注册一个新的 Provider
        
        Args:
            name: Provider 名称标识
            provider_class: Provider 类（必须继承 BaseProvider）
        """
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> BaseProvider:
        """
        创建 Provider 实例
        
        Args:
            provider_name: Provider 名称（如 'nvidia', 'openai'）
            config: Provider 配置
            
        Returns:
            BaseProvider: Provider 实例
            
        Raises:
            ValueError: 如果 Provider 未注册
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的 Provider 名称
        
        Returns:
            list: Provider 名称列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def auto_register(cls):
        """
        自动注册内置的 Provider
        
        在导入时自动调用，注册所有内置 Provider
        """
        # 避免重复注册
        if cls._providers:
            return
        
        try:
            from .nvidia_provider import NvidiaProvider
            cls.register('nvidia', NvidiaProvider)
        except ImportError as e:
            print(f"Warning: Failed to register NVIDIA provider: {e}")
        
        try:
            from .openai_provider import OpenAIProvider
            cls.register('openai', OpenAIProvider)
        except ImportError as e:
            print(f"Warning: Failed to register OpenAI provider: {e}")


# 自动注册内置 Provider
ProviderFactory.auto_register()


def create_provider(config: Dict[str, Any]) -> BaseProvider:
    """
    便捷函数：根据配置创建 Provider
    
    Args:
        config: 配置字典，必须包含 'provider' 字段
        
    Returns:
        BaseProvider: Provider 实例
        
    Example:
        config = {
            'provider': 'nvidia',
            'api_key': 'your-api-key',
            'model': 'deepseek-ai/deepseek-v3.2'
        }
        provider = create_provider(config)
    """
    provider_name = config.get('provider', 'openai')
    return ProviderFactory.create(provider_name, config)
