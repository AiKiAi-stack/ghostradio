"""
URL 内容获取模块
支持从各种网页提取正文内容
"""

import re
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from .logger import get_logger

logger = get_logger("content_fetcher")


class ContentFetcher:
    """内容获取器"""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout: int = timeout
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch(self, url: str) -> Dict[str, Any]:
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
        logger.info(f"Fetching URL: {url}")
        
        try:
            if not self._is_valid_url(url):
                logger.error(f"Invalid URL format: {url}")
                return {
                    'success': False,
                    'error': 'Invalid URL format',
                    'url': url
                }

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            response.encoding = response.apparent_encoding

            html: str = response.text
            title: str = self._extract_title(html)
            content: Optional[str] = self._extract_content(html)

            if not content:
                logger.warning(f"No content extracted from {url}")
                return {
                    'success': False,
                    'error': 'Could not extract content from page',
                    'url': url
                }

            content_length = len(content)
            logger.info(
                f"Successfully fetched content",
                context={
                    "url": url,
                    "title": title,
                    "content_length": content_length,
                    "title_length": len(title)
                }
            )

            return {
                'success': True,
                'title': title,
                'content': content,
                'url': url
            }

        except requests.RequestException as e:
            logger.error(f"Network error fetching {url}: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'url': url
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}")
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
        except Exception:
            return False

    def _extract_title(self, html: str) -> str:
        """从 HTML 中提取标题"""
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            return self._clean_text(title_match.group(1))

        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return self._clean_text(h1_match.group(1))

        return "Untitled"

    def _extract_content(self, html: str) -> Optional[str]:
        """从 HTML 中提取正文内容"""
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<aside[^>]*>.*?</aside>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)

        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            content: str = article_match.group(1)
        else:
            main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
            if main_match:
                content = main_match.group(1)
            else:
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
                content = body_match.group(1) if body_match else html

        text_parts: List[str] = []

        paragraphs: List[str] = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
        for p in paragraphs:
            text: str = self._clean_html_tags(p)
            if len(text) > 20:
                text_parts.append(text)

        if len(text_parts) < 3:
            text = self._clean_html_tags(content)
            sentences: List[str] = re.split(r'[。！？.!?]+', text)
            text_parts = [s.strip() for s in sentences if len(s.strip()) > 20]

        full_text: str = '\n\n'.join(text_parts)

        if len(full_text) > 50000:
            full_text = full_text[:50000] + "..."

        return full_text

    def _clean_html_tags(self, html: str) -> str:
        """移除 HTML 标签"""
        text: str = re.sub(r'<[^>]+>', '', html)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        return text

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
