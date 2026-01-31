"""
LLM 内容处理模块
支持多种 LLM API (OpenAI 格式兼容)
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI


class LLMProcessor:
    """LLM 处理器 - 将文章内容转换为播客脚本"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 OpenAI 客户端"""
        api_key = self.config.get('api_key')
        base_url = self.config.get('base_url')
        
        if not api_key:
            raise ValueError(f"API Key not found in environment variable: {self.config.get('api_key_env', 'LLM_API_KEY')}")
        
        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
        
        self.client = OpenAI(**client_kwargs)
    
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
                'error': str (if failed)
            }
        """
        try:
            # 加载系统提示词
            system_prompt = self._load_system_prompt()
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(title, content)
            
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.config.get('model_name', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.get('temperature', 0.7),
                max_tokens=self.config.get('context_window', 16000)
            )
            
            script = response.choices[0].message.content
            
            return {
                'success': True,
                'script': script,
                'tokens_used': response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM processing error: {str(e)}'
            }
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
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
        """构建用户提示"""
        return f"""请将以下文章转换为播客脚本：

文章标题：{title}

文章内容：
{content}

请生成适合朗读的播客脚本，要求：
1. 开头简单介绍这篇文章的主题
2. 用口语化的方式讲述核心内容
3. 结尾给出简短总结
4. 总长度控制在 5-10 分钟朗读时间"""
