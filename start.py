#!/usr/bin/env python3
"""
GhostRadio 启动脚本
简化常用操作
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

def run_server():
    """启动触发器服务器"""
    print("🚀 启动 GhostRadio 触发器服务器...")
    print("访问 http://localhost:8080 查看状态")
    print("按 Ctrl+C 停止\n")
    
    server_script = PROJECT_ROOT / 'src' / 'server.py'
    subprocess.run([sys.executable, str(server_script)])

def run_worker():
    """手动运行 Worker"""
    print("⚙️  运行 GhostRadio Worker...\n")
    
    worker_script = PROJECT_ROOT / 'src' / 'worker.py'
    subprocess.run([sys.executable, str(worker_script), '--once'])

def run_scheduler():
    """运行调度器"""
    print("📅 运行 GhostRadio 调度器...\n")
    
    scheduler_script = PROJECT_ROOT / 'src' / 'scheduler.py'
    subprocess.run([sys.executable, str(scheduler_script)])

def test_config():
    """测试配置"""
    print("🧪 测试配置...\n")
    
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.config import get_config
        
        config = get_config()
        
        print("✅ 配置文件加载成功")
        print(f"\n播客标题: {config.get('podcast.title')}")
        print(f"播客作者: {config.get('podcast.author')}")
        print(f"LLM 提供商: {config.get('llm.provider')}")
        print(f"TTS 提供商: {config.get('tts.provider')}")
        print(f"音频格式: {config.get('resources.audio_format')}")
        
        # 检查环境变量
        llm_key = config.get('llm.api_key_env')
        tts_key = config.get('tts.api_key_env')
        
        print(f"\n环境变量检查:")
        print(f"  {llm_key}: {'✅ 已设置' if os.environ.get(llm_key) else '❌ 未设置'}")
        print(f"  {tts_key}: {'✅ 已设置' if os.environ.get(tts_key) else '❌ 未设置'}")
        
        print("\n✅ 配置测试通过")
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        sys.exit(1)

def generate_rss():
    """生成 RSS Feed"""
    print("📻 生成 RSS Feed...\n")
    
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.config import get_config
        from src.file_manager import FileManager
        from src.rss_generator import RSSGenerator
        
        config = get_config()
        
        # 获取节目列表
        file_manager = FileManager(config.get_resources_config())
        episodes = file_manager.get_episodes()
        
        if not episodes:
            print("⚠️  没有找到节目文件")
            return
        
        print(f"找到 {len(episodes)} 个节目")
        
        # 生成 RSS
        rss_gen = RSSGenerator(config._config)
        rss_path = rss_gen.save_rss(episodes)
        
        print(f"✅ RSS 已生成: {rss_path}")
        
    except Exception as e:
        print(f"❌ RSS 生成失败: {e}")
        sys.exit(1)

def submit_url(url: str):
    """提交 URL 到队列"""
    print(f"📝 提交 URL: {url}\n")
    
    import requests
    
    try:
        response = requests.post(
            'http://localhost:8080/webhook',
            json={'url': url},
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ URL 已添加到队列")
            print(f"响应: {response.json()}")
        else:
            print(f"❌ 提交失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("请先运行: python start.py server")
    except Exception as e:
        print(f"❌ 提交失败: {e}")

def show_help():
    """显示帮助信息"""
    print("""
GhostRadio 启动脚本

用法: python start.py <命令>

命令:
  server     启动触发器服务器
  worker     手动运行 Worker 处理队列
  scheduler  运行调度器检查队列
  test       测试配置
  rss        生成 RSS Feed
  submit     提交 URL 到队列 (需要 --url 参数)
  help       显示此帮助信息

示例:
  python start.py server              # 启动服务器
  python start.py worker              # 手动运行 Worker
  python start.py test                # 测试配置
  python start.py submit --url https://example.com/article
    """)

def main():
    parser = argparse.ArgumentParser(
        description='GhostRadio 启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        choices=['server', 'worker', 'scheduler', 'test', 'rss', 'submit', 'help'],
        help='要执行的命令'
    )
    parser.add_argument(
        '--url',
        help='要提交的 URL (用于 submit 命令)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'server':
        run_server()
    elif args.command == 'worker':
        run_worker()
    elif args.command == 'scheduler':
        run_scheduler()
    elif args.command == 'test':
        test_config()
    elif args.command == 'rss':
        generate_rss()
    elif args.command == 'submit':
        if not args.url:
            print("❌ 请提供 --url 参数")
            print("示例: python start.py submit --url https://example.com/article")
            sys.exit(1)
        submit_url(args.url)
    elif args.command == 'help':
        show_help()

if __name__ == '__main__':
    main()
