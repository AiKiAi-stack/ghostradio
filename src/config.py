"""
GhostRadio 配置加载模块
"""

import os
import yaml
from typing import Dict, Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n"
                f"请复制 config.example.yaml 为 {self.config_path} 并配置"
            )
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None, value_type: type = str) -> Any:
        """获取配置项，支持点号分隔的路径和类型转换"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        try:
            if value_type != str and value is not None:
                return value_type(value)
            return value
        except (TypeError, ValueError):
            return default
    
    def get_env_value(self, env_var: str) -> Optional[str]:
        """从环境变量获取值"""
        return os.environ.get(env_var)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置"""
        llm = self.get('llm', {})
        api_key_env = llm.get('api_key_env', 'LLM_API_KEY')
        
        return {
            'provider': llm.get('provider', 'custom'),
            'base_url': llm.get('base_url', ''),
            'api_key': self.get_env_value(api_key_env),
            'model_name': llm.get('model_name', ''),
            'context_window': llm.get('context_window', 16000),
            'temperature': llm.get('temperature', 0.7),
            'prompt_file': llm.get('prompt_file', 'prompts/podcast_host.txt')
        }
    
    def get_tts_config(self) -> Dict[str, Any]:
        """获取 TTS 配置"""
        tts = self.get('tts', {})
        api_key_env = tts.get('api_key_env', 'TTS_API_KEY')
        
        return {
            'provider': tts.get('provider', 'openai'),
            'api_key': self.get_env_value(api_key_env),
            'voice': tts.get('voice', 'alloy'),
            'speed': tts.get('speed', 1.0)
        }
    
    def get_resources_config(self) -> Dict[str, Any]:
        """获取资源限制配置"""
        resources = self.get('resources', {})
        
        return {
            'max_concurrent_tasks': resources.get('max_concurrent_tasks', 1),
            'keep_last_n_episodes': resources.get('keep_last_n_episodes', 5),
            'max_disk_usage_mb': resources.get('max_disk_usage_mb', 200),
            'audio_format': resources.get('audio_format', 'm4a'),
            'audio_quality': resources.get('audio_quality', 'medium')
        }
    
    def get_podcast_config(self) -> Dict[str, Any]:
        """获取播客配置"""
        podcast = self.get('podcast', {})
        
        return {
            'title': podcast.get('title', 'GhostRadio'),
            'description': podcast.get('description', 'AI Generated Podcast'),
            'author': podcast.get('author', 'GhostRadio'),
            'email': podcast.get('email', ''),
            'language': podcast.get('language', 'zh-CN'),
            'category': podcast.get('category', 'Technology'),
            'base_url': podcast.get('base_url', ''),
            'cover_image': podcast.get('cover_image', 'cover.jpg')
        }
    
    def get_paths_config(self) -> Dict[str, str]:
        """获取路径配置"""
        paths = self.get('paths', {})
        
        return {
            'queue_file': paths.get('queue_file', 'queue.txt'),
            'episodes_dir': paths.get('episodes_dir', 'episodes'),
            'logs_dir': paths.get('logs_dir', 'logs'),
            'rss_file': paths.get('rss_file', 'episodes/feed.xml')
        }
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        scheduler = self.get('scheduler', {})
        
        return {
            'check_interval_minutes': scheduler.get('check_interval_minutes', 5),
            'nice_level': scheduler.get('nice_level', 19)
        }


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """获取配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: str = "config.yaml") -> Config:
    """重新加载配置"""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
