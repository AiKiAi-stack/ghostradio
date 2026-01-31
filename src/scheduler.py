#!/usr/bin/env python3
"""
GhostRadio Scheduler - 调度脚本
由 crontab 调用，每 5 分钟检查一次队列
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_config


def run_worker(nice_level: int = 19):
    """
    运行 Worker 进程
    
    Args:
        nice_level: CPU 优先级 (19 为最低)
    """
    worker_script = project_root / 'src' / 'worker.py'
    
    if not worker_script.exists():
        print(f"Error: Worker script not found: {worker_script}")
        return False
    
    try:
        # 使用 nice 命令降低优先级
        cmd = ['nice', '-n', str(nice_level), sys.executable, str(worker_script), '--once']
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Worker completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"Worker failed with code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error running worker: {e}")
        return False


def check_queue() -> bool:
    """检查队列是否有内容"""
    try:
        config = get_config()
        paths = config.get_paths_config()
        queue_file = paths['queue_file']
        
        if not os.path.exists(queue_file):
            return False
        
        with open(queue_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        return len(content) > 0
        
    except Exception as e:
        print(f"Error checking queue: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GhostRadio Scheduler')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--force', '-f', action='store_true', help='Force run even if queue is empty')
    parser.add_argument('--nice', '-n', type=int, default=19, help='Nice level (CPU priority)')
    
    args = parser.parse_args()
    
    # 加载配置
    from src.config import reload_config
    reload_config(args.config)
    
    print(f"GhostRadio Scheduler started at {__import__('datetime').datetime.now()}")
    
    # 检查队列
    if not args.force:
        if not check_queue():
            print("Queue is empty, skipping")
            return
        print("Queue has items, starting worker...")
    else:
        print("Force mode enabled, starting worker...")
    
    # 运行 Worker
    success = run_worker(args.nice)
    
    if success:
        print("Scheduler completed successfully")
    else:
        print("Scheduler completed with errors")
        sys.exit(1)


if __name__ == '__main__':
    main()
