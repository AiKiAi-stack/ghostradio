"""
模型健康检查模块 - 具体模型级别
服务启动时自检，记录可用模型，故障时自动切换
"""

import time
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from logger import get_logger

logger = get_logger("model_health")


class ModelHealthChecker:
    """
    模型健康检查器 - 具体模型级别
    
    设计：
    - 服务启动时自检所有模型
    - 缓存可用模型列表
    - 当前模型故障时自动切换到下一个可用模型
    - 前端用户无感知
    """
    
    # 模型配置（provider, model_name, api_key_env, base_url）
    LLM_MODELS = [
        {
            "provider": "nvidia",
            "model": "deepseek-ai/deepseek-v3.2",
            "api_key_env": "NVIDIA_API_KEY",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "priority": 1
        },
        {
            "provider": "nvidia", 
            "model": "meta/llama-3.1-405b-instruct",
            "api_key_env": "NVIDIA_API_KEY",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "priority": 2
        },
        {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
            "priority": 3
        },
        {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
            "priority": 4
        }
    ]
    
    TTS_MODELS = [
        {
            "provider": "volcengine",
            "voice": "zh_female_xiaoxiao",
            "api_key_env": "VOLCENGINE_TOKEN",
            "appid_env": "VOLCENGINE_APPID",
            "priority": 1
        },
        {
            "provider": "openai",
            "voice": "alloy",
            "api_key_env": "OPENAI_API_KEY",
            "priority": 2
        },
        {
            "provider": "edge-tts",
            "voice": "zh-CN-XiaoxiaoNeural",
            "priority": 3  # 免费，总是可用
        }
    ]
    
    def __init__(self, cache_file: str = "logs/model_health_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 可用模型缓存
        self._available_llm: List[Dict[str, Any]] = []
        self._available_tts: List[Dict[str, Any]] = []
        self._last_check: Optional[datetime] = None
        
        # 当前使用的模型索引
        self._current_llm_index = 0
        self._current_tts_index = 0
        
        # 服务启动时执行自检
        self._startup_health_check()
    
    def _startup_health_check(self) -> None:
        """服务启动时执行完整自检"""
        logger.info("Starting model health check on startup...")
        
        # 检查 LLM 模型
        self._available_llm = []
        for model_config in self.LLM_MODELS:
            if self._check_llm_model(model_config):
                self._available_llm.append(model_config)
                logger.info(f"✅ LLM model available: {model_config['model']}")
            else:
                logger.warning(f"❌ LLM model unavailable: {model_config['model']}")
        
        # 检查 TTS 模型
        self._available_tts = []
        for model_config in self.TTS_MODELS:
            if self._check_tts_model(model_config):
                self._available_tts.append(model_config)
                logger.info(f"✅ TTS model available: {model_config['provider']}")
            else:
                logger.warning(f"❌ TTS model unavailable: {model_config['provider']}")
        
        self._last_check = datetime.now()
        
        # 保存缓存
        self._save_cache()
        
        logger.info(
            f"Health check complete. Available: {len(self._available_llm)} LLM, "
            f"{len(self._available_tts)} TTS models"
        )
    
    def _check_llm_model(self, config: Dict[str, Any]) -> bool:
        """检查具体 LLM 模型是否可用"""
        try:
            import requests
            
            api_key = os.environ.get(config["api_key_env"])
            if not api_key:
                return False
            
            # 发送简单测试请求
            response = requests.post(
                f"{config['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config["model"],
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                },
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"LLM health check failed for {config['model']}: {e}")
            return False
    
    def _check_tts_model(self, config: Dict[str, Any]) -> bool:
        """检查具体 TTS 模型是否可用"""
        provider = config["provider"]
        
        try:
            if provider == "volcengine":
                return self._check_volcengine(config)
            elif provider == "openai":
                return self._check_openai_tts(config)
            elif provider == "edge-tts":
                return True  # 免费服务，假设可用
            return False
        except Exception as e:
            logger.debug(f"TTS health check failed for {provider}: {e}")
            return False
    
    def _check_volcengine(self, config: Dict[str, Any]) -> bool:
        """检查火山引擎"""
        import requests
        
        api_key = os.environ.get(config["api_key_env"])
        appid = os.environ.get(config["appid_env"])
        
        if not api_key or not appid:
            return False
        
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers={
                "Authorization": f"Bearer;{api_key}",
                "Content-Type": "application/json"
            },
            json={
                "app": {"appid": appid, "token": api_key, "cluster": "volcano_tts"},
                "user": {"uid": "health-check"},
                "audio": {"voice_type": config["voice"], "encoding": "mp3"},
                "request": {"reqid": "health-check", "text": "测试", "text_type": "plain", "operation": "sync"}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("code") == 0 or "text" in str(data.get("message", "")).lower()
        return False
    
    def _check_openai_tts(self, config: Dict[str, Any]) -> bool:
        """检查 OpenAI TTS"""
        import requests
        
        api_key = os.environ.get(config["api_key_env"])
        if not api_key:
            return False
        
        # 检查 API key 是否有效
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        return response.status_code == 200
    
    def _save_cache(self) -> None:
        """保存健康检查结果到缓存文件"""
        cache_data = {
            "timestamp": self._last_check.isoformat() if self._last_check else None,
            "available_llm": self._available_llm,
            "available_tts": self._available_tts,
            "current_llm_index": self._current_llm_index,
            "current_tts_index": self._current_tts_index
        }
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health cache: {e}")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取当前 LLM 模型配置"""
        if not self._available_llm:
            raise RuntimeError("No LLM models available")
        
        if self._current_llm_index >= len(self._available_llm):
            self._current_llm_index = 0
        
        return self._available_llm[self._current_llm_index]
    
    def get_tts_config(self) -> Dict[str, Any]:
        """获取当前 TTS 模型配置"""
        if not self._available_tts:
            raise RuntimeError("No TTS models available")
        
        if self._current_tts_index >= len(self._available_tts):
            self._current_tts_index = 0
        
        return self._available_tts[self._current_tts_index]
    
    def switch_llm_model(self) -> Tuple[Dict[str, Any], bool]:
        """
        切换到下一个可用的 LLM 模型
        
        Returns:
            (新配置, 是否成功切换)
        """
        if len(self._available_llm) <= 1:
            logger.error("No fallback LLM models available")
            return self.get_llm_config(), False
        
        old_model = self._available_llm[self._current_llm_index]["model"]
        self._current_llm_index = (self._current_llm_index + 1) % len(self._available_llm)
        new_config = self._available_llm[self._current_llm_index]
        
        logger.warning(
            f"🔄 Switched LLM model from {old_model} to {new_config['model']}"
        )
        
        self._save_cache()
        return new_config, True
    
    def switch_tts_model(self) -> Tuple[Dict[str, Any], bool]:
        """
        切换到下一个可用的 TTS 模型
        
        Returns:
            (新配置, 是否成功切换)
        """
        if len(self._available_tts) <= 1:
            logger.error("No fallback TTS models available")
            return self.get_tts_config(), False
        
        old_provider = self._available_tts[self._current_tts_index]["provider"]
        self._current_tts_index = (self._current_tts_index + 1) % len(self._available_tts)
        new_config = self._available_tts[self._current_tts_index]
        
        logger.warning(
            f"🔄 Switched TTS provider from {old_provider} to {new_config['provider']}"
        )
        
        self._save_cache()
        return new_config, True
    
    def report_llm_failure(self) -> Dict[str, Any]:
        """
        报告 LLM 模型故障，触发切换
        
        Returns:
            新的模型配置
        """
        logger.error(f"❌ LLM model {self.get_llm_config()['model']} reported failure, switching...")
        new_config, success = self.switch_llm_model()
        
        if not success:
            raise RuntimeError("Failed to switch to alternative LLM model")
        
        return new_config
    
    def report_tts_failure(self) -> Dict[str, Any]:
        """
        报告 TTS 模型故障，触发切换
        
        Returns:
            新的模型配置
        """
        logger.error(f"❌ TTS provider {self.get_tts_config()['provider']} reported failure, switching...")
        new_config, success = self.switch_tts_model()
        
        if not success:
            raise RuntimeError("Failed to switch to alternative TTS model")
        
        return new_config
    
    def get_status(self) -> Dict[str, Any]:
        """获取健康检查状态"""
        return {
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "available_llm_count": len(self._available_llm),
            "available_tts_count": len(self._available_tts),
            "current_llm": self.get_llm_config()["model"] if self._available_llm else None,
            "current_tts": self.get_tts_config()["provider"] if self._available_tts else None,
            "all_llm_models": [m["model"] for m in self._available_llm],
            "all_tts_models": [m["provider"] for m in self._available_tts]
        }


# 全局健康检查器实例
_health_checker: Optional[ModelHealthChecker] = None


def get_health_checker() -> ModelHealthChecker:
    """获取健康检查器实例（单例）"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ModelHealthChecker()
    return _health_checker
