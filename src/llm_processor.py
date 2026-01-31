"""
LLM 内容处理模块
使用 Provider 架构支持多种 LLM API

设计原则：
- 依赖注入：通过构造函数注入配置和 Provider
- 不可变配置：初始化后不修改配置
- 清晰的错误分类
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .providers import create_provider, ProviderFactory
from .prompt_manager import PromptManager, get_prompt_manager
from .model_health_checker import get_health_checker


class LLMResult(TypedDict):  # type: ignore[misc]
    """LLM 处理结果类型"""
    success: bool
    script: str
    tokens_used: int
    error: str


@dataclass
class ProviderInfo:
    """Provider 信息"""
    name: str
    model: str
    available_models: List[str]


class LLMError(Exception):
    """LLM 处理错误"""
    pass


class LLMProcessor:
    """
    LLM 处理器
    
    职责：
    - 管理 LLM Provider 生命周期
    - 处理文章内容生成播客脚本
    - 格式化 Prompt
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        prompt_manager: Optional[PromptManager] = None
    ) -> None:
        """
        初始化 LLM 处理器
        
        Args:
            config: 配置字典
            prompt_manager: Prompt 管理器实例
            
        Raises:
            ValueError: 配置无效
        """
        self._config: Dict[str, Any] = config.copy()
        self._prompt_manager = prompt_manager
        
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
        """初始化 LLM Provider，带健康检查"""
        from logger import get_logger
        logger = get_logger("llm_processor")
        
        # 健康检查并自动切换
        health_checker = get_health_checker()
        final_config, switched, error = health_checker.check_and_switch("llm", self._config)
        
        if error:
            raise LLMError(f"No healthy LLM provider available: {error}")
        
        if switched:
            original = self._config.get('provider')
            new_provider = final_config.get('provider')
            logger.warning(
                f"Switched LLM provider from {original} to {new_provider} due to health check"
            )
            self._config = final_config
        
        provider_name = self._config.get('provider', 'openai')
        
        try:
            self._provider = create_provider(self._config)
        except ValueError as e:
            raise LLMError(
                f"Failed to initialize LLM provider '{provider_name}': {e}"
            ) from e
    
    def process(self, title: str, content: str) -> LLMResult:
        """
        处理文章内容，生成播客脚本
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            LLMResult: 处理结果
        """
        try:
            # 加载 Prompt
            system_prompt = self._load_system_prompt()
            user_prompt = self._build_user_prompt(title, content)
            
            # 调用 LLM
            messages = self._provider.format_messages(system_prompt, user_prompt)
            result = self._provider.chat_completion(messages)
            
            if result['success']:
                return LLMResult(
                    success=True,
                    script=result['content'],
                    tokens_used=result.get('tokens_used', 0),
                    error=""
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                return LLMResult(
                    success=False,
                    script="",
                    tokens_used=0,
                    error=error_msg
                )
                
        except Exception as e:
            return LLMResult(
                success=False,
                script="",
                tokens_used=0,
                error=f"LLM processing error: {str(e)}"
            )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        manager = self._prompt_manager or get_prompt_manager()
        prompt_type = self._config.get('prompt_type', 'default_host')
        return manager.get_system_prompt(prompt_type)
    
    def _build_user_prompt(self, title: str, content: str) -> str:
        """构建用户提示"""
        manager = self._prompt_manager or get_prompt_manager()
        template_type = self._config.get('prompt_template', 'article_to_podcast')
        return manager.format_user_prompt(
            template_type,
            title=title,
            content=content
        )
    
    @property
    def provider_info(self) -> ProviderInfo:
        """获取当前 Provider 信息"""
        return ProviderInfo(
            name=self._provider.get_provider_name(),
            model=self._provider.model or "",
            available_models=self._provider.get_model_list()
        )
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置副本（只读）"""
        return self._config.copy()


def get_available_providers() -> List[str]:
    """
    获取所有可用的 LLM Provider 列表
    
    Returns:
        Provider 名称列表
    """
    return ProviderFactory.get_available_providers()
