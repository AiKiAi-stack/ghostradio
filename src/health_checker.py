"""
Health Check Module
Provides system and worker health status monitoring
"""

import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


class HealthChecker:
    """System health monitoring"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})
        self.start_time = time.time()

    def get_worker_status(self) -> Dict[str, Any]:
        """Check worker process status"""
        logs_dir = self.paths.get("logs_dir", "logs")
        lock_file = os.path.join(logs_dir, "worker.lock")

        is_running = os.path.exists(lock_file)

        worker_log = os.path.join(logs_dir, "worker.log")
        last_run = None
        last_run_status = "unknown"

        if os.path.exists(worker_log):
            try:
                stat = os.stat(worker_log)
                last_run = datetime.fromtimestamp(stat.st_mtime).isoformat()

                with open(worker_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if "complete" in last_line.lower():
                            last_run_status = "success"
                        elif "error" in last_line.lower():
                            last_run_status = "error"
            except Exception:
                pass

        return {
            "status": "running" if is_running else "idle",
            "is_locked": is_running,
            "last_run": last_run,
            "last_run_status": last_run_status,
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """Check job queue status"""
        from src.job_queue import JobQueue

        try:
            job_queue = JobQueue()
            pending_jobs = job_queue.get_pending_jobs()

            queue_dir = Path("logs/queue")
            processed_dir = Path("logs/processed")

            pending_count = len(pending_jobs)
            processed_count = (
                len(list(processed_dir.glob("*.json"))) if processed_dir.exists() else 0
            )

            return {
                "pending": pending_count,
                "processed_total": processed_count,
                "oldest_pending": (
                    pending_jobs[0].get("_queue_file", "").split("/")[-1]
                    if pending_jobs
                    else None
                ),
            }
        except Exception as e:
            return {"error": str(e), "pending": 0, "processed_total": 0}

    def get_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "memory": {
                    "total_mb": round(memory.total / (1024 * 1024), 2),
                    "used_mb": round(memory.used / (1024 * 1024), 2),
                    "available_mb": round(memory.available / (1024 * 1024), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                    "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                    "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                    "percent": disk.percent,
                },
                "cpu_percent": psutil.cpu_percent(interval=0.1),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_episodes_status(self) -> Dict[str, Any]:
        """Check episodes metadata status"""
        try:
            from src.episode_metadata import get_metadata_manager

            metadata_manager = get_metadata_manager()
            episodes = metadata_manager.get_all_episodes()

            total_size_mb = sum(ep.get("size_mb", 0) for ep in episodes)
            total_duration = sum(ep.get("duration_seconds", 0) for ep in episodes)

            return {
                "total_episodes": len(episodes),
                "total_size_mb": round(total_size_mb, 2),
                "total_duration_hours": round(total_duration / 3600, 2),
                "latest_episode": (episodes[0].get("id") if episodes else None),
            }
        except Exception as e:
            return {"error": str(e), "total_episodes": 0}

    def get_full_health(self) -> Dict[str, Any]:
        """Get complete health status"""
        uptime_seconds = time.time() - self.start_time

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(uptime_seconds, 2),
            "worker": self.get_worker_status(),
            "queue": self.get_queue_status(),
            "episodes": self.get_episodes_status(),
            "system": self.get_system_resources(),
        }


_health_checker_instance: Optional[HealthChecker] = None


def get_health_checker(config: Optional[Dict[str, Any]] = None) -> HealthChecker:
    """Get singleton HealthChecker instance"""
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = HealthChecker(config)
    return _health_checker_instance
