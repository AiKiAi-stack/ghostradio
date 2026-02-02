"""
Atomic Job Queue Manager
Replaces the monolithic queue.txt with individual JSON files
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class JobQueue:
    """Atomic job queue using individual JSON files"""

    def __init__(
        self,
        queue_dir: str = "logs/queue",
        processed_dir: str = "logs/processed",
        failed_dir: str = "logs/failed",
    ):
        self.queue_dir = Path(queue_dir)
        self.processed_dir = Path(processed_dir)
        self.failed_dir = Path(failed_dir)

        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def add_job(
        self,
        url: str,
        job_id: str,
        llm_model: str = "nvidia",
        tts_model: str = "volcengine",
        need_summary: bool = True,
        tts_config: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        user_id: str = "default",
    ) -> str:
        """Add a new job to the queue"""
        timestamp = datetime.now().isoformat()
        queue_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        job_data = {
            "queue_id": queue_id,
            "job_id": job_id,
            "user_id": user_id,
            "url": url,
            "llm_model": llm_model,
            "tts_model": tts_model,
            "need_summary": need_summary,
            "tts_config": tts_config or {},
            "created_at": timestamp,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "last_attempt": timestamp if retry_count > 0 else None,
        }

        queue_file = self.queue_dir / f"{queue_id}.json"
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)

        return queue_id

    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """Get all pending jobs from queue"""
        jobs = []
        for queue_file in sorted(self.queue_dir.glob("*.json")):
            try:
                with open(queue_file, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    job_data["_queue_file"] = str(queue_file)
                    jobs.append(job_data)
            except Exception as e:
                print(f"Error reading queue file {queue_file}: {e}")
        return jobs

    def mark_processed(self, queue_file: str) -> bool:
        """Move processed job file to processed directory"""
        try:
            source = Path(queue_file)
            if not source.exists():
                return False

            dest = self.processed_dir / source.name
            source.rename(dest)
            return True
        except Exception as e:
            print(f"Error moving queue file {queue_file}: {e}")
            return False

    def mark_failed(self, queue_file: str, error: str) -> bool:
        """Move failed job to failed directory with error info"""
        try:
            source = Path(queue_file)
            if not source.exists():
                return False

            with open(source, "r", encoding="utf-8") as f:
                job_data = json.load(f)

            job_data["failed_at"] = datetime.now().isoformat()
            job_data["error"] = error

            dest = self.failed_dir / source.name
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(job_data, f, ensure_ascii=False, indent=2)

            source.unlink()
            return True
        except Exception as e:
            print(f"Error marking job as failed {queue_file}: {e}")
            return False

    def retry_job(self, queue_file: str) -> Optional[str]:
        """Retry a failed job with incremented retry count"""
        try:
            source = Path(queue_file)
            with open(source, "r", encoding="utf-8") as f:
                job_data = json.load(f)

            retry_count = job_data.get("retry_count", 0) + 1
            max_retries = job_data.get("max_retries", 3)

            if retry_count > max_retries:
                return None

            new_queue_id = self.add_job(
                url=job_data["url"],
                job_id=job_data["job_id"],
                user_id=job_data.get("user_id", "default"),
                llm_model=job_data.get("llm_model", "nvidia"),
                tts_model=job_data.get("tts_model", "volcengine"),
                need_summary=job_data.get("need_summary", True),
                tts_config=job_data.get("tts_config", {}),
                retry_count=retry_count,
                max_retries=max_retries,
            )

            source.unlink()
            return new_queue_id
        except Exception as e:
            print(f"Error retrying job {queue_file}: {e}")
            return None

    def clear_old_processed(self, keep_days: int = 7):
        """Clean up old processed job files"""
        cutoff_time = datetime.now().timestamp() - (keep_days * 86400)
        for processed_file in self.processed_dir.glob("*.json"):
            if processed_file.stat().st_mtime < cutoff_time:
                try:
                    processed_file.unlink()
                except Exception as e:
                    print(f"Error deleting old processed file {processed_file}: {e}")

    @classmethod
    def migrate_from_old_queue(cls, old_queue_file: str = "queue.txt") -> int:
        """Migrate from old queue.txt format to new atomic queue"""
        if not os.path.exists(old_queue_file):
            return 0

        queue = cls()
        migrated_count = 0

        try:
            with open(old_queue_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) >= 2:
                    url = parts[1]
                    job_id = parts[2] if len(parts) >= 3 else str(uuid.uuid4())[:8]
                    queue.add_job(url, job_id)
                    migrated_count += 1

            os.rename(old_queue_file, f"{old_queue_file}.backup")
            print(f"Migrated {migrated_count} jobs from old queue")

        except Exception as e:
            print(f"Error migrating old queue: {e}")

        return migrated_count
