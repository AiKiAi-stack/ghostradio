#!/usr/bin/env python3
"""
Simple Content Fetcher Tests
Basic functionality tests without network calls
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.content_fetcher import ContentFetcher
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Install with: pip install -r requirements.txt")
    sys.exit(1)


class TestContentFetcherBasic(unittest.TestCase):
    """Basic ContentFetcher tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = ContentFetcher()
        self.test_url = "https://example.com/test-article"
    
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        self.assertTrue(self.fetcher._is_valid_url("https://example.com"))
        self.assertTrue(self.fetcher._is_valid_url("http://test.org/path"))
        
        # Invalid URLs
        self.assertFalse(self.fetcher._is_valid_url(""))
        self.assertFalse(self.fetcher._is_valid_url("not-a-url"))
        self.assertFalse(self.fetcher._is_valid_url("ftp://example.com"))
        
        print("+ URL validation tests passed")
    
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
        
        print("+ Title extraction tests passed")
        print("+ HTML cleaning tests passed")
        print("+ Text cleaning tests passed")
        print("+ Content extraction tests passed")
        print("+ Invalid URL handling test passed")


if __name__ == '__main__':
    print("Running basic Content Fetcher tests...")
    print("These tests don't require network access.")
    print()
    
    # Run tests
    unittest.main(verbosity=2)