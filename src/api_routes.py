"""
API 路由模块
提供前端交互所需的 REST API
"""

import json
import uuid
import os
import sys
import time
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.job_models import JobStatus, Job
from src.logger import get_logger
from src.job_queue import JobQueue
from src.episode_metadata import get_metadata_manager, EpisodeMetadataManager
from src.qrcode_utils import generate_feed_qr_payload

logger = get_logger("api")
job_queue = JobQueue()

_worker_lock = threading.Lock()
_worker_running = False


def _trigger_worker_async():
    """在后台线程中启动 Worker 进程"""
    global _worker_running
    with _worker_lock:
        if _worker_running:
            logger.info("Worker already running, skip trigger")
            return
        _worker_running = True

    def run_worker():
        global _worker_running
        try:
            project_root = Path(__file__).parent.parent
            worker_script = project_root / "src" / "worker.py"
            cmd = [sys.executable, str(worker_script), "--once"]
            logger.info(f"Triggering worker: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(project_root)
            )
            if result.returncode == 0:
                logger.info("Worker completed successfully")
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"Worker failed: {error_msg}")
                _mark_pending_jobs_failed(error_msg)
        except Exception as e:
            logger.error(f"Worker trigger error: {e}")
            _mark_pending_jobs_failed(str(e))
        finally:
            with _worker_lock:
                _worker_running = False

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()


def _mark_pending_jobs_failed(error: str):
    """Worker 崩溃时标记所有待处理任务为失败"""
    try:
        job_manager = get_job_manager()
        for job in job_manager.get_all_jobs():
            if job.status in [
                JobStatus.PENDING,
                JobStatus.QUEUED,
                JobStatus.PROCESSING,
            ]:
                job_manager.set_job_error(job.id, f"Worker crashed: {error[:200]}")
                logger.info(f"Marked job {job.id} as failed due to worker crash")
    except Exception as e:
        logger.error(f"Failed to mark jobs as failed: {e}")


