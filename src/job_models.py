"""
任务模型定义
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


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
        tts_model: str,
        need_summary: bool = True,
        tts_config: Optional[Dict[str, Any]] = None,
    ):
        self.id = job_id
        self.url = url
        self.llm_model = llm_model
        self.tts_model = tts_model
        self.need_summary = need_summary
        self.tts_config = tts_config or {}
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
        self.stages: List[Dict[str, Any]] = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """从字典创建对象"""
        job = cls(
            job_id=data["id"],
            url=data["url"],
            llm_model=data.get("llm_model", "nvidia"),
            tts_model=data.get("tts_model", "volcengine"),
            need_summary=data.get("need_summary", True),
            tts_config=data.get("tts_config", {}),
        )
        job.status = data.get("status", JobStatus.PENDING)
        job.progress = data.get("progress", 0)
        job.message = data.get("message", "")
        job.error = data.get("error")
        job.error_details = data.get("error_details")
        job.result = data.get("result")
        job.cancelled = data.get("cancelled", False)
        job.stage = data.get("stage", "")
        job.stages = data.get("stages", [])

        if data.get("created_at"):
            job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            job.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])

        return job

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "url": self.url,
            "llm_model": self.llm_model,
            "tts_model": self.tts_model,
            "tts_config": self.tts_config,
            "need_summary": self.need_summary,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": self.result,
            "error": self.error,
            "error_details": self.error_details,
            "cancelled": self.cancelled,
            "stage": self.stage,
            "stages": self.stages,
        }

    def update(
        self,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        stage: Optional[str] = None,
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

        if stage:
            self.stages.append(
                {
                    "stage": stage,
                    "progress": progress or self.progress,
                    "timestamp": self.updated_at.isoformat(),
                }
            )

    def set_error(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """设置错误信息"""
        self.status = JobStatus.FAILED
        self.error = error
        self.error_details = details
        self.completed_at = datetime.now()
        self.message = f"失败: {error}"

    def set_result(self, result: Dict[str, Any]) -> None:
        """设置成功结果"""
        self.status = JobStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
        self.progress = 100
        self.message = "处理完成"

    def cancel(self, reason: str = "用户取消") -> None:
        """取消任务"""
        self.status = JobStatus.CANCELLED
        self.cancelled = True
        self.message = f"已取消: {reason}"
        self.completed_at = datetime.now()

    def get_elapsed_time(self) -> float:
        """获取总耗时（秒）"""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.created_at).total_seconds()

    def get_stage_elapsed_time(self) -> Optional[float]:
        """获取当前阶段耗时"""
        if self.stage_start_time:
            return (datetime.now() - self.stage_start_time).total_seconds()
        return None
