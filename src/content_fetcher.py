"""
URL 内容获取模块
支持从各种网页提取正文内容
"""

import re
import requests
from typing import Optional
from urllib.parse import urlparse


class ContentFetcher:
    """内容获取器"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch(self, url: str) -> dict:
        """
        获取 URL 内容
        
        Returns:
            dict: {
                'title': str,
                'content': str,
                'url': str,
                'success': bool,
                'error': str (if failed)
            }
        """
        try:
            # 验证 URL
            if not self._is_valid_url(url):
                return {
                    'success': False,
                    'error': 'Invalid URL format',
                    'url': url
                }
            
            # 发送请求
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 检测编码
            response.encoding = response.apparent_encoding
            
            # 解析内容
            html = response.text
            title = self._extract_title(html)
            content = self._extract_content(html)
            
            if not content:
                return {
                    'success': False,
                    'error': 'Could not extract content from page',
                    'url': url
                }
            
            return {
                'success': True,
                'title': title,
                'content': content,
                'url': url
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'url': url
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error: {str(e)}',
                'url': url
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """验证 URL 格式"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
    
    def _extract_title(self, html: str) -> str:
        """从 HTML 中提取标题"""
        # 尝试提取 title 标签
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            return self._clean_text(title_match.group(1))
        
        # 尝试提取 h1 标签
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return self._clean_text(h1_match.group(1))
        
        return "Untitled"
    
    def _extract_content(self, html: str) -> str:
        """从 HTML 中提取正文内容"""
        # 移除 script 和 style 标签及其内容
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除导航、页脚、侧边栏等常见非内容区域
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<aside[^>]*>.*?</aside>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 尝试提取 article 或 main 标签内容
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            content = article_match.group(1)
        else:
            main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
            if main_match:
                content = main_match.group(1)
            else:
                # 提取 body 内容
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
                content = body_match.group(1) if body_match else html
        
        # 提取段落和标题文本
        text_parts = []
        
        # 提取段落
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
        for p in paragraphs:
            text = self._clean_html_tags(p)
            if len(text) > 20:  # 过滤太短的段落
                text_parts.append(text)
        
        # 如果没有足够的段落，尝试提取所有文本
        if len(text_parts) < 3:
            # 提取所有文本节点
            text = self._clean_html_tags(content)
            # 按句子分割
            sentences = re.split(r'[。！？.!?]+', text)
            text_parts = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # 合并内容
        full_text = '\n\n'.join(text_parts)
        
        # 限制长度
        if len(full_text) > 50000:
            full_text = full_text[:50000] + "..."
        
        return full_text
    
    def _clean_html_tags(self, html: str) -> str:
        """移除 HTML 标签"""
        # 移除所有 HTML 标签
        text = re.sub(r'<[^>]+>', '', html)
        # 解码 HTML 实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        return text
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
