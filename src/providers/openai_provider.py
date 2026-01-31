"""
OpenAI Provider 实现
支持 OpenAI API 和兼容 OpenAI 格式的 API（如 DeepSeek、Azure 等）
"""

from typing import Dict, Any, List, Optional
from .base_provider import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    OpenAI 格式兼容 Provider
    
    支持：
    - OpenAI 官方 API
    - DeepSeek API（OpenAI 格式）
    - Azure OpenAI
    - 其他 OpenAI 格式兼容的 API
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 OpenAI Provider
        
        Args:
            config: 配置字典，应包含：
                - api_key: API 密钥
                - base_url: API 基础 URL（可选，用于第三方 API）
                - model: 模型名称
                - temperature: 温度参数
                - max_tokens: 最大 token 数
        """
        # 设置默认值
        config.setdefault('model', 'gpt-3.5-turbo')
        config.setdefault('temperature', 0.7)
        config.setdefault('max_tokens', 4096)
        
        super().__init__(config)
        
        self.base_url = config.get('base_url')  # 可选，用于第三方 API
        self._client = None
    
    def _get_client(self):
        """获取或创建 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                
                client_kwargs = {'api_key': self.api_key}
                if self.base_url:
                    client_kwargs['base_url'] = self.base_url
                
                self._client = OpenAI(**client_kwargs)
            except ImportError:
                raise ImportError(
                    "OpenAI package is required. Install it with: pip install openai"
                )
        
        return self._client
    
    def validate_config(self) -> bool:
        """
        验证 OpenAI 配置
        
        Returns:
            bool: 配置有效
            
        Raises:
            ValueError: 配置无效
        """
        if not self.api_key:
            raise ValueError(
                "API key is required. Set it in config['api_key'] or "
                f"{self.config.get('api_key_env', 'OPENAI_API_KEY')} environment variable."
            )
        
        if not self.model:
            raise ValueError("Model name is required. Set it in config['model'].")
        
        return True
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表
            **kwargs: 额外的请求参数
            
        Returns:
            Dict: 包含 success, content, tokens_used, error 等字段
        """
        try:
            client = self._get_client()
            
            # 构建请求参数
            request_params = {
                'model': kwargs.get('model', self.model),
                'messages': messages,
                'temperature': kwargs.get('temperature', self.temperature),
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            }
            
            # 添加可选参数
            if 'top_p' in kwargs:
                request_params['top_p'] = kwargs['top_p']
            if 'frequency_penalty' in kwargs:
                request_params['frequency_penalty'] = kwargs['frequency_penalty']
            if 'presence_penalty' in kwargs:
                request_params['presence_penalty'] = kwargs['presence_penalty']
            
            # 发送请求
            response = client.chat.completions.create(**request_params)
            
            # 提取生成的内容
            content = response.choices[0].message.content
            
            # 提取 token 使用情况
            tokens_used = 0
            if response.usage:
                tokens_used = response.usage.total_tokens
            
            return {
                'success': True,
                'content': content,
                'tokens_used': tokens_used,
                'raw_response': response
            }
            
        except ImportError as e:
            return {
                'success': False,
                'error': f'OpenAI package not installed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}'
            }
    
    def get_model_list(self) -> List[str]:
        """
        获取常用 OpenAI 模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        return [
            'gpt-4',
            'gpt-4-turbo',
            'gpt-4o',
            'gpt-4o-mini',
            'gpt-3.5-turbo',
            'deepseek-chat',
            'deepseek-coder',
        ]
    
    def get_provider_name(self) -> str:
        """获取 Provider 名称"""
        return "openai"
