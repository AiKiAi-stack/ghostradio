"""
LLM 内容处理模块
使用 Provider 架构支持多种 LLM API
"""

import os
from typing import Dict, Any, Optional

# 导入 Provider 系统
from .providers import create_provider, ProviderFactory
from .prompt_manager import get_prompt_manager


class LLMProcessor:
    """
    LLM 处理器 - 将文章内容转换为播客脚本
    
    支持多种 Provider：
    - nvidia: NVIDIA API
    - openai: OpenAI 及兼容 API（DeepSeek、Azure 等）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 处理器
        
        Args:
            config: 配置字典，包含：
                - provider: Provider 名称（nvidia/openai）
                - api_key: API 密钥
                - model: 模型名称
                - temperature: 温度参数
                - max_tokens: 最大 token 数
                - prompt_file: 系统提示词文件路径
        """
        self.config = config
        
        # 从环境变量获取 API key（如果配置了）
        api_key_env = config.get('api_key_env')
        if api_key_env and not config.get('api_key'):
            config['api_key'] = os.environ.get(api_key_env)
        
        # 创建 Provider
        try:
            self.provider = create_provider(config)
        except ValueError as e:
            # 如果指定的 provider 不存在，回退到 openai
            print(f"Warning: {e}, falling back to 'openai' provider")
            config['provider'] = 'openai'
            self.provider = create_provider(config)
    
    def process(self, title: str, content: str) -> dict:
        """
        处理文章内容，生成播客脚本
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            dict: {
                'success': bool,
                'script': str,
                'tokens_used': int,
                'error': str (if failed)
            }
        """
        try:
            # 加载系统提示词
            system_prompt = self._load_system_prompt()
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(title, content)
            
            # 格式化消息
            messages = self.provider.format_messages(system_prompt, user_prompt)
            
            # 调用 LLM
            result = self.provider.chat_completion(messages)
            
            if result['success']:
                return {
                    'success': True,
                    'script': result['content'],
                    'tokens_used': result.get('tokens_used', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM processing error: {str(e)}'
            }
    
    def _load_system_prompt(self) -> str:
        """
        加载系统提示词
        
        Returns:
            str: 系统提示词内容
        """
        # 使用 PromptManager 从配置文件加载
        prompt_manager = get_prompt_manager()
        
        # 获取 prompt 类型，默认为 default_host
        prompt_type = self.config.get('prompt_type', 'default_host')
        
        return prompt_manager.get_system_prompt(prompt_type)
    
    def _build_user_prompt(self, title: str, content: str) -> str:
        """
        构建用户提示
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            str: 用户提示词
        """
        # 使用 PromptManager 从配置文件加载模板
        prompt_manager = get_prompt_manager()
        
        # 获取模板类型，默认为 article_to_podcast
        template_type = self.config.get('prompt_template', 'article_to_podcast')
        
        return prompt_manager.format_user_prompt(
            template_type,
            title=title,
            content=content
        )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取当前 Provider 信息
        
        Returns:
            dict: Provider 信息
        """
        return {
            'name': self.provider.get_provider_name(),
            'model': self.provider.model,
            'available_models': self.provider.get_model_list()
        }


# 向后兼容的便捷函数
def get_available_providers() -> list:
    """
    获取所有可用的 Provider 列表
    
    Returns:
        list: Provider 名称列表
    """
    return ProviderFactory.get_available_providers()
