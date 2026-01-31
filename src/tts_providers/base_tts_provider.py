"""
TTS Provider 抽象基类
定义所有 TTS Provider 的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class TTSProvider(ABC):
    """
    TTS Provider 抽象基类
    
    所有具体的 TTS Provider 实现都需要继承此类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 TTS Provider
        
        Args:
            config: Provider 配置字典
        """
        self.config = config
        self.api_key = config.get('api_key')
        self.voice = config.get('voice', 'default')
        self.speed = config.get('speed', 1.0)
        self.volume = config.get('volume', 1.0)
        self.pitch = config.get('pitch', 1.0)
        
        # 验证配置
        self.validate_config()
    
    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            **kwargs: 额外的参数
            
        Returns:
            Dict: 包含 success, file_path, duration, error 等字段
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置是否完整
        
        Returns:
            bool: 配置是否有效
        """
        pass
    
    def get_voice_list(self) -> list:
        """
        获取可用的音色列表
        
        Returns:
            list: 音色列表
        """
        return []
    
    def split_text(self, text: str, max_length: int = 1000) -> list:
        """
        将长文本分割成多个小段
        
        Args:
            text: 原始文本
            max_length: 每段最大长度
            
        Returns:
            list: 文本段列表
        """
        if len(text) <= max_length:
            return [text]
        
        # 按句子分割
        import re
        sentences = re.split(r'([。！？.!?]+)', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text[:max_length]]
    
    def estimate_duration(self, text: str) -> float:
        """
        估算语音时长（秒）
        
        Args:
            text: 文本内容
            
        Returns:
            float: 估算的时长（秒）
        """
        # 粗略估算：中文约 5 字/秒
        char_count = len(text)
        duration = char_count / 5
        
        # 根据语速调整
        if self.speed > 0:
            duration = duration / self.speed
        
        return duration
    
    def get_provider_name(self) -> str:
        """获取 Provider 名称"""
        return self.__class__.__name__.replace('Provider', '').lower()
