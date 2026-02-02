"""
结构化日志模块
提供详细的日志记录，支持不同级别和上下文信息
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """
    结构化日志记录器
    
    特点：
    - 支持结构化输出（JSON格式）
    - 自动添加上下文信息（时间、模块、行号）
    - 支持不同日志级别
    - 同时输出到文件和控制台
    """
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        log_file: str = "ghostradio.log",
        level: LogLevel = LogLevel.INFO,
        console_output: bool = True
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / log_file
        self.level = level
        self.console_output = console_output
        
        # 设置标准库日志
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self._get_logging_level(level))
        
        # 清除现有处理器
        self._logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self._logger.addHandler(console_handler)
    
    def _get_logging_level(self, level: LogLevel) -> int:
        """转换日志级别"""
        levels = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        return levels.get(level, logging.INFO)
    
    def _format_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> str:
        """格式化日志消息"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "logger": self.name,
            "message": message
        }
        
        if context:
            log_entry["context"] = context
        
        if error:
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": self._get_traceback(error)
            }
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)
    
    def _get_traceback(self, error: Exception) -> str:
        """获取异常堆栈"""
        import traceback
        return traceback.format_exc()
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """调试日志"""
        self._logger.debug(self._format_message(message, context))
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """信息日志"""
        self._logger.info(self._format_message(message, context))
    
    def warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """警告日志"""
        self._logger.warning(self._format_message(message, context, error))
    
    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """错误日志"""
        self._logger.error(self._format_message(message, context, error))
    
    def critical(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """严重错误日志"""
        self._logger.critical(self._format_message(message, context, error))
    
    def log_job_start(
        self,
        job_id: str,
        url: str,
        llm_model: str,
        tts_model: str,
        need_summary: bool = True
    ) -> None:
        """记录任务开始"""
        self.info(
            f"Job {job_id} started",
            context={
                "job_id": job_id,
                "url": url,
                "llm_model": llm_model,
                "tts_model": tts_model,
                "need_summary": need_summary,
                "event": "job_start"
            }
        )
    
    def log_job_progress(
        self,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录任务进度"""
        context = {
            "job_id": job_id,
            "stage": stage,
            "progress": progress,
            "event": "job_progress"
        }
        if details:
            context["details"] = details
        
        self.info(message, context=context)
    
    def log_job_complete(
        self,
        job_id: str,
        duration: float,
        output_file: str,
        tokens_used: int = 0
    ) -> None:
        """记录任务完成"""
        self.info(
            f"Job {job_id} completed in {duration:.2f}s",
            context={
                "job_id": job_id,
                "duration": duration,
                "output_file": output_file,
                "tokens_used": tokens_used,
                "event": "job_complete"
            }
        )
    
    def log_job_error(
        self,
        job_id: str,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录任务错误"""
        ctx = {
            "job_id": job_id,
            "stage": stage,
            "event": "job_error"
        }
        if context:
            ctx.update(context)
        
        self.error(
            f"Job {job_id} failed at stage '{stage}': {str(error)}",
            context=ctx,
            error=error
        )
    
    def log_job_cancelled(self, job_id: str, reason: str) -> None:
        """记录任务取消"""
        self.warning(
            f"Job {job_id} cancelled: {reason}",
            context={
                "job_id": job_id,
                "reason": reason,
                "event": "job_cancelled"
            }
        )
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: Optional[str] = None
    ) -> None:
        """记录API请求"""
        self.debug(
            f"API {method} {path} -> {status_code}",
            context={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "event": "api_request"
            }
        )
    
    def log_timeout(
        self,
        job_id: str,
        stage: str,
        elapsed: float,
        timeout: float
    ) -> None:
        """记录超时警告"""
        self.warning(
            f"Job {job_id} timeout warning at stage '{stage}'",
            context={
                "job_id": job_id,
                "stage": stage,
                "elapsed_seconds": elapsed,
                "timeout_seconds": timeout,
                "event": "timeout_warning"
            }
        )


# 全局日志实例
_default_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "ghostradio") -> StructuredLogger:
    """获取日志记录器实例"""
    global _default_logger
    if _default_logger is None:
        _default_logger = StructuredLogger(name)
    return _default_logger


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "ghostradio.log",
    level: LogLevel = LogLevel.INFO
) -> StructuredLogger:
    """设置日志系统"""
    global _default_logger
    _default_logger = StructuredLogger(
        name="ghostradio",
        log_dir=log_dir,
        log_file=log_file,
        level=level
    )
    return _default_logger
