"""
TTS 音频生成模块
使用 Provider 架构支持多种 TTS 服务

改进：
- 集成模型健康检查
- Provider 故障时自动切换
- 前端用户无感知
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from .tts_providers import create_tts_provider, TTSProviderFactory
from .model_health_checker import get_health_checker
from .logger import get_logger

logger = get_logger("tts_generator")


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
    - Provider 故障时自动切换（前端无感知）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化 TTS 生成器

        优先使用传入配置，否则从健康检查器获取当前可用 Provider 配置
        """
        if config and config.get("api_key"):
            self._config = config
            logger.info(f"Using provided TTS config: {self._config.get('provider')}")
        else:
            # 从健康检查器获取当前 Provider 配置
            health_checker = get_health_checker()
            try:
                self._config = health_checker.get_tts_config()
                logger.info(
                    f"Using TTS provider from health checker: {self._config.get('provider')}"
                )
            except RuntimeError as e:
                # 初始化时暂不报错，以允许某些极端情况
                self._config = config or {}
                logger.warning(f"No TTS providers available in health checker: {e}")

        # 延迟初始化 Provider
        self._provider = None

    def _init_provider(self) -> None:
        """初始化 TTS Provider"""
        if self._provider:
            return

        provider_name = self._config.get("provider", "edge-tts")

        try:
            self._provider = create_tts_provider(self._config)
        except ValueError as e:
            raise TTSError(
                f"Failed to initialize TTS provider '{provider_name}': {e}"
            ) from e

    def generate(self, text: str, output_path: str, **kwargs) -> TTSResult:
        """
        生成音频文件

        支持通过 kwargs 传递 Provider 特定参数
        如果当前 Provider 失败，自动切换到下一个可用 Provider 重试
        """
        # 确保 Provider 已初始化
        self._init_provider()

        max_retries = 3
        last_error = None
        current_provider = self.provider_info["name"]

        logger.info(
            f"Starting TTS generation",
            context={
                "provider": current_provider,
                "voice": kwargs.get("voice") or self.provider_info.get("voice"),
                "text_length": len(text),
                "output_path": output_path,
                "extra_params": list(kwargs.keys()),
            },
        )

        for attempt in range(max_retries):
            try:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                # 使用 Provider 合成语音
                result = self._provider.synthesize(text, output_path, **kwargs)

                logger.debug(
                    f"TTS synthesis result",
                    context={
                        "provider": current_provider,
                        "success": result.get("success"),
                        "attempt": attempt + 1,
                    },
                )

                if result["success"]:
                    logger.info(
                        f"TTS generation successful",
                        context={
                            "provider": current_provider,
                            "file_path": result.get("file_path"),
                            "duration": result.get("duration"),
                            "attempt": attempt + 1,
                        },
                    )
                    return TTSResult(
                        success=True,
                        file_path=result.get("file_path", ""),
                        duration=result.get("duration", 0.0),
                        error="",
                    )
                else:
                    # API 返回错误，可能是 Provider 问题
                    error_msg = result.get("error", "Unknown error")
                    logger.warning(
                        f"TTS API error",
                        context={
                            "provider": current_provider,
                            "attempt": attempt + 1,
                            "error": error_msg,
                            "raw_response": result,
                        },
                    )

                    # 尝试切换 Provider
                    if self._try_switch_provider():
                        current_provider = self.provider_info["name"]
                        logger.info(f"Switched to new TTS provider: {current_provider}")
                        continue  # 用新 Provider 重试
                    else:
                        logger.error(f"Failed to switch TTS provider, giving up")
                        return TTSResult(
                            success=False, file_path="", duration=0.0, error=error_msg
                        )

            except Exception as e:
                last_error = e
                logger.error(
                    f"TTS generation exception",
                    context={
                        "provider": current_provider,
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                    error=e,
                )

                # 尝试切换 Provider
                if self._try_switch_provider():
                    current_provider = self.provider_info["name"]
                    logger.info(
                        f"Switched to new TTS provider after exception: {current_provider}"
                    )
                    continue  # 用新 Provider 重试
                else:
                    logger.error(f"No more TTS providers available")
                    break  # 没有可用 Provider 了

        # 所有尝试都失败
        logger.error(
            f"TTS generation failed after all retries",
            context={
                "attempts": max_retries,
                "final_provider": current_provider,
                "last_error": str(last_error),
            },
        )
        return TTSResult(
            success=False,
            file_path="",
            duration=0.0,
            error=f"Failed after {max_retries} attempts: {str(last_error)}",
        )

    def _try_switch_provider(self) -> bool:
        """
        尝试切换到下一个可用 Provider

        Returns:
            是否成功切换
        """
        try:
            health_checker = get_health_checker()
            new_config = health_checker.report_tts_failure()

            # 更新配置并重新初始化 provider
            self._config = new_config
            self._init_provider()

            logger.info(f"Switched to TTS provider: {new_config.get('provider')}")
            return True

        except RuntimeError as e:
            logger.error(f"Failed to switch TTS provider: {e}")
            return False

    @property
    def provider_info(self) -> Dict[str, Any]:
        """获取当前 Provider 信息"""
        return {
            "name": self._provider.get_provider_name(),
            "voice": self._config.get("voice", ""),
            "available_voices": self._provider.get_voice_list(),
        }

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置副本（只读）"""
        return self._config.copy()


def get_available_tts_providers() -> List[str]:
    """获取所有可用的 TTS Provider 列表"""
    return TTSProviderFactory.get_available_providers()
