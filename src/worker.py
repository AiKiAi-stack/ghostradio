#!/usr/bin/env python3
"""
GhostRadio Worker - 核心处理脚本
处理队列中的 URL，生成播客音频
"""

import os
import sys
import json
import signal
import argparse
from datetime import datetime
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import get_config
from src.content_fetcher import ContentFetcher
from src.llm_processor import LLMProcessor
from src.tts_generator import TTSGenerator
from src.file_lock import FileLock


class Worker:
    """GhostRadio 工作进程"""
    
    def __init__(self):
        self.config = get_config()
        self.paths = self.config.get_paths_config()
        self.resources = self.config.get_resources_config()
        self.podcast = self.config.get_podcast_config()
        
        # 初始化组件
        self.fetcher = ContentFetcher()
        self.llm = LLMProcessor(self.config.get_llm_config())
        self.tts = TTSGenerator(self.config.get_tts_config())
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        for dir_path in [self.paths['episodes_dir'], self.paths['logs_dir']]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _acquire_lock(self) -> bool:
        """获取文件锁，防止并发运行"""
        lock_file = os.path.join(self.paths['logs_dir'], 'worker.lock')
        self._lock = FileLock(lock_file)
        return self._lock.acquire()
    
    def _release_lock(self):
        """释放文件锁"""
        if hasattr(self, '_lock') and self._lock:
            self._lock.release()
            self._lock = None
    
    def _read_queue(self) -> list:
        """读取队列文件"""
        queue_file = self.paths['queue_file']
        
        if not os.path.exists(queue_file):
            return []
        
        with open(queue_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 解析队列条目
        queue = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|', 1)
            if len(parts) == 2:
                timestamp, url = parts
                queue.append({
                    'timestamp': timestamp,
                    'url': url
                })
        
        return queue
    
    def _clear_queue(self):
        """清空队列文件"""
        queue_file = self.paths['queue_file']
        if os.path.exists(queue_file):
            with open(queue_file, 'w', encoding='utf-8') as f:
                f.write('')
    
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        # 输出到控制台
        print(log_line.strip())
        
        # 写入日志文件
        log_file = os.path.join(self.paths['logs_dir'], 'worker.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
    
    def _generate_episode_id(self) -> str:
        """生成节目 ID"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _cleanup_old_episodes(self):
        """清理旧节目文件"""
        episodes_dir = self.paths['episodes_dir']
        keep_n = self.resources['keep_last_n_episodes']
        max_size_mb = self.resources['max_disk_usage_mb']
        
        # 获取所有音频文件
        audio_files = []
        for ext in ['.mp3', '.m4a', '.ogg', '.opus']:
            audio_files.extend(Path(episodes_dir).glob(f'*{ext}'))
        
        # 按修改时间排序
        audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 删除超过保留数量的文件
        if len(audio_files) > keep_n:
            for old_file in audio_files[keep_n:]:
                try:
                    old_file.unlink()
                    self._log(f"Cleaned up old episode: {old_file.name}")
                except Exception as e:
                    self._log(f"Failed to clean up {old_file.name}: {e}", 'WARNING')
        
        # 检查总大小
        total_size_mb = sum(f.stat().st_size for f in audio_files[:keep_n]) / (1024 * 1024)
        if total_size_mb > max_size_mb:
            self._log(f"Warning: Episodes directory size ({total_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)", 'WARNING')
    
    def process_url(self, url: str) -> dict:
        """处理单个 URL"""
        episode_id = self._generate_episode_id()
        self._log(f"Processing URL: {url}")
        
        try:
            # 1. 获取内容
            self._log("Step 1: Fetching content...")
            content_result = self.fetcher.fetch(url)
            
            if not content_result['success']:
                raise Exception(f"Failed to fetch content: {content_result.get('error', 'Unknown error')}")
            
            title = content_result['title']
            content = content_result['content']
            self._log(f"Fetched: {title}")
            
            # 2. LLM 处理
            self._log("Step 2: Processing with LLM...")
            llm_result = self.llm.process(title, content)
            
            if not llm_result['success']:
                raise Exception(f"LLM processing failed: {llm_result.get('error', 'Unknown error')}")
            
            script = llm_result['script']
            self._log(f"Generated script ({llm_result.get('tokens_used', 0)} tokens)")
            
            # 保存脚本
            script_path = os.path.join(self.paths['episodes_dir'], f"{episode_id}.txt")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: {title}\n")
                f.write(f"Source: {url}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(script)
            
            # 3. TTS 生成
            self._log("Step 3: Generating audio...")
            audio_format = self.resources['audio_format']
            audio_path = os.path.join(self.paths['episodes_dir'], f"{episode_id}.{audio_format}")
            
            tts_result = self.tts.generate(script, audio_path)
            
            if not tts_result['success']:
                raise Exception(f"TTS generation failed: {tts_result.get('error', 'Unknown error')}")
            
            self._log(f"Generated audio: {audio_path}")
            
            # 4. 清理旧文件
            self._cleanup_old_episodes()
            
            return {
                'success': True,
                'episode_id': episode_id,
                'title': title,
                'url': url,
                'audio_path': audio_path,
                'script_path': script_path,
                'duration': tts_result.get('duration', 0)
            }
            
        except Exception as e:
            self._log(f"Error processing URL: {e}", 'ERROR')
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    def run(self):
        """运行 Worker"""
        self._log("GhostRadio Worker started")
        
        # 获取锁
        if not self._acquire_lock():
            self._log("Another worker is already running, exiting")
            return
        
        try:
            # 读取队列
            queue = self._read_queue()
            
            if not queue:
                self._log("Queue is empty, nothing to do")
                return
            
            self._log(f"Found {len(queue)} items in queue")
            
            # 处理队列中的每个 URL
            results = []
            for item in queue:
                result = self.process_url(item['url'])
                results.append(result)
            
            # 清空队列
            self._clear_queue()
            
            # 统计结果
            success_count = sum(1 for r in results if r['success'])
            fail_count = len(results) - success_count
            
            self._log(f"Processing complete: {success_count} succeeded, {fail_count} failed")
            
            return results
            
        finally:
            self._release_lock()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GhostRadio Worker')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--once', '-o', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    # 加载配置
    from src.config import reload_config
    reload_config(args.config)
    
    # 创建并运行 Worker
    worker = Worker()
    
    if args.once:
        worker.run()
    else:
        # 持续运行模式（由外部调度器调用）
        worker.run()


if __name__ == '__main__':
    main()
