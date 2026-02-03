"""
LLM 内容处理模块
使用 Provider 架构支持多种 LLM API

改进：
- 集成模型健康检查
- 模型故障时自动切换
- 前端用户无感知
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from .providers import create_provider, ProviderFactory
from .prompt_manager import PromptManager, get_prompt_manager
from .model_health_checker import get_health_checker
from .logger import get_logger

logger = get_logger("llm_processor")


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
    - 模型故障时自动切换（前端无感知）
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        prompt_manager: Optional[PromptManager] = None,
    ) -> None:
        """
        初始化 LLM 处理器

        优先使用传入配置，否则从健康检查器获取当前可用模型配置
        """
        self._prompt_manager = prompt_manager

        if config and config.get("api_key"):
            self._config = config
            logger.info(
                f"Using provided LLM config: {self._config.get('model_name') or self._config.get('model')}"
            )
        else:
            # 从健康检查器获取当前模型配置
            health_checker = get_health_checker()
            try:
                self._config = health_checker.get_llm_config()
                logger.info(
                    f"Using LLM model from health checker: {self._config.get('model')}"
                )
            except RuntimeError as e:
                # 只有当确实需要 LLM（通过 process 方法调用）时才报错
                # 初始化时暂不报错，以允许只用 TTS 的场景
                self._config = config or {}
                logger.warning(f"No LLM models available in health checker: {e}")

        # 延迟初始化 Provider，只有在真正需要时才报错
        self._provider = None

    def _init_provider(self) -> None:
        """初始化 LLM Provider"""
        if self._provider:
            return

        if not self._config or not self._config.get("api_key"):
            raise LLMError("LLM provider config is missing or has no API key")

        provider_name = self._config.get("provider", "openai")

        try:
            self._provider = create_provider(self._config)
        except ValueError as e:
            raise LLMError(
                f"Failed to initialize LLM provider '{provider_name}': {e}"
            ) from e

    def process(self, title: str, content: str) -> LLMResult:
        """
        处理文章内容，生成播客脚本

        如果当前模型失败，自动切换到下一个可用模型重试
        """
        # 确保 Provider 已初始化
        self._init_provider()

        max_retries = 3
        last_error = None
        current_model = self.provider_info.model

        logger.info(
            f"Starting LLM processing",
            context={
                "title": title,
                "content_length": len(content),
                "model": current_model,
                "provider": self.provider_info.name,
            },
        )

        for attempt in range(max_retries):
            try:
                # 加载 Prompt
                system_prompt = self._load_system_prompt()
                user_prompt = self._build_user_prompt(title, content)

                logger.debug(
                    f"LLM prompt prepared",
                    context={
                        "model": current_model,
                        "system_prompt_preview": system_prompt[:100] + "...",
                        "user_prompt_preview": user_prompt[:200] + "...",
                        "user_prompt_length": len(user_prompt),
                    },
                )

                # 调用 LLM
                messages = self._provider.format_messages(system_prompt, user_prompt)
                result = self._provider.chat_completion(messages)

                logger.debug(
                    f"LLM response received",
                    context={
                        "model": current_model,
                        "success": result.get("success"),
                        "tokens_used": result.get("tokens_used", 0),
                        "content_preview": result.get("content", "")[:200] + "...",
                    },
                )

                if result["success"]:
                    logger.info(
                        f"LLM processing successful",
                        context={
                            "model": current_model,
                            "tokens_used": result.get("tokens_used", 0),
                            "script_length": len(result.get("content", "")),
                        },
                    )
                    return LLMResult(
                        success=True,
                        script=result["content"],
                        tokens_used=result.get("tokens_used", 0),
                        error="",
                    )
                else:
                    # API 返回错误，可能是模型问题
                    error_msg = result.get("error", "Unknown error")
                    logger.warning(
                        f"LLM API error",
                        context={
                            "model": current_model,
                            "attempt": attempt + 1,
                            "error": error_msg,
                            "raw_response": result,
                        },
                    )

                    # 尝试切换模型
                    if self._try_switch_model():
                        current_model = self.provider_info.model
                        logger.info(f"Switched to new model: {current_model}")
                        continue  # 用新模型重试
                    else:
                        logger.error(f"Failed to switch model, giving up")
                        return LLMResult(
                            success=False, script="", tokens_used=0, error=error_msg
                        )

            except Exception as e:
                last_error = e
                logger.error(
                    f"LLM processing exception",
                    context={
                        "model": current_model,
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                    error=e,
                )

                # 尝试切换模型
                if self._try_switch_model():
                    current_model = self.provider_info.model
                    logger.info(
                        f"Switched to new model after exception: {current_model}"
                    )
                    continue  # 用新模型重试
                else:
                    logger.error(f"No more models available")
                    break  # 没有可用模型了

        # 所有尝试都失败
        logger.error(
            f"LLM processing failed after all retries",
            context={
                "attempts": max_retries,
                "final_model": current_model,
                "last_error": str(last_error),
            },
        )
        return LLMResult(
            success=False,
            script="",
            tokens_used=0,
            error=f"Failed after {max_retries} attempts: {str(last_error)}",
        )

    def _try_switch_model(self) -> bool:
        """
        尝试切换到下一个可用模型

        Returns:
            是否成功切换
        """
        try:
            health_checker = get_health_checker()
            new_config = health_checker.report_llm_failure()

            # 更新配置并重新初始化 provider
            self._config = new_config
            self._init_provider()

            logger.info(f"Switched to model: {new_config.get('model')}")
            return True

        except RuntimeError as e:
            logger.error(f"Failed to switch LLM model: {e}")
            return False

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        manager = self._prompt_manager or get_prompt_manager()
        prompt_type = self._config.get("prompt_type", "default_host")
        return manager.get_system_prompt(prompt_type)

    def _build_user_prompt(self, title: str, content: str) -> str:
        """构建用户提示"""
        manager = self._prompt_manager or get_prompt_manager()
        template_type = self._config.get("prompt_template", "article_to_podcast")
        return manager.format_user_prompt(template_type, title=title, content=content)

    @property
    def provider_info(self) -> ProviderInfo:
        """获取当前 Provider 信息"""
        return ProviderInfo(
            name=self._provider.get_provider_name(),
            model=self._config.get("model", ""),
            available_models=self._provider.get_model_list(),
        )

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置副本（只读）"""
        return self._config.copy()


def get_available_providers() -> List[str]:
    """获取所有可用的 LLM Provider 列表"""
    return ProviderFactory.get_available_providers()
