#!/usr/bin/env python3
"""
Content Fetcher Tests
Test URL content extraction and edge cases
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.content_fetcher import ContentFetcher


class TestContentFetcher(unittest.TestCase):
    """Test ContentFetcher functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = ContentFetcher()
        self.test_url = "https://example.com/test-article"
    
    def test_valid_url_check(self):
        """Test URL validation"""
        # Valid URLs
        self.assertTrue(self.fetcher._is_valid_url("https://example.com"))
        self.assertTrue(self.fetcher._is_valid_url("http://test.org/path"))
        self.assertTrue(self.fetcher._is_valid_url("https://sub.example.com/path/to/page"))
        
        # Invalid URLs
        self.assertFalse(self.fetcher._is_valid_url(""))
        self.assertFalse(self.fetcher._is_valid_url("not-a-url"))
        self.assertFalse(self.fetcher._is_valid_url("ftp://example.com"))
        self.assertFalse(self.fetcher._is_valid_url("javascript:alert('xss')"))
    
    def test_title_extraction(self):
        """Test HTML title extraction"""
        # Test title tag
        html_with_title = "<html><head><title>Test Article Title</title></head><body>Content</body></html>"
        self.assertEqual(self.fetcher._extract_title(html_with_title), "Test Article Title")
        
        # Test H1 fallback
        html_with_h1 = "<html><body><h1>Headline Title</h1><p>Content</p></body></html>"
        self.assertEqual(self.fetcher._extract_title(html_with_h1), "Headline Title")
        
        # Test no title
        html_no_title = "<html><body><p>Just content</p></body></html>"
        self.assertEqual(self.fetcher._extract_title(html_no_title), "Untitled")
    
    def test_content_extraction(self):
        """Test HTML content extraction"""
        # Test article tag
        html_article = """
        <html>
            <head><title>Test</title></head>
            <body>
                <header>Header</header>
                <article>
                    <p>This is the first paragraph with substantial content that should be extracted.</p>
                    <p>This is the second paragraph with more than 20 characters.</p>
                    <p>This is the third paragraph for testing.</p>
                </article>
                <footer>Footer</footer>
            </body>
        </html>
        """
        content = self.fetcher._extract_content(html_article)
        self.assertIn("first paragraph", content or '')
        self.assertIn("second paragraph", content or '')
        self.assertIn("third paragraph", content or '')
        self.assertNotIn("Header", content or '')
        self.assertNotIn("Footer", content or '')
        
        # Test main tag
        html_main = """
        <html>
            <body>
                <nav>Navigation</nav>
                <main>
                    <p>Main content paragraph 1 with sufficient length.</p>
                    <p>Main content paragraph 2 with sufficient length.</p>
                </main>
                <aside>Sidebar</aside>
            </body>
        </html>
        """
        content = self.fetcher._extract_content(html_main)
        self.assertIn("Main content paragraph", content or '')
        self.assertNotIn("Navigation", content or '')
        self.assertNotIn("Sidebar", content or '')
    
    def test_html_cleaning(self):
        """Test HTML tag cleaning"""
        dirty_html = "This is <b>bold</b> text with <a href='link'>link</a> and &amp; entities."
        clean = self.fetcher._clean_html_tags(dirty_html)
        self.assertEqual(clean, "This is bold text with link and & entities.")
        
        # Test HTML entities
        html_entities = "Test &nbsp; space &lt;tag&gt; &quot;quote&quot; &#39;apostrophe&#39;"
        clean = self.fetcher._clean_html_tags(html_entities)
        self.assertEqual(clean, 'Test  space <tag> "quote" \'apostrophe\'')
    
    def test_text_cleaning(self):
        """Test text whitespace cleaning"""
        messy_text = "  This   has   \t\n  multiple   spaces  \n\n and  lines  "
        clean = self.fetcher._clean_text(messy_text)
        self.assertEqual(clean, "This has multiple spaces and lines")
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_successful_fetch(self, mock_get):
        """Test successful URL fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <article>
                    <p>First paragraph with substantial content for testing purposes.</p>
                    <p>Second paragraph with enough content to be extracted.</p>
                    <p>Third paragraph to ensure we have minimum required content.</p>
                </article>
            </body>
        </html>
        """
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['title'], 'Test Article')
        self.assertIn('First paragraph', result['content'])
        self.assertIn('Second paragraph', result['content'])
        self.assertEqual(result['url'], self.test_url)
        
        # Verify request was made with correct headers
        mock_get.assert_called_once_with(self.test_url, timeout=30)
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_invalid_url(self, mock_get):
        """Test fetching with invalid URL"""
        invalid_url = "not-a-url"
        result = self.fetcher.fetch(invalid_url)
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid URL format', result['error'])
        self.assertEqual(result['url'], invalid_url)
        
        # Should not make HTTP request
        mock_get.assert_not_called()
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_network_error(self, mock_get):
        """Test handling of network errors"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Network failed")
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertFalse(result['success'])
        self.assertIn('Network error', result['error'])
        self.assertEqual(result['url'], self.test_url)
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_http_error(self, mock_get):
        """Test handling of HTTP errors"""
        import requests
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertFalse(result['success'])
        self.assertIn('Network error', result['error'])
        self.assertEqual(result['url'], self.test_url)
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_no_content(self, mock_get):
        """Test handling of pages with no extractable content"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = """
        <html>
            <head><title>Empty Page</title></head>
            <body>
                <p>Short</p>
            </body>
        </html>
        """
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertFalse(result['success'])
        self.assertIn('Could not extract content', result['error'])
        self.assertEqual(result['url'], self.test_url)
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_large_content_truncation(self, mock_get):
        """Test content truncation for very large pages"""
        # Create large content
        large_content = "This is a long paragraph. " * 1000  # About 25,000 characters
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = f"""
        <html>
            <head><title>Large Article</title></head>
            <body>
                <article>
                    <p>{large_content}</p>
                </article>
            </body>
        </html>
        """
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertTrue(result['success'])
        # Content should be truncated to 50,000 chars and have "..."
        self.assertLessEqual(len(result['content']), 50300)  # 50,000 + "..."
        if len(result['content']) >= 50000:
            self.assertTrue(result['content'].endswith("..."))
    
    @patch('src.content_fetcher.requests.Session.get')
    def test_fetch_encoding_handling(self, mock_get):
        """Test handling of different content encodings"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        # Mock content with special characters that need proper encoding
        mock_response.text = """
        <html>
            <head><title>编码测试</title></head>
            <body>
                <article>
                    <p>这是一个包含中文的测试段落，内容足够长以被提取。</p>
                    <p>这是第二个中文段落，同样包含足够的内容。</p>
                </article>
            </body>
        </html>
        """
        mock_response.apparent_encoding = 'gbk'  # Simulate different encoding
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch(self.test_url)
        
        self.assertTrue(result['success'])
        self.assertIn('编码测试', result['title'])
        self.assertIn('中文的测试段落', result['content'])


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)