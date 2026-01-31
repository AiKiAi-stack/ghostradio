"""
Prompt 管理模块
从 YAML 配置文件加载和管理所有 Prompt
"""

import os
import yaml
from typing import Dict, Any, Optional


class PromptManager:
    """Prompt 管理器"""
    
    def __init__(self, prompts_file: str = "prompts/prompts.yaml"):
        """
        初始化 Prompt 管理器
        
        Args:
            prompts_file: Prompt 配置文件路径
        """
        self.prompts_file = prompts_file
        self._prompts: Dict[str, Any] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """加载 Prompt 配置文件"""
        if not os.path.exists(self.prompts_file):
            raise FileNotFoundError(f"Prompt file not found: {self.prompts_file}")
        
        with open(self.prompts_file, 'r', encoding='utf-8') as f:
            self._prompts = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取 Prompt，支持点号分隔的路径
        
        Args:
            key: Prompt 键名，如 "llm.default_host"
            default: 默认值
            
        Returns:
            Prompt 内容
        """
        keys = key.split('.')
        value = self._prompts
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_system_prompt(self, prompt_type: str = "default_host") -> str:
        """
        获取系统 Prompt
        
        Args:
            prompt_type: Prompt 类型，如 default_host, concise_host, academic_host
            
        Returns:
            系统 Prompt 文本
        """
        prompt = self.get(f"llm.{prompt_type}")
        if not prompt:
            # 返回默认 Prompt
            return self.get("llm.default_host", "")
        return prompt
    
    def format_user_prompt(self, template_key: str, **kwargs) -> str:
        """
        格式化用户 Prompt 模板
        
        Args:
            template_key: 模板键名，如 "article_to_podcast"
            **kwargs: 模板变量
            
        Returns:
            格式化后的 Prompt
        """
        template = self.get(f"user_templates.{template_key}")
        if not template:
            # 使用默认模板
            template = """请将以下文章转换为播客脚本：

文章标题：{title}

文章内容：
{content}

请生成适合朗读的播客脚本。"""
        
        return template.format(**kwargs)
    
    def get_error_message(self, error_key: str) -> str:
        """
        获取错误消息
        
        Args:
            error_key: 错误键名
            
        Returns:
            错误消息文本
        """
        return self.get(f"error_messages.{error_key}", "操作失败")
    
    def get_system_message(self, message_key: str, **kwargs) -> str:
        """
        获取系统消息
        
        Args:
            message_key: 消息键名
            **kwargs: 消息变量
            
        Returns:
            格式化后的消息
        """
        message = self.get(f"system_messages.{message_key}", "")
        if message and kwargs:
            return message.format(**kwargs)
        return message


# 全局 Prompt 管理器实例
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_file: str = "prompts/prompts.yaml") -> PromptManager:
    """
    获取 Prompt 管理器实例（单例模式）
    
    Args:
        prompts_file: Prompt 配置文件路径
        
    Returns:
        PromptManager 实例
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(prompts_file)
    return _prompt_manager


def reload_prompts(prompts_file: str = "prompts/prompts.yaml") -> PromptManager:
    """
    重新加载 Prompt 配置
    
    Args:
        prompts_file: Prompt 配置文件路径
        
    Returns:
        PromptManager 实例
    """
    global _prompt_manager
    _prompt_manager = PromptManager(prompts_file)
    return _prompt_manager
