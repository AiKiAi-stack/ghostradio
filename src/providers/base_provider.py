"""
Base Provider 抽象基类
定义所有 LLM Provider 的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseProvider(ABC):
    """
    LLM Provider 抽象基类
    
    所有具体的 Provider 实现都需要继承此类，并实现以下方法：
    - chat_completion: 发送聊天请求并获取回复
    - validate_config: 验证配置是否完整
    - get_model_list: 获取支持的模型列表（可选）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Provider
        
        Args:
            config: Provider 配置字典，包含：
                - api_key: API 密钥
                - base_url: API 基础 URL（可选）
                - model: 模型名称
                - temperature: 温度参数
                - max_tokens: 最大 token 数
                - timeout: 请求超时时间
        """
        self.config = config
        self.api_key = config.get('api_key')
        self.model = config.get('model')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 4096)
        self.timeout = config.get('timeout', 60)
        
        # 验证配置
        self.validate_config()
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            **kwargs: 额外的请求参数
            
        Returns:
            Dict: 包含以下字段：
                - success: bool - 是否成功
                - content: str - 生成的文本内容
                - tokens_used: int - 使用的 token 数量（可选）
                - error: str - 错误信息（如果失败）
                - raw_response: Any - 原始响应（可选，用于调试）
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置是否完整和有效
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出，包含具体错误信息
        """
        pass
    
    def get_model_list(self) -> List[str]:
        """
        获取该 Provider 支持的模型列表
        
        Returns:
            List[str]: 模型名称列表
            
        Note:
            这是一个可选方法，默认返回空列表。
            具体 Provider 可以重写此方法返回实际支持的模型。
        """
        return []
    
    def format_messages(
        self,
        system_prompt: Optional[str],
        user_prompt: str
    ) -> List[Dict[str, str]]:
        """
        格式化消息为 Provider 需要的格式
        
        Args:
            system_prompt: 系统提示词（可选）
            user_prompt: 用户提示词
            
        Returns:
            List[Dict[str, str]]: 格式化后的消息列表
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        return messages
    
    def count_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的 token 数量
            
        Note:
            这是一个粗略估算，不同模型的 token 计算方式不同。
            具体 Provider 可以重写此方法提供更准确的计算。
        """
        # 粗略估算：中文约 1.5 字符/token，英文约 4 字符/token
        # 这里使用保守估计
        return len(text) // 2
    
    def get_provider_name(self) -> str:
        """
        获取 Provider 名称
        
        Returns:
            str: Provider 的标识名称
        """
        return self.__class__.__name__.replace('Provider', '').lower()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(model={self.model})>"
