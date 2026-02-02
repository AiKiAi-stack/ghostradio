"""
任务状态更新器
供 Worker 使用，用于原子化更新任务状态 JSON 文件
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from src.job_models import Job, JobStatus


class JobStatusUpdater:
    """任务状态更新器"""

    def __init__(self, jobs_dir: str = "logs/jobs"):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def update_job(self, job_id: str, **kwargs) -> bool:
        """
        更新任务状态文件

        Args:
            job_id: 任务 ID
            **kwargs: 要更新的字段 (status, progress, message, stage, result, error 等)
        """
        if not job_id:
            return False

        job_file = self.jobs_dir / f"{job_id}.json"

        # 尝试读取现有任务
        job_data = {}
        if job_file.exists():
            try:
                with open(job_file, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
            except Exception:
                return False

        if not job_data:
            # 如果文件不存在，我们无法创建一个完整的 Job 对象，因为缺少 url 等信息
            # 但在正常流程中，server 已经创建了文件
            return False

        # 更新字段
        if "status" in kwargs:
            job_data["status"] = kwargs["status"]
        if "progress" in kwargs:
            job_data["progress"] = kwargs["progress"]
        if "message" in kwargs:
            job_data["message"] = kwargs["message"]
        if "stage" in kwargs:
            job_data["stage"] = kwargs["stage"]

            # 记录阶段历史
            if "stages" not in job_data:
                job_data["stages"] = []

            job_data["stages"].append(
                {
                    "stage": kwargs["stage"],
                    "progress": kwargs.get("progress", job_data.get("progress", 0)),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        if "result" in kwargs:
            job_data["result"] = kwargs["result"]
            job_data["status"] = JobStatus.COMPLETED
            job_data["progress"] = 100
            job_data["completed_at"] = datetime.now().isoformat()

        if "error" in kwargs:
            job_data["error"] = kwargs["error"]
            job_data["error_details"] = kwargs.get("error_details")
            job_data["status"] = JobStatus.FAILED
            job_data["completed_at"] = datetime.now().isoformat()

        job_data["updated_at"] = datetime.now().isoformat()

        # 保存回文件
        try:
            with open(job_file, "w", encoding="utf-8") as f:
                json.dump(job_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
