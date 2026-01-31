"""
TTS 音频生成模块
使用 Provider 架构支持多种 TTS 服务

设计原则：
- 依赖注入
- 不可变配置
- 清晰的错误分类
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from .tts_providers import create_tts_provider, TTSProviderFactory


class TTSResult(TypedDict):  # type: ignore[misc]
    """TTS 生成结果类型"""
    success: bool
    file_path: str
    duration: float
    error: str


@dataclass
class TTSVoiceInfo:
    """TTS 音色信息"""
    id: str
    name: str


class TTSError(Exception):
    """TTS 处理错误"""
    pass


class TTSGenerator:
    """
    TTS 生成器
    
    职责：
    - 管理 TTS Provider 生命周期
    - 生成语音文件
    - 返回处理结果
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        初始化 TTS 生成器
        
        Args:
            config: 配置字典，包含 provider, api_key, voice, speed 等
            
        Raises:
            TTSError: Provider 初始化失败
        """
        self._config: Dict[str, Any] = config.copy()
        
        # 解析 API Key
        self._resolve_api_key()
        
        # 初始化 Provider
        self._init_provider()
    
    def _resolve_api_key(self) -> None:
        """从环境变量解析 API Key"""
        api_key_env = self._config.get('api_key_env')
        if api_key_env and not self._config.get('api_key'):
            api_key = os.environ.get(api_key_env)
            if api_key:
                self._config['api_key'] = api_key
    
    def _init_provider(self) -> None:
        """初始化 TTS Provider"""
        provider_name = self._config.get('provider', 'edge-tts')
        
        try:
            self._provider = create_tts_provider(self._config)
        except ValueError as e:
            raise TTSError(
                f"Failed to initialize TTS provider '{provider_name}': {e}"
            ) from e
    
    def generate(self, text: str, output_path: str) -> TTSResult:
        """
        生成音频文件
        
        Args:
            text: 要转换为语音的文本
            output_path: 输出文件路径
            
        Returns:
            TTSResult: 生成结果
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 使用 Provider 合成语音
            result = self._provider.synthesize(text, output_path)
            
            return TTSResult(
                success=result['success'],
                file_path=result.get('file_path', ''),
                duration=result.get('duration', 0.0),
                error=result.get('error', '')
            )
            
        except Exception as e:
            return TTSResult(
                success=False,
                file_path="",
                duration=0.0,
                error=f"TTS generation error: {str(e)}"
            )
    
    @property
    def provider_info(self) -> Dict[str, Any]:
        """获取当前 Provider 信息"""
        return {
            'name': self._provider.get_provider_name(),
            'voice': self._provider.voice,
            'available_voices': self._provider.get_voice_list()
        }
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置副本（只读）"""
        return self._config.copy()


def get_available_tts_providers() -> List[str]:
    """
    获取所有可用的 TTS Provider 列表
    
    Returns:
        Provider 名称列表
    """
    return TTSProviderFactory.get_available_providers()
