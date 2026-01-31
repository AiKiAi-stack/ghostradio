"""
API 路由模块
提供前端交互所需的 REST API

改进：
- 添加详细的日志记录
- 支持任务取消
- 添加超时检测
- 更细粒度的进度更新
"""

import json
import uuid
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from logger import get_logger

logger = get_logger("api")


class JobStatus:
    """任务状态常量"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    FETCHING = "fetching"  # 获取内容
    LLM_PROCESSING = "llm_processing"  # LLM处理
    TTS_GENERATING = "tts_generating"  # TTS生成
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class Job:
    """任务对象"""
    
    def __init__(
        self,
        job_id: str,
        url: str,
        llm_model: str,
        tts_model: str
    ):
        self.id = job_id
        self.url = url
        self.llm_model = llm_model
        self.tts_model = tts_model
        self.status = JobStatus.PENDING
        self.progress = 0
        self.message = "等待处理"
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.error_details: Optional[Dict[str, Any]] = None
        self.cancelled = False
        self.stage_start_time: Optional[datetime] = None
        self.stage = ""
        
        # 详细进度
        self.stages: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "url": self.url,
            "llm_model": self.llm_model,
            "tts_model": self.tts_model,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "error_details": self.error_details,
            "cancelled": self.cancelled,
            "stage": self.stage,
            "stages": self.stages
        }
    
    def update(
        self,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        stage: Optional[str] = None
    ) -> None:
        """更新任务状态"""
        if status:
            self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        if stage:
            self.stage = stage
            self.stage_start_time = datetime.now()
        
        self.updated_at = datetime.now()
        
        # 记录阶段
        if stage:
            self.stages.append({
                "stage": stage,
                "progress": progress or self.progress,
                "timestamp": self.updated_at.isoformat()
            })
    
    def set_error(
        self,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置错误信息"""
        self.status = JobStatus.FAILED
        self.error = error
        self.error_details = details
        self.completed_at = datetime.now()
        self.message = f"失败: {error}"
    
    def set_result(self, result: Dict[str, Any]) -> None:
        """设置结果"""
        self.status = JobStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
        self.progress = 100
        self.message = "生成完成"
    
    def cancel(self, reason: str = "用户取消") -> None:
        """取消任务"""
        self.cancelled = True
        self.status = JobStatus.CANCELLED
        self.message = f"已取消: {reason}"
        self.completed_at = datetime.now()
    
    def get_elapsed_time(self) -> float:
        """获取已运行时间（秒）"""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_stage_elapsed_time(self) -> Optional[float]:
        """获取当前阶段运行时间（秒）"""
        if self.stage_start_time:
            return (datetime.now() - self.stage_start_time).total_seconds()
        return None


