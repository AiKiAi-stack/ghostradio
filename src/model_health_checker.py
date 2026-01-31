"""
模型健康检查模块
自动检测模型可用性，故障时自动切换
"""

import time
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from logger import get_logger

logger = get_logger("health_check")


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # 可用但性能下降
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    provider: str
    status: HealthStatus
    response_time_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ModelHealthChecker:
    """
    模型健康检查器
    
    职责：
    - 检测 LLM 和 TTS 模型可用性
    - 自动切换到健康模型
    - 记录健康状态历史
    """
    
    # 超时配置（秒）
    TIMEOUT = 10
    
    # 备选模型配置
    FALLBACK_MODELS = {
        "llm": ["nvidia", "openai"],
        "tts": ["volcengine", "openai", "edge-tts"]
    }
    
    def __init__(self):
        self._health_cache: Dict[str, HealthCheckResult] = {}
        self._cache_time: float = 0
        self._cache_ttl = 60  # 缓存 60 秒
    
    def check_llm_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """
        检查 LLM 模型健康状态
        
        Args:
            config: LLM 配置
            
        Returns:
            HealthCheckResult: 健康检查结果
        """
        provider = config.get("provider", "openai")
        start_time = time.time()
        
        try:
            if provider == "nvidia":
                return self._check_nvidia_llm(config, start_time)
            elif provider == "openai":
                return self._check_openai_llm(config, start_time)
            else:
                return HealthCheckResult(
                    provider=provider,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error=f"Unknown provider: {provider}"
                )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"LLM health check failed for {provider}", error=e)
            return HealthCheckResult(
                provider=provider,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed,
                error=str(e)
            )
    
    def check_tts_health(self, config: Dict[str, Any]) -> HealthCheckResult:
        """
        检查 TTS 模型健康状态
        
        Args:
            config: TTS 配置
            
        Returns:
            HealthCheckResult: 健康检查结果
        """
        provider = config.get("provider", "edge-tts")
        start_time = time.time()
        
        try:
            if provider == "volcengine":
                return self._check_volcengine_tts(config, start_time)
            elif provider == "openai":
                return self._check_openai_tts(config, start_time)
            elif provider == "edge-tts":
                return self._check_edge_tts(config, start_time)
            else:
                return HealthCheckResult(
                    provider=provider,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error=f"Unknown provider: {provider}"
                )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"TTS health check failed for {provider}", error=e)
            return HealthCheckResult(
                provider=provider,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed,
                error=str(e)
            )
    
    def _check_nvidia_llm(self, config: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """检查 NVIDIA LLM"""
        import requests
        
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env", "NVIDIA_API_KEY"))
        if not api_key:
            return HealthCheckResult(
                provider="nvidia",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error="API key not found"
            )
        
        base_url = config.get("base_url", "https://integrate.api.nvidia.com/v1")
        model = config.get("model_name", "deepseek-ai/deepseek-v3.2")
        
        # 发送简单测试请求
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=self.TIMEOUT
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            return HealthCheckResult(
                provider="nvidia",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed,
                details={"model": model}
            )
        else:
            return HealthCheckResult(
                provider="nvidia",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
    
    def _check_openai_llm(self, config: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """检查 OpenAI LLM"""
        import requests
        
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        if not api_key:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error="API key not found"
            )
        
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model_name", "gpt-3.5-turbo")
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=self.TIMEOUT
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed,
                details={"model": model}
            )
        else:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed,
                error=f"HTTP {response.status_code}: {response.text[:200]}"
            )
    
    def _check_volcengine_tts(self, config: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """检查火山引擎 TTS"""
        import requests
        
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env", "VOLCENGINE_TOKEN"))
        appid = config.get("appid") or os.environ.get(config.get("appid_env", "VOLCENGINE_APPID"))
        
        if not api_key or not appid:
            return HealthCheckResult(
                provider="volcengine",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error="API key or AppID not found"
            )
        
        # 火山引擎使用简单的认证检查
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers={
                "Authorization": f"Bearer;{api_key}",
                "Content-Type": "application/json"
            },
            json={
                "app": {"appid": appid, "token": api_key, "cluster": "volcano_tts"},
                "user": {"uid": "health-check"},
                "audio": {"voice_type": "zh_female_xiaoxiao", "encoding": "mp3"},
                "request": {"reqid": "health-check", "text": "测试", "text_type": "plain", "operation": "sync"}
            },
            timeout=self.TIMEOUT
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        # 火山引擎即使返回错误也可能是正常的（比如文本太短）
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0 or "text" in str(data.get("message", "")).lower():
                return HealthCheckResult(
                    provider="volcengine",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed
                )
        
        return HealthCheckResult(
            provider="volcengine",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=elapsed,
            error=f"HTTP {response.status_code}: {response.text[:200]}"
        )
    
    def _check_openai_tts(self, config: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """检查 OpenAI TTS"""
        import requests
        
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        if not api_key:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error="API key not found"
            )
        
        # OpenAI TTS 没有健康检查端点，检查 API key 是否有效
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.TIMEOUT
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed
            )
        else:
            return HealthCheckResult(
                provider="openai",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed,
                error=f"HTTP {response.status_code}"
            )
    
    def _check_edge_tts(self, config: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """检查 Edge TTS（免费，通常总是可用）"""
        elapsed = (time.time() - start_time) * 1000
        
        # Edge TTS 是免费的，基于微软 Edge 浏览器服务
        # 通常总是可用，除非网络问题
        try:
            import urllib.request
            # 简单检查微软服务是否可达
            urllib.request.urlopen(
                "https://speech.platform.bing.com/",
                timeout=self.TIMEOUT
            )
            return HealthCheckResult(
                provider="edge-tts",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed
            )
        except:
            # 即使检查失败，Edge TTS 通常也能工作
            return HealthCheckResult(
                provider="edge-tts",
                status=HealthStatus.HEALTHY,  # 假设可用
                response_time_ms=elapsed,
                details={"note": "Health check endpoint not available, assuming healthy"}
            )
    
    def get_fallback_config(
        self,
        model_type: str,
        original_config: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        获取备选模型配置
        
        Args:
            model_type: "llm" 或 "tts"
            original_config: 原始配置
            
        Returns:
            (备选配置, 错误信息) - 如果都不可用返回 (None, error)
        """
        original_provider = original_config.get("provider")
        fallback_providers = self.FALLBACK_MODELS.get(model_type, [])
        
        # 排除原始 provider
        candidates = [p for p in fallback_providers if p != original_provider]
        
        logger.info(f"Looking for fallback {model_type} providers", context={
            "original": original_provider,
            "candidates": candidates
        })
        
        for provider in candidates:
            # 创建测试配置
            test_config = original_config.copy()
            test_config["provider"] = provider
            
            # 检查该 provider 是否可用
            if model_type == "llm":
                result = self.check_llm_health(test_config)
            else:
                result = self.check_tts_health(test_config)
            
            if result.status == HealthStatus.HEALTHY:
                logger.info(f"Found healthy fallback {model_type} provider: {provider}", context={
                    "response_time_ms": result.response_time_ms
                })
                return test_config, None
            else:
                logger.warning(f"Fallback {model_type} provider {provider} is unhealthy", context={
                    "error": result.error
                })
        
        error_msg = f"No healthy fallback {model_type} provider available"
        logger.error(error_msg)
        return None, error_msg
    
    def check_and_switch(
        self,
        model_type: str,
        config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool, Optional[str]]:
        """
        检查模型健康，如不健康则切换到备选
        
        Args:
            model_type: "llm" 或 "tts"
            config: 当前配置
            
        Returns:
            (最终配置, 是否切换了模型, 错误信息)
        """
        # 检查当前模型
        if model_type == "llm":
            result = self.check_llm_health(config)
        else:
            result = self.check_tts_health(config)
        
        if result.status == HealthStatus.HEALTHY:
            logger.info(f"{model_type} provider {result.provider} is healthy", context={
                "response_time_ms": result.response_time_ms
            })
            return config, False, None
        
        # 当前模型不健康，尝试切换
        logger.warning(
            f"{model_type} provider {result.provider} is unhealthy, attempting fallback",
            context={"error": result.error}
        )
        
        fallback_config, error = self.get_fallback_config(model_type, config)
        
        if fallback_config:
            logger.info(f"Switched {model_type} to fallback provider: {fallback_config.get('provider')}")
            return fallback_config, True, None
        else:
            return config, False, error


# 全局健康检查器
_health_checker: Optional[ModelHealthChecker] = None


def get_health_checker() -> ModelHealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ModelHealthChecker()
    return _health_checker
