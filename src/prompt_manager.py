"""
Prompt 管理模块
从 YAML 配置文件加载和管理所有 Prompt

设计原则：
- 不可变配置：加载后不修改
- 线程安全：只读访问
- 清晰的错误信息
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


class PromptError(Exception):
    """Prompt 相关错误基类"""
    pass


class PromptFileNotFoundError(PromptError):
    """Prompt 文件未找到"""
    pass


class PromptKeyNotFoundError(PromptError):
    """Prompt 键名不存在"""
    pass


class PromptManager:
    """
    Prompt 管理器
    
    职责：
    - 从 YAML 文件加载 Prompt 配置
    - 提供类型安全的访问方法
    - 支持嵌套键查询
    """
    
    def __init__(self, prompts_file: Union[str, Path] = "prompts/prompts.yaml") -> None:
        """
        初始化 Prompt 管理器
        
        Args:
            prompts_file: Prompt 配置文件路径
            
        Raises:
            PromptFileNotFoundError: 配置文件不存在
        """
        self._prompts_file = Path(prompts_file)
        self._prompts: Dict[str, Any] = {}
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """加载 Prompt 配置文件"""
        if not self._prompts_file.exists():
            raise PromptFileNotFoundError(
                f"Prompt file not found: {self._prompts_file}"
            )
        
        try:
            import yaml
            with open(self._prompts_file, 'r', encoding='utf-8') as f:
                self._prompts = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise PromptError(f"Invalid YAML format in {self._prompts_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取 Prompt 值，支持点号分隔的嵌套键
        
        Args:
            key: 键名，如 "llm.default_host"
            default: 默认值
            
        Returns:
            Prompt 值，不存在返回 default
        """
        keys = key.split('.')
        value = self._prompts
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_required(self, key: str) -> Any:
        """
        获取必需的 Prompt 值
        
        Args:
            key: 键名
            
        Returns:
            Prompt 值
            
        Raises:
            PromptKeyNotFoundError: 键不存在
        """
        value = self.get(key)
        if value is None:
            raise PromptKeyNotFoundError(f"Required prompt key not found: {key}")
        return value
    
    def get_system_prompt(self, prompt_type: str = "default_host") -> str:
        """
        获取系统 Prompt
        
        Args:
            prompt_type: Prompt 类型 (default_host, concise_host, academic_host)
            
        Returns:
            系统 Prompt 文本，如果不存在返回空字符串
        """
        prompt = self.get(f"llm.{prompt_type}")
        return prompt or self.get("llm.default_host", "")
    
    def format_user_prompt(self, template_key: str, **kwargs: Any) -> str:
        """
        格式化用户 Prompt 模板
        
        Args:
            template_key: 模板键名
            **kwargs: 模板变量
            
        Returns:
            格式化后的 Prompt
        """
        template = self.get(f"user_templates.{template_key}")
        
        if not template:
            # 返回最小化的默认模板
            template = "请将以下文章转换为播客脚本：\n\n标题：{title}\n\n内容：{content}"
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise PromptError(f"Missing template variable: {e}")
    
    def get_error_message(self, error_key: str) -> str:
        """
        获取错误消息
        
        Args:
            error_key: 错误键名
            
        Returns:
            错误消息文本
        """
        return self.get(f"error_messages.{error_key}", "操作失败")
    
    def get_system_message(self, message_key: str, **kwargs: Any) -> str:
        """
        获取系统消息
        
        Args:
            message_key: 消息键名
            **kwargs: 格式化变量
            
        Returns:
            格式化后的消息
        """
        message = self.get(f"system_messages.{message_key}", "")
        if message and kwargs:
            try:
                return message.format(**kwargs)
            except KeyError:
                return message
        return message
    
    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._prompts_file


def get_prompt_manager(
    prompts_file: Union[str, Path] = "prompts/prompts.yaml"
) -> PromptManager:
    """
    获取 Prompt 管理器实例（工厂函数）
    
    每次调用都创建新实例，避免单例问题
    
    Args:
        prompts_file: 配置文件路径
        
    Returns:
        PromptManager 实例
    """
    return PromptManager(prompts_file)
