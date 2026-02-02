#!/usr/bin/env python3
"""
GhostRadio 快速测试脚本
验证核心功能是否正常工作
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """测试所有模块是否可以正常导入"""
    print("[TEST] 测试模块导入...")
    
    try:
        from src import config
        from src import content_fetcher
        from src import llm_processor
        from src import tts_generator
        from src import file_manager
        from src import file_lock
        from src import rss_generator
        print("[PASS] 所有模块导入成功\n")
        return True
    except Exception as e:
        print(f"[FAIL] 模块导入失败: {e}\n")
        return False

def test_config_loading():
    """测试配置加载"""
    print("[TEST] 测试配置加载...")
    
    try:
        from src.config import Config
        
        # 测试加载示例配置
        config = Config('config.example.yaml')
        
        # 验证关键配置项
        assert config.get('podcast.title') is not None
        assert config.get('llm.provider') is not None
        assert config.get('resources.audio_format') is not None
        
        print("[PASS] 配置加载成功")
        print(f"  播客标题: {config.get('podcast.title')}")
        print(f"  LLM 提供商: {config.get('llm.provider')}")
        print(f"  音频格式: {config.get('resources.audio_format')}\n")
        return True
        
    except FileNotFoundError:
        print("[WARN] config.example.yaml 不存在，跳过配置测试\n")
        return True
    except Exception as e:
        print(f"[FAIL] 配置加载失败: {e}\n")
        return False

def test_file_lock():
    """测试文件锁"""
    print("[TEST] 测试文件锁...")
    
    try:
        from src.file_lock import FileLock
        import tempfile
        
        # 创建临时锁文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.lock') as f:
            lock_file = f.name
        
        # 测试获取锁
        lock = FileLock(lock_file)
        assert lock.acquire() == True, "应该能获取锁"
        
        # 测试重复获取（应该失败）
        lock2 = FileLock(lock_file)
        assert lock2.acquire() == False, "不应该能获取已被占用的锁"
        
        # 释放锁
        lock.release()
        
        # 清理
        os.remove(lock_file)
        
        print("[PASS] 文件锁功能正常\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] 文件锁测试失败: {e}\n")
        return False

def test_content_fetcher():
    """测试内容获取器（模拟测试）"""
    print("[TEST] 测试内容获取器...")
    
    try:
        from src.content_fetcher import ContentFetcher
        
        fetcher = ContentFetcher()
        
        # 测试 URL 验证
        assert fetcher._is_valid_url('https://example.com') == True
        assert fetcher._is_valid_url('http://test.com/path') == True
        assert fetcher._is_valid_url('ftp://invalid.com') == False
        assert fetcher._is_valid_url('not-a-url') == False
        
        # 测试文本清理
        html = '<p>Hello <b>World</b></p>'
        text = fetcher._clean_html_tags(html)
        assert 'Hello' in text and 'World' in text
        
        print("[PASS] 内容获取器基础功能正常\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] 内容获取器测试失败: {e}\n")
        return False

def test_rss_generator():
    """测试 RSS 生成器"""
    print("[TEST] 测试 RSS 生成器...")
    
    try:
        from src.rss_generator import RSSGenerator
        from datetime import datetime
        
        config = {
            'podcast': {
                'title': 'Test Podcast',
                'description': 'Test Description',
                'author': 'Test Author',
                'base_url': 'https://test.com',
                'language': 'zh-CN',
                'category': 'Technology'
            },
            'resources': {
                'audio_format': 'm4a'
            }
        }
        
        rss_gen = RSSGenerator(config)
        
        # 测试节目数据
        episodes = [
            {
                'id': 'test-001',
                'title': 'Test Episode',
                'description': 'Test episode description',
                'created': datetime.now(),
                'audio_file': '/path/to/test.m4a',
                'size_mb': 10.5,
                'duration': 300
            }
        ]
        
        # 生成 RSS
        rss_xml = rss_gen.generate(episodes)
        
        # 验证 RSS 包含关键元素
        assert '<rss' in rss_xml
        assert 'Test Podcast' in rss_xml
        assert 'Test Episode' in rss_xml
        
        print("[PASS] RSS 生成器功能正常\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] RSS 生成器测试失败: {e}\n")
        return False

def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("GhostRadio 快速测试")
    print("="*50 + "\n")
    
    tests = [
        test_imports,
        test_config_loading,
        test_file_lock,
        test_content_fetcher,
        test_rss_generator
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ 测试异常: {e}\n")
            results.append(False)
    
    # 统计结果
    passed = sum(results)
    total = len(results)
    
    print("="*50)
    print(f"测试结果: {passed}/{total} 通过")
    print("="*50)
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！GhostRadio 已准备好使用。")
        print("\n下一步:")
        print("1. 复制 config.example.yaml 为 config.yaml")
        print("2. 配置你的 API 密钥")
        print("3. 运行: python start.py server")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查错误信息。")
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
