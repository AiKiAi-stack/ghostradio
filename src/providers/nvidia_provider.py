"""
NVIDIA Provider 实现
使用 NVIDIA API 进行 LLM 推理
"""

import requests
from typing import Dict, Any, List, Optional
from .base_provider import BaseProvider


class NvidiaProvider(BaseProvider):
    """
    NVIDIA LLM Provider
    
    使用 NVIDIA 的 API 服务，支持多种模型：
    - deepseek-ai/deepseek-v3.2
    - meta/llama-3.1-405b-instruct
    - 等
    
    API 文档: https://www.nvidia.com/en-us/ai/
    """
    
    # 默认 API 端点
    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
    
    # 常用模型列表
    AVAILABLE_MODELS = [
        "deepseek-ai/deepseek-v3.2",
        "deepseek-ai/deepseek-r1",
        "meta/llama-3.1-405b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
        "mistralai/mistral-large",
        "google/gemma-2-27b-it",
        "google/gemma-2-9b-it",
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 NVIDIA Provider
        
        Args:
            config: 配置字典，应包含：
                - api_key: NVIDIA API 密钥
                - model: 模型名称（默认为 deepseek-ai/deepseek-v3.2）
                - temperature: 温度参数（默认 0.7）
                - max_tokens: 最大 token 数（默认 4096）
                - top_p: 核采样参数（默认 0.95）
                - stream: 是否流式输出（默认 False）
        """
        # 设置默认值
        config.setdefault('base_url', self.DEFAULT_BASE_URL)
        config.setdefault('model', 'deepseek-ai/deepseek-v3.2')
        config.setdefault('temperature', 0.7)
        config.setdefault('max_tokens', 4096)
        config.setdefault('top_p', 0.95)
        config.setdefault('stream', False)
        
        super().__init__(config)
        
        self.base_url = self.config.get('base_url', self.DEFAULT_BASE_URL)
        self.top_p = self.config.get('top_p', 0.95)
        self.stream = self.config.get('stream', False)
    
    def validate_config(self) -> bool:
        """
        验证 NVIDIA 配置
        
        Returns:
            bool: 配置有效
            
        Raises:
            ValueError: 配置无效
        """
        if not self.api_key:
            raise ValueError("NVIDIA API key is required. Set it in config['api_key'] or NVIDIA_API_KEY environment variable.")
        
        if not self.model:
            raise ValueError("Model name is required. Set it in config['model'].")
        
        # 验证模型是否在可用列表中（警告但不阻止）
        if self.model not in self.AVAILABLE_MODELS:
            print(f"Warning: Model '{self.model}' is not in the known models list. "
                  f"Available models: {', '.join(self.AVAILABLE_MODELS[:5])}...")
        
        return True
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天完成请求到 NVIDIA API
        
        Args:
            messages: 消息列表
            **kwargs: 额外的请求参数，可覆盖默认配置
            
        Returns:
            Dict: 包含 success, content, tokens_used, error 等字段
        """
        try:
            # 构建请求 URL
            url = f"{self.base_url}/chat/completions"
            
            # 构建请求体
            payload = {
                "model": kwargs.get('model', self.model),
                "messages": messages,
                "temperature": kwargs.get('temperature', self.temperature),
                "top_p": kwargs.get('top_p', self.top_p),
                "max_tokens": kwargs.get('max_tokens', self.max_tokens),
                "stream": kwargs.get('stream', self.stream),
            }
            
            # 添加可选参数
            if 'seed' in kwargs:
                payload['seed'] = kwargs['seed']
            
            # 构建请求头
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 发送请求
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # 提取生成的内容
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0].get('message', {}).get('content', '')
            else:
                return {
                    'success': False,
                    'error': 'No completion found in response',
                    'raw_response': data
                }
            
            # 提取 token 使用情况
            tokens_used = 0
            if 'usage' in data:
                tokens_used = data['usage'].get('total_tokens', 0)
            
            return {
                'success': True,
                'content': content,
                'tokens_used': tokens_used,
                'raw_response': data
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f'Request timeout after {self.timeout} seconds'
            }
        except requests.exceptions.HTTPError as e:
            error_msg = f'HTTP error: {e.response.status_code}'
            try:
                error_data = e.response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error']}"
            except:
                pass
            return {
                'success': False,
                'error': error_msg,
                'status_code': e.response.status_code
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_model_list(self) -> List[str]:
        """
        获取 NVIDIA 支持的模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        return self.AVAILABLE_MODELS.copy()
    
    def count_tokens(self, text: str) -> int:
        """
        估算 NVIDIA 模型的 token 数量
        
        对于 DeepSeek 和 Llama 模型，使用更准确的估算
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的 token 数量
        """
        # 对于中文文本，DeepSeek 和 Llama 模型通常使用 BPE tokenizer
        # 粗略估算：每个汉字约 1-2 tokens，英文单词约 1.3 tokens
        
        import re
        
        # 分离中英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        other_chars = len(text) - chinese_chars - english_words
        
        # 估算：中文 1.5 tokens/字，英文 1.3 tokens/词，其他 0.5 tokens/字符
        estimated_tokens = int(chinese_chars * 1.5 + english_words * 1.3 + other_chars * 0.5)
        
        return max(1, estimated_tokens)
    
    def get_provider_name(self) -> str:
        """获取 Provider 名称"""
        return "nvidia"