class JobManager:
    """任务管理器 - 管理生成任务的状态"""
    
    # 超时配置（秒）
    STAGE_TIMEOUTS = {
        "fetching": 60,  # 获取内容最多60秒
        "llm_processing": 300,  # LLM处理最多5分钟
        "tts_generating": 600,  # TTS生成最多10分钟
    }
    
    def __init__(self, jobs_dir: str = "logs/jobs"):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        
        # 加载现有任务
        self._load_existing_jobs()
    
    def _load_existing_jobs(self) -> None:
        """加载已存在的任务"""
        try:
            for job_file in self.jobs_dir.glob("*.json"):
                try:
                    with open(job_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 这里可以恢复任务对象
                except Exception as e:
                    logger.warning(f"Failed to load job file {job_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load existing jobs: {e}")
    
    def create_job(
        self,
        url: str,
        llm_model: str,
        tts_model: str
    ) -> Job:
        """创建新任务"""
        with self._lock:
            job_id = str(uuid.uuid4())[:8]
            job = Job(job_id, url, llm_model, tts_model)
            self._jobs[job_id] = job
            self._save_job(job)
            
            logger.log_job_start(job_id, url, llm_model, tts_model)
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        with self._lock:
            # 先查内存
            if job_id in self._jobs:
                return self._jobs[job_id]
            
            # 再查文件
            job_file = self.jobs_dir / f"{job_id}.json"
            if job_file.exists():
                try:
                    with open(job_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        job = Job(
                            data['id'],
                            data['url'],
                            data['llm_model'],
                            data['tts_model']
                        )
                        # 恢复状态
                        job.status = data.get('status', JobStatus.PENDING)
                        job.progress = data.get('progress', 0)
                        job.message = data.get('message', '')
                        job.error = data.get('error')
                        job.error_details = data.get('error_details')
                        job.result = data.get('result')
                        job.cancelled = data.get('cancelled', False)
                        self._jobs[job_id] = job
                        return job
                except Exception as e:
                    logger.error(f"Failed to load job {job_id}: {e}")
            
            return None
    
    def update_job(self, job_id: str, **kwargs) -> None:
        """更新任务"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(**kwargs)
                self._save_job(job)
                
                # 记录进度
                if 'progress' in kwargs or 'stage' in kwargs:
                    logger.log_job_progress(
                        job_id,
                        job.stage,
                        job.progress,
                        job.message,
                        {"status": job.status}
                    )
    
    def set_job_error(
        self,
        job_id: str,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置任务错误"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.set_error(error, details)
                self._save_job(job)
                logger.log_job_error(job_id, job.stage, Exception(error), details)
    
    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> None:
        """设置任务结果"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.set_result(result)
                self._save_job(job)
                duration = job.get_elapsed_time()
                logger.log_job_complete(
                    job_id,
                    duration,
                    result.get('audio_url', ''),
                    result.get('tokens_used', 0)
                )
    
    def cancel_job(self, job_id: str, reason: str = "用户取消") -> bool:
        """取消任务"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                # 只能取消正在进行的任务
                if job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.PROCESSING]:
                    job.cancel(reason)
                    self._save_job(job)
                    logger.log_job_cancelled(job_id, reason)
                    return True
            return False
    
    def check_timeout(self, job_id: str) -> Optional[str]:
        """检查任务是否超时，返回警告信息"""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        stage = job.stage
        if stage in self.STAGE_TIMEOUTS:
            elapsed = job.get_stage_elapsed_time()
            if elapsed:
                timeout = self.STAGE_TIMEOUTS[stage]
                if elapsed > timeout:
                    warning = f"阶段 '{stage}' 已运行 {elapsed:.0f} 秒，超过预期 {timeout} 秒"
                    logger.log_timeout(job_id, stage, elapsed, timeout)
                    return warning
                elif elapsed > timeout * 0.8:  # 80% 阈值
                    return f"阶段 '{stage}' 即将超时 ({elapsed:.0f}/{timeout} 秒)"
        
        return None
    
    def _save_job(self, job: Job) -> None:
        """保存任务到文件"""
        try:
            job_file = self.jobs_dir / f"{job.id}.json"
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {e}")
    
    def get_all_jobs(self) -> List[Job]:
        """获取所有任务"""
        with self._lock:
            return list(self._jobs.values())


# 全局任务管理器
_job_manager: Optional[JobManager] = None
_job_manager_lock = threading.Lock()


def get_job_manager() -> JobManager:
    """获取任务管理器实例（线程安全）"""
    global _job_manager
    with _job_manager_lock:
        if _job_manager is None:
            _job_manager = JobManager()
        return _job_manager


def handle_api_request(
    handler,
    path: str,
    method: str
) -> tuple:
    """
    处理 API 请求
    
    Returns:
        (status_code, response_data, content_type)
    """
    job_manager = get_job_manager()
    start_time = time.time()
    
    try:
        # POST /api/generate - 创建生成任务
        if path == '/api/generate' and method == 'POST':
            result = handle_generate(handler, job_manager)
        
        # GET /api/progress/{job_id} - 获取任务进度
        elif path.startswith('/api/progress/') and method == 'GET':
            job_id = path.split('/')[-1]
            result = handle_progress(job_id, job_manager)
        
        # POST /api/cancel/{job_id} - 取消任务
        elif path.startswith('/api/cancel/') and method == 'POST':
            job_id = path.split('/')[-1]
            result = handle_cancel(job_id, job_manager)
        
        # GET /api/episodes - 获取节目列表
        elif path == '/api/episodes' and method == 'GET':
            result = handle_episodes()
        
        else:
            result = (404, {'error': 'Not found'}, 'application/json')
        
        # 记录API请求（排除频繁的进度查询）
        if not path.startswith('/api/progress/'):
            duration_ms = (time.time() - start_time) * 1000
            logger.log_api_request(method, path, result[0], duration_ms)
        
        return result
        
    except Exception as e:
        logger.error(f"API request failed: {method} {path}", error=e)
        return 500, {'error': str(e)}, 'application/json'


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
        
        # 记录完整的请求信息
        logger.info(
            "API generate request received",
            context={
                "url": url,
                "llm_model": llm_model,
                "tts_model": tts_model,
                "url_length": len(url),
                "request_data": data
            }
        )
        
        # 创建任务
        job = job_manager.create_job(url, llm_model, tts_model)
        
        # 将任务添加到队列（写入 queue.txt）
        queue_file = Path("queue.txt")
        timestamp = datetime.now().isoformat()
        with open(queue_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp}|{url}|{job.id}\n")
        
        # 更新任务状态为已排队
        job_manager.update_job(
            job.id,
            status=JobStatus.QUEUED,
            progress=5,
            message="已加入处理队列"
        )
        
        return 200, {
            'success': True,
            'job_id': job.id,
            'message': 'Task created successfully',
            'status': job.status,
            'progress': job.progress
        }, 'application/json'
        
    except json.JSONDecodeError:
        return 400, {'error': 'Invalid JSON'}, 'application/json'
    except Exception as e:
        logger.error("Failed to create job", error=e)
        return 500, {'error': str(e)}, 'application/json'


def handle_progress(job_id: str, job_manager: JobManager) -> tuple:
    """处理进度查询请求"""
    job = job_manager.get_job(job_id)
    
    if not job:
        return 404, {'error': 'Job not found'}, 'application/json'
    
    # 检查超时
    timeout_warning = job_manager.check_timeout(job_id)
    
    # 模拟进度更新（实际应该由 worker 更新）
    if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
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
                                job_manager.set_job_result(
                                    job_id,
                                    {
                                        'audio_url': f'episodes/{file.name}',
                                        'title': file.stem
                                    }
                                )
                                job = job_manager.get_job(job_id)
                                break
                        else:
                            # 正在处理中
                            if job.status == JobStatus.QUEUED:
                                job_manager.update_job(
                                    job_id,
                                    status=JobStatus.PROCESSING,
                                    progress=10,
                                    message="开始处理...",
                                    stage="fetching"
                                )
                                job = job_manager.get_job(job_id)
    
    response = {
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'stage': job.stage,
        'elapsed_time': job.get_elapsed_time(),
        'result': job.result,
        'error': job.error,
        'error_details': job.error_details,
        'cancelled': job.cancelled
    }
    
    if timeout_warning:
        response['timeout_warning'] = timeout_warning
    
    return 200, response, 'application/json'


def handle_cancel(job_id: str, job_manager: JobManager) -> tuple:
    """处理取消任务请求"""
    success = job_manager.cancel_job(job_id)
    
    if success:
        return 200, {
            'success': True,
            'message': 'Job cancelled successfully',
            'job_id': job_id
        }, 'application/json'
    else:
        job = job_manager.get_job(job_id)
        if not job:
            return 404, {'error': 'Job not found'}, 'application/json'
        else:
            return 400, {
                'error': 'Cannot cancel job',
                'status': job.status,
                'message': f"当前状态为 '{job.status}'，无法取消"
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
        logger.error("Failed to load episodes", error=e)
        return 500, {'error': str(e)}, 'application/json'