class JobManager:
    """任务管理器 - 管理生成任务的状态"""

    # 超时配置（秒）
    STAGE_TIMEOUTS = {
        "fetching": 60,
        "llm_processing": 300,
        "tts_generating": 600,
    }

    def __init__(self, jobs_dir: str = "logs/jobs"):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()  # RLock to allow reentrant locking
        self._load_existing_jobs()

    def _load_existing_jobs(self) -> None:
        """加载已存在的任务"""
        try:
            for job_file in self.jobs_dir.glob("*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load job file {job_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load existing jobs: {e}")

    def create_job(
        self,
        url: str,
        llm_model: str,
        tts_model: str,
        need_summary: bool = True,
        tts_config: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Job:
        """创建新任务"""
        with self._lock:
            job_id = str(uuid.uuid4())[:8]
            job = Job(
                job_id,
                url,
                llm_model,
                tts_model,
                need_summary,
                tts_config,
                user_id=user_id,
            )
            self._jobs[job_id] = job
            self._save_job(job)
            logger.log_job_start(job_id, url, llm_model, tts_model, need_summary)
            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        with self._lock:
            job_file = self.jobs_dir / f"{job_id}.json"
            if job_file.exists():
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        job = Job.from_dict(data)
                        self._jobs[job_id] = job
                        return job
                except Exception as e:
                    logger.error(f"Failed to load job {job_id}: {e}")
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs) -> None:
        """更新任务"""
        with self._lock:
            job = self.get_job(job_id)
            if job:
                job.update(**kwargs)
                self._save_job(job)
                if "progress" in kwargs or "stage" in kwargs:
                    logger.log_job_progress(
                        job_id,
                        job.stage,
                        job.progress,
                        job.message,
                        {"status": job.status},
                    )

    def set_job_error(
        self, job_id: str, error: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置任务错误"""
        with self._lock:
            job = self.get_job(job_id)
            if job:
                job.set_error(error, details)
                self._save_job(job)
                logger.log_job_error(job_id, job.stage, Exception(error), details)

    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> None:
        """设置任务结果"""
        with self._lock:
            job = self.get_job(job_id)
            if job:
                job.set_result(result)
                self._save_job(job)
                duration = job.get_elapsed_time()
                logger.log_job_complete(
                    job_id,
                    duration,
                    result.get("audio_url", ""),
                    result.get("tokens_used", 0),
                )

    def cancel_job(self, job_id: str, reason: str = "用户取消") -> bool:
        """取消任务"""
        with self._lock:
            job = self.get_job(job_id)
            if job:
                if job.status in [
                    JobStatus.PENDING,
                    JobStatus.QUEUED,
                    JobStatus.PROCESSING,
                    JobStatus.FETCHING,
                    JobStatus.LLM_PROCESSING,
                    JobStatus.TTS_GENERATING,
                ]:
                    job.cancel(reason)
                    self._save_job(job)
                    logger.log_job_cancelled(job_id, reason)
                    return True
            return False

    def check_timeout(self, job_id: str) -> Optional[str]:
        """检查任务是否超时"""
        job = self.get_job(job_id)
        if not job:
            return None
        stage = job.stage
        if stage in self.STAGE_TIMEOUTS:
            elapsed = job.get_stage_elapsed_time()
            if elapsed:
                timeout = self.STAGE_TIMEOUTS[stage]
                if elapsed > timeout:
                    logger.log_timeout(job_id, stage, elapsed, timeout)
                    return (
                        f"阶段 '{stage}' 已运行 {elapsed:.0f} 秒，超过预期 {timeout} 秒"
                    )
        return None

    def _save_job(self, job: Job) -> None:
        """保存任务到文件"""
        try:
            job_file = self.jobs_dir / f"{job.id}.json"
            with open(job_file, "w", encoding="utf-8") as f:
                json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {e}")

    def get_all_jobs(self) -> List[Job]:
        """获取所有任务"""
        all_jobs = []
        for job_file in self.jobs_dir.glob("*.json"):
            job = self.get_job(job_file.stem)
            if job:
                all_jobs.append(job)
        return all_jobs


_job_manager: Optional[JobManager] = None
_job_manager_lock = threading.Lock()


def get_job_manager() -> JobManager:
    """获取任务管理器实例"""
    global _job_manager
    with _job_manager_lock:
        if _job_manager is None:
            _job_manager = JobManager()
        return _job_manager


def handle_api_request(handler, path: str, method: str) -> tuple:
    """处理 API 请求"""
    job_manager = get_job_manager()
    start_time = time.time()
    try:
        if path.startswith("/api/generate") and method == "POST":
            result = handle_generate(handler, job_manager)
        elif path.startswith("/api/progress/") and method == "GET":
            job_id = path.split("/")[-1]
            result = handle_progress(job_id, job_manager)
        elif path.startswith("/api/cancel/") and method == "POST":
            job_id = path.split("/")[-1]
            result = handle_cancel(job_id, job_manager)
        elif path.startswith("/api/episodes") and method == "GET":
            user_id = "default"
            if "?" in path:
                from urllib.parse import urlparse, parse_qs

                query = parse_qs(urlparse(path).query)
                user_id = query.get("user_id", ["default"])[0]
            result = handle_episodes(user_id)
        elif path.startswith("/api/qrcode") and method == "GET":
            from urllib.parse import urlparse, parse_qs

            query = parse_qs(urlparse(path).query)
            user_id = query.get("user_id", ["default"])[0]
            result = handle_qrcode(user_id, handler)
        elif path == "/health" and method == "GET":
            result = handle_health()
        elif path == "/health/worker" and method == "GET":
            result = handle_health_worker()
        elif path == "/health/system" and method == "GET":
            result = handle_health_system()
        elif path == "/health/full" and method == "GET":
            result = handle_health_full()
        else:
            result = (404, {"error": "Not found"}, "application/json")
        if not path.startswith("/api/progress/"):
            duration_ms = (time.time() - start_time) * 1000
            logger.log_api_request(method, path, result[0], duration_ms)
        return result
    except Exception as e:
        logger.error(f"API request failed: {method} {path}", error=e)
        return 500, {"error": str(e)}, "application/json"


def handle_generate(handler, job_manager: JobManager) -> tuple:
    """处理生成任务请求"""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        if content_length == 0:
            return 400, {"error": "Empty request body"}, "application/json"
        post_data = handler.rfile.read(content_length).decode("utf-8")
        data = json.loads(post_data)
        url = data.get("url", "").strip()
        user_id = data.get("user_id", "default").strip()
        prompt_text = data.get("prompt_text", "").strip()
        nlp_texts = data.get("nlp_texts")
        llm_model = data.get("llm_model", "nvidia")
        tts_model = data.get("tts_model", "volcengine")
        need_summary = data.get("need_summary", True)
        tts_config = data.get("tts_config", {})

        metadata_manager = get_metadata_manager(user_id)
        if len(metadata_manager.get_all_episodes()) >= 10:
            logger.info(f"User {user_id} reached limit. Oldest will be removed.")

        safe_tts_config = tts_config.copy()
        if "appid" in safe_tts_config:
            safe_tts_config["appid"] = "********"
        if "token" in safe_tts_config:
            safe_tts_config["token"] = "********"

        logger.info(
            "API generate request received",
            context={
                "url": url,
                "user_id": user_id,
                "prompt_text": prompt_text,
                "llm_model": llm_model,
                "tts_model": tts_model,
            },
        )
        job = job_manager.create_job(
            url or "manual_input",
            llm_model,
            tts_model,
            need_summary,
            tts_config,
            user_id=user_id,
        )
        job_queue.add_job(
            url=url or "manual_input",
            job_id=job.id,
            user_id=user_id,
            llm_model=llm_model,
            tts_model=tts_model,
            need_summary=need_summary,
            tts_config=tts_config,
        )
        job_manager.update_job(
            job.id, status=JobStatus.QUEUED, progress=5, message="已加入处理队列"
        )
        _trigger_worker_async()
        return (200, {"success": True, "job_id": job.id}, "application/json")
    except Exception as e:
        logger.error("Failed to create job", error=e)
        return 500, {"error": str(e)}, "application/json"


def handle_progress(job_id: str, job_manager: JobManager) -> tuple:
    """处理进度查询请求"""
    job = job_manager.get_job(job_id)
    if not job:
        return 404, {"error": "Job not found"}, "application/json"
    timeout_warning = job_manager.check_timeout(job_id)
    response = {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "stage": job.stage,
        "elapsed_time": job.get_elapsed_time(),
        "result": job.result,
        "error": job.error,
        "cancelled": job.cancelled,
    }
    if timeout_warning:
        response["timeout_warning"] = timeout_warning
    return 200, response, "application/json"


def handle_cancel(job_id: str, job_manager: JobManager) -> tuple:
    """处理取消任务请求"""
    success = job_manager.cancel_job(job_id)
    if success:
        return (200, {"success": True, "job_id": job_id}, "application/json")
    else:
        job = job_manager.get_job(job_id)
        if not job:
            return 404, {"error": "Job not found"}, "application/json"
        return (
            400,
            {"error": "Cannot cancel", "status": job.status},
            "application/json",
        )


def handle_episodes(user_id: str = "default") -> tuple:
    """处理节目列表请求"""
    try:
        metadata_manager = get_metadata_manager(user_id)
        EpisodeMetadataManager.migrate_from_filesystem(user_id=user_id)
        episodes = metadata_manager.get_all_episodes()
        formatted = []
        for ep in episodes:
            formatted.append(
                {
                    "id": ep["id"],
                    "title": ep.get("title", ep["id"]),
                    "audio_file": f"episodes/{user_id}/{ep['audio_file']}",
                    "created": ep.get("created_at", ""),
                    "size_mb": ep.get("size_mb", 0),
                    "duration": ep.get("duration_seconds", 0),
                }
            )
        return 200, formatted, "application/json"
    except Exception as e:
        logger.error(f"Failed to load episodes for {user_id}", error=e)
        return 500, {"error": str(e)}, "application/json"


def handle_qrcode(user_id: str, handler) -> tuple:
    """处理二维码生成请求"""
    try:
        from src.config import get_config

        config = get_config()
        host = handler.headers.get(
            "Host", f"localhost:{config.get('server.port', 8080)}"
        )
        protocol = (
            "https" if handler.headers.get("X-Forwarded-Proto") == "https" else "http"
        )
        base_url = f"{protocol}://{host}"
        rss_url = f"{base_url}/episodes/{user_id}/feed.xml"
        payload = generate_feed_qr_payload(rss_url)
        return 200, payload, "application/json"
    except Exception as e:
        logger.error(f"Failed to generate QR for {user_id}", error=e)
        return 500, {"error": str(e)}, "application/json"


def handle_health() -> tuple:
    return (
        200,
        {"status": "ok", "timestamp": datetime.now().isoformat()},
        "application/json",
    )


def handle_health_worker() -> tuple:
    try:
        from src.health_checker import get_health_checker
        from src.config import get_config

        config = get_config()
        health_checker = get_health_checker(config._config)
        return (
            200,
            {
                "status": "ok",
                "worker": health_checker.get_worker_status(),
                "queue": health_checker.get_queue_status(),
            },
            "application/json",
        )
    except Exception as e:
        return 500, {"error": str(e)}, "application/json"


def handle_health_system() -> tuple:
    try:
        from src.health_checker import get_health_checker
        from src.config import get_config

        config = get_config()
        health_checker = get_health_checker(config._config)
        return (
            200,
            {
                "status": "ok",
                "system": health_checker.get_system_resources(),
                "episodes": health_checker.get_episodes_status(),
            },
            "application/json",
        )
    except Exception as e:
        return 500, {"error": str(e)}, "application/json"


def handle_health_full() -> tuple:
    try:
        from src.health_checker import get_health_checker
        from src.config import get_config

        config = get_config()
        health_checker = get_health_checker(config._config)
        return 200, health_checker.get_full_health(), "application/json"
    except Exception as e:
        return 500, {"error": str(e)}, "application/json"
