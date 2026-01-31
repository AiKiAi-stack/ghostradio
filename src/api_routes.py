"""
API 路由模块
提供前端交互所需的 REST API
"""

import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JobManager:
    """任务管理器 - 管理生成任务的状态"""
    
    def __init__(self, jobs_dir: str = "logs/jobs"):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Dict[str, Any]] = {}
    
    def create_job(self, url: str, llm_model: str, tts_model: str) -> str:
        """创建新任务"""
        job_id = str(uuid.uuid4())[:8]
        job = {
            'id': job_id,
            'url': url,
            'llm_model': llm_model,
            'tts_model': tts_model,
            'status': 'pending',
            'progress': 0,
            'message': '等待处理',
            'created_at': datetime.now().isoformat(),
            'result': None,
            'error': None
        }
        self._jobs[job_id] = job
        self._save_job(job_id)
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if job_id in self._jobs:
            return self._jobs[job_id]
        
        # 尝试从文件加载
        job_file = self.jobs_dir / f"{job_id}.json"
        if job_file.exists():
            with open(job_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def update_job(self, job_id: str, **kwargs) -> None:
        """更新任务状态"""
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)
            self._jobs[job_id]['updated_at'] = datetime.now().isoformat()
            self._save_job(job_id)
    
    def _save_job(self, job_id: str) -> None:
        """保存任务到文件"""
        if job_id in self._jobs:
            job_file = self.jobs_dir / f"{job_id}.json"
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(self._jobs[job_id], f, ensure_ascii=False, indent=2)


# 全局任务管理器
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """获取任务管理器实例"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def handle_api_request(handler, path: str, method: str) -> tuple:
    """
    处理 API 请求
    
    Args:
        handler: HTTP 请求处理器
        path: 请求路径
        method: HTTP 方法
        
    Returns:
        (status_code, response_data, content_type)
    """
    job_manager = get_job_manager()
    
    # POST /api/generate - 创建生成任务
    if path == '/api/generate' and method == 'POST':
        return handle_generate(handler, job_manager)
    
    # GET /api/progress/{job_id} - 获取任务进度
    if path.startswith('/api/progress/') and method == 'GET':
        job_id = path.split('/')[-1]
        return handle_progress(job_id, job_manager)
    
    # GET /api/episodes - 获取节目列表
    if path == '/api/episodes' and method == 'GET':
        return handle_episodes()
    
    return 404, {'error': 'Not found'}, 'application/json'


def handle_generate(handler, job_manager: JobManager) -> tuple:
    """处理生成任务请求"""
    try:
        content_length = int(handler.headers.get('Content-Length', 0))
        if content_length == 0:
            return 400, {'error': 'Empty request body'}, 'application/json'
        
        post_data = handler.rfile.read(content_length).decode('utf-8')
        data = json.loads(post_data)
        
        url = data.get('url', '').strip()
        llm_model = data.get('llm_model', 'nvidia')
        tts_model = data.get('tts_model', 'volcengine')
        
        if not url:
            return 400, {'error': 'URL is required'}, 'application/json'
        
        # 创建任务
        job_id = job_manager.create_job(url, llm_model, tts_model)
        
        # 将任务添加到队列（写入 queue.txt）
        queue_file = Path("queue.txt")
        timestamp = datetime.now().isoformat()
        with open(queue_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp}|{url}|{job_id}\n")
        
        return 200, {
            'success': True,
            'job_id': job_id,
            'message': 'Task created successfully'
        }, 'application/json'
        
    except json.JSONDecodeError:
        return 400, {'error': 'Invalid JSON'}, 'application/json'
    except Exception as e:
        return 500, {'error': str(e)}, 'application/json'


def handle_progress(job_id: str, job_manager: JobManager) -> tuple:
    """处理进度查询请求"""
    job = job_manager.get_job(job_id)
    
    if not job:
        return 404, {'error': 'Job not found'}, 'application/json'
    
    # 模拟进度更新（实际应该由 worker 更新）
    if job['status'] == 'pending':
        # 检查队列文件，看是否已被处理
        queue_file = Path("queue.txt")
        if queue_file.exists():
            with open(queue_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 如果 job_id 不在队列中，说明正在处理或已完成
                if job_id not in content:
                    # 检查 episodes 目录是否有结果
                    episodes_dir = Path("episodes")
                    if episodes_dir.exists():
                        # 查找包含 job_id 的文件
                        for file in episodes_dir.glob("*.mp3"):
                            if job_id in file.name:
                                job_manager.update_job(
                                    job_id,
                                    status='completed',
                                    progress=100,
                                    message='生成完成',
                                    result={
                                        'audio_url': f'episodes/{file.name}',
                                        'title': file.stem
                                    }
                                )
                                job = job_manager.get_job(job_id)
                                break
                        else:
                            # 正在处理中
                            job_manager.update_job(
                                job_id,
                                status='processing',
                                progress=50,
                                message='正在生成音频...'
                            )
                            job = job_manager.get_job(job_id)
    
    return 200, {
        'job_id': job_id,
        'status': job['status'],
        'progress': job.get('progress', 0),
        'status_message': job.get('message', ''),
        'result': job.get('result'),
        'error': job.get('error')
    }, 'application/json'


def handle_episodes() -> tuple:
    """处理节目列表请求"""
    try:
        episodes_dir = Path("episodes")
        episodes = []
        
        if episodes_dir.exists():
            for file in sorted(episodes_dir.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True):
                stat = file.stat()
                size_mb = stat.st_size / (1024 * 1024)
                
                episodes.append({
                    'id': file.stem,
                    'title': file.stem.replace('_', ' ').title(),
                    'audio_file': f'episodes/{file.name}',
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size_mb': round(size_mb, 2),
                    'duration': 0  # 暂时无法获取时长
                })
        
        return 200, episodes, 'application/json'
        
    except Exception as e:
        return 500, {'error': str(e)}, 'application/json'
