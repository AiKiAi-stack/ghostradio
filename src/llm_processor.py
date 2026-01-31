"""
LLM 内容处理模块
使用 Provider 架构支持多种 LLM API
"""

import os
from typing import Dict, Any, Optional

# 导入 Provider 系统
from .providers import create_provider, ProviderFactory


class LLMProcessor:
    """
    LLM 处理器 - 将文章内容转换为播客脚本
    
    支持多种 Provider：
    - nvidia: NVIDIA API
    - openai: OpenAI 及兼容 API（DeepSeek、Azure 等）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 处理器
        
        Args:
            config: 配置字典，包含：
                - provider: Provider 名称（nvidia/openai）
                - api_key: API 密钥
                - model: 模型名称
                - temperature: 温度参数
                - max_tokens: 最大 token 数
                - prompt_file: 系统提示词文件路径
        """
        self.config = config
        
        # 从环境变量获取 API key（如果配置了）
        api_key_env = config.get('api_key_env')
        if api_key_env and not config.get('api_key'):
            config['api_key'] = os.environ.get(api_key_env)
        
        # 创建 Provider
        try:
            self.provider = create_provider(config)
        except ValueError as e:
            # 如果指定的 provider 不存在，回退到 openai
            print(f"Warning: {e}, falling back to 'openai' provider")
            config['provider'] = 'openai'
            self.provider = create_provider(config)
    
    def process(self, title: str, content: str) -> dict:
        """
        处理文章内容，生成播客脚本
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            dict: {
                'success': bool,
                'script': str,
                'tokens_used': int,
                'error': str (if failed)
            }
        """
        try:
            # 加载系统提示词
            system_prompt = self._load_system_prompt()
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(title, content)
            
            # 格式化消息
            messages = self.provider.format_messages(system_prompt, user_prompt)
            
            # 调用 LLM
            result = self.provider.chat_completion(messages)
            
            if result['success']:
                return {
                    'success': True,
                    'script': result['content'],
                    'tokens_used': result.get('tokens_used', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM processing error: {str(e)}'
            }
    
    def _load_system_prompt(self) -> str:
        """
        加载系统提示词
        
        Returns:
            str: 系统提示词内容
        """
        prompt_file = self.config.get('prompt_file', 'prompts/podcast_host.txt')
        
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 默认提示词
        return """你是一位专业的播客主持人，擅长将文章内容转化为生动有趣的播客节目。

风格：轻松自然、富有感染力
语气：友好、专业但不失亲和力
语言：中文（除非原文是其他语言）

任务：
1. 阅读并理解提供的文章内容
2. 提取核心观点和关键信息
3. 将内容重新组织为适合音频收听的形式
4. 添加适当的过渡语和连接词
5. 在开头简要介绍文章主题
6. 在结尾提供简短的总结或个人见解

注意事项：
- 保持段落简短，便于朗读
- 使用口语化表达，避免过于书面化的长句
- 适当添加停顿标记（用"..."表示）
- 总长度控制在 5-10 分钟朗读时间（约 800-1500 字）

请直接输出适合朗读的播客脚本，不需要标注"主持人："等角色前缀。"""
    
    def _build_user_prompt(self, title: str, content: str) -> str:
        """
        构建用户提示
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            str: 用户提示词
        """
        return f"""请将以下文章转换为播客脚本：

文章标题：{title}

文章内容：
{content}

请生成适合朗读的播客脚本，要求：
1. 开头简单介绍这篇文章的主题
2. 用口语化的方式讲述核心内容
3. 结尾给出简短总结
4. 总长度控制在 5-10 分钟朗读时间"""
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取当前 Provider 信息
        
        Returns:
            dict: Provider 信息
        """
        return {
            'name': self.provider.get_provider_name(),
            'model': self.provider.model,
            'available_models': self.provider.get_model_list()
        }


# 向后兼容的便捷函数
def get_available_providers() -> list:
    """
    获取所有可用的 Provider 列表
    
    Returns:
        list: Provider 名称列表
    """
    return ProviderFactory.get_available_providers()
