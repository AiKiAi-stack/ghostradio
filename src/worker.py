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
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_config
from src.content_fetcher import ContentFetcher
from src.llm_processor import LLMProcessor
from src.tts_generator import TTSGenerator
from src.config import get_config
from src.file_lock import FileLock
from src.job_queue import JobQueue
from src.episode_metadata import get_metadata_manager
from src.audio_utils import get_audio_duration
from src.job_status_updater import JobStatusUpdater
from src.job_models import JobStatus
from src.webhook_manager import get_webhook_manager
from typing import Optional, Dict, Any


class Worker:
    """GhostRadio 工作进程"""

    def __init__(self):
        self.config = get_config()
        self.paths = self.config.get_paths_config()
        self.resources = self.config.get_resources_config()
        self.podcast = self.config.get_podcast_config()

        self.fetcher = ContentFetcher()
        self._llm = None
        self._llm_config = self.config.get_llm_config()
        self.tts = TTSGenerator(self.config.get_tts_config())
        self.job_queue = JobQueue()
        self.status_updater = JobStatusUpdater(
            self.paths.get("logs_dir", "logs") + "/jobs"
        )
        self.webhook_manager = get_webhook_manager(self.config.get("notifications", {}))

        self._ensure_directories()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = LLMProcessor(self._llm_config)
        return self._llm

    def _ensure_directories(self):
        """确保必要的目录存在"""
        for dir_path in [self.paths["episodes_dir"], self.paths["logs_dir"]]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _acquire_lock(self) -> bool:
        """获取文件锁，防止并发运行"""
        lock_file = os.path.join(self.paths["logs_dir"], "worker.lock")
        self._lock = FileLock(lock_file)
        return self._lock.acquire()

    def _release_lock(self):
        """释放文件锁"""
        if hasattr(self, "_lock") and self._lock:
            self._lock.release()
            self._lock = None

    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        # 输出到控制台
        print(log_line.strip())

        # 写入日志文件
        log_file = os.path.join(self.paths["logs_dir"], "worker.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def _generate_episode_id(self) -> str:
        """生成节目 ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _cleanup_old_episodes(self):
        """清理旧节目文件"""
        episodes_dir = self.paths["episodes_dir"]
        keep_n = self.resources["keep_last_n_episodes"]
        max_size_mb = self.resources["max_disk_usage_mb"]

        # 获取所有音频文件
        audio_files = []
        for ext in [".mp3", ".m4a", ".ogg", ".opus"]:
            audio_files.extend(Path(episodes_dir).glob(f"*{ext}"))

        # 按修改时间排序
        audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # 删除超过保留数量的文件
        if len(audio_files) > keep_n:
            for old_file in audio_files[keep_n:]:
                try:
                    old_file.unlink()
                    self._log(f"Cleaned up old episode: {old_file.name}")
                except Exception as e:
                    self._log(f"Failed to clean up {old_file.name}: {e}", "WARNING")

        # 检查总大小
        total_size_mb = sum(f.stat().st_size for f in audio_files[:keep_n]) / (
            1024 * 1024
        )
        if total_size_mb > max_size_mb:
            self._log(
                f"Warning: Episodes directory size ({total_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)",
                "WARNING",
            )

    def process_url(
        self,
        url: str,
        need_summary: bool = True,
        job_id: Optional[str] = None,
        tts_config: Optional[dict] = None,
        user_id: str = "default",
    ) -> dict:
        """处理单个 URL"""
        episode_id = self._generate_episode_id()
        start_time = time.time()

        user_dir = os.path.join(self.paths["episodes_dir"], user_id)
        os.makedirs(user_dir, exist_ok=True)

        self._log(f"Processing URL for user {user_id}: {url}")

        self._log(
            f"Mode: {'With LLM summary' if need_summary else 'Direct URL (no summary)'}"
        )
        if tts_config:
            self._log(f"Custom TTS Config provided: {list(tts_config.keys())}")

        try:
            # 1. 获取内容
            if job_id:
                self.status_updater.update_job(
                    job_id,
                    status=JobStatus.PROCESSING,
                    progress=10,
                    message="开始抓取内容...",
                    stage="fetching",
                )

            fetch_start = time.time()
            self._log("Step 1: Fetching content...")
            content_result = self.fetcher.fetch(url)
            fetch_duration = time.time() - fetch_start

            if not content_result["success"]:
                raise Exception(
                    f"Failed to fetch content: {content_result.get('error', 'Unknown error')}"
                )

            title = content_result["title"]
            content = content_result["content"]
            self._log(f"Fetched: {title} ({len(content)} chars)")

            llm_tokens = 0
            llm_provider = "none"
            llm_duration = 0
            if need_summary:
                # 2. LLM 处理
                if job_id:
                    self.status_updater.update_job(
                        job_id,
                        progress=25,
                        message=f"正在生成播客脚本 ({llm_provider})...",
                        stage="llm_processing",
                    )

                llm_start = time.time()
                self._log("Step 2: Processing with LLM...")
                llm_result = self.llm.process(title, content)
                llm_duration = time.time() - llm_start

                if not llm_result["success"]:
                    raise Exception(
                        f"LLM processing failed: {llm_result.get('error', 'Unknown error')}"
                    )

                script = llm_result["script"]
                llm_tokens = llm_result.get("tokens_used", 0)
                llm_provider = self.llm.provider_info.name
                self._log(f"Generated script ({llm_tokens} tokens)")

                if job_id:
                    self.status_updater.update_job(
                        job_id,
                        progress=50,
                        message="脚本生成完成",
                    )
            else:
                # 直接使用内容
                script = content
                self._log("Step 2: Using raw content (no summary)")
                if job_id:
                    self.status_updater.update_job(
                        job_id,
                        progress=50,
                        message="跳过总结，直接使用正文",
                    )

            # 保存脚本
            script_path = os.path.join(user_dir, f"{episode_id}.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n")
                f.write(f"Source: {url}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(
                    f"Mode: {'LLM Summary' if need_summary else 'Direct Content'}\n"
                )
                f.write("\n" + "=" * 50 + "\n\n")
                f.write(script)

            # 3. TTS 生成
            if job_id:
                self.status_updater.update_job(
                    job_id,
                    progress=60,
                    message=f"正在合成语音 ({self.tts.provider_info['name']})...",
                    stage="tts_generating",
                )

            tts_start = time.time()
            self._log("Step 3: Generating audio...")
            audio_format = self.resources["audio_format"]
            audio_path = os.path.join(user_dir, f"{episode_id}.{audio_format}")

            # 传递 tts_config
            tts_params = tts_config or {}
            tts_result = self.tts.generate(script, audio_path, **tts_params)
            tts_duration = time.time() - tts_start

            if not tts_result["success"]:
                raise Exception(
                    f"TTS generation failed: {tts_result.get('error', 'Unknown error')}"
                )

            self._log(
                f"Generated audio: {audio_path} ({tts_result.get('duration', 0)}s)"
            )

            actual_duration = get_audio_duration(audio_path)
            if actual_duration > 0:
                self._log(f"Actual audio duration detected: {actual_duration:.2f}s")
            else:
                actual_duration = float(tts_result.get("duration", 0))

            total_duration = time.time() - start_time

            # 4. 保存元数据
            if job_id:
                self.status_updater.update_job(
                    job_id,
                    progress=90,
                    message="正在保存节目信息...",
                )

            try:
                metadata_manager = get_metadata_manager(user_id)
                audio_size_bytes = os.path.getsize(audio_path)

                episode_metadata = {
                    "id": episode_id,
                    "title": title,
                    "created_at": datetime.now().isoformat(),
                    "audio_file": os.path.basename(audio_path),
                    "size_bytes": audio_size_bytes,
                    "size_mb": round(audio_size_bytes / (1024 * 1024), 2),
                    "duration_seconds": actual_duration,
                    "source_url": url,
                    "tokens_used": {"llm": llm_tokens},
                    "providers_used": {
                        "llm": llm_provider,
                        "tts": self.tts.provider_info["name"],
                    },
                    "performance": {
                        "fetch_seconds": round(fetch_duration, 2),
                        "llm_seconds": round(llm_duration, 2),
                        "tts_seconds": round(tts_duration, 2),
                        "total_seconds": round(total_duration, 2),
                    },
                }
                metadata_manager.add_episode(episode_metadata, limit=10)
                self._log(f"Metadata saved for user {user_id}, episode {episode_id}")
            except Exception as e:
                self._log(f"Failed to save metadata: {e}", "WARNING")

            # 5. 清理旧文件
            self._cleanup_old_episodes()

            result_data = {
                "success": True,
                "episode_id": episode_id,
                "title": title,
                "url": url,
                "audio_path": audio_path,
                "script_path": script_path,
                "duration": actual_duration,
                "need_summary": need_summary,
                "audio_url": f"episodes/{os.path.basename(audio_path)}",
            }

            if job_id:
                self.status_updater.update_job(
                    job_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    message="播客生成成功！",
                    result=result_data,
                )
                self.webhook_manager.send_notification("job_success", result_data)

            return result_data

        except Exception as e:
            self._log(f"Error processing URL: {e}", "ERROR")
            if job_id:
                error_data = {
                    "job_id": job_id,
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                self.status_updater.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    error=str(e),
                    message=f"处理失败: {str(e)}",
                )
                self.webhook_manager.send_notification("job_failed", error_data)
            return {"success": False, "error": str(e), "url": url}

    def run(self):
        self._log("GhostRadio Worker started")

        if not self._acquire_lock():
            self._log("Another worker is already running, exiting")
            return

        try:
            JobQueue.migrate_from_old_queue()

            pending_jobs = self.job_queue.get_pending_jobs()

            if not pending_jobs:
                self._log("Queue is empty, nothing to do")
                return

            self._log(f"Found {len(pending_jobs)} items in queue")

            results = []
            users_processed = set()

            for job_data in pending_jobs:
                url = job_data["url"]
                job_id = job_data.get("job_id")
                user_id = job_data.get("user_id", "default")
                need_summary = job_data.get("need_summary", True)
                tts_config = job_data.get("tts_config", {})
                queue_file = job_data.get("_queue_file")

                users_processed.add(user_id)

                if job_id:
                    try:
                        job_file = os.path.join(
                            self.paths["logs_dir"], "jobs", f"{job_id}.json"
                        )
                        if os.path.exists(job_file):
                            with open(job_file, "r", encoding="utf-8") as f:
                                job_metadata = json.load(f)
                                need_summary = job_metadata.get("need_summary", True)
                                tts_config = job_metadata.get("tts_config", {})
                                self._log(
                                    f"Loaded job {job_id}: user={user_id}, need_summary={need_summary}, tts_config={list(tts_config.keys())}"
                                )
                    except Exception as e:
                        self._log(f"Failed to load job {job_id}: {e}", "WARNING")

                result = self.process_url(
                    url, need_summary, job_id, tts_config, user_id=user_id
                )
                results.append(result)

                if queue_file:
                    if result["success"]:
                        self.job_queue.mark_processed(queue_file)
                    else:
                        retry_count = job_data.get("retry_count", 0)
                        max_retries = job_data.get("max_retries", 3)

                        if retry_count < max_retries:
                            new_queue_id = self.job_queue.retry_job(queue_file)
                            if new_queue_id:
                                self._log(
                                    f"Job retry scheduled: attempt {retry_count + 1}/{max_retries}, new queue_id: {new_queue_id}"
                                )
                            else:
                                self.job_queue.mark_failed(
                                    queue_file, result.get("error", "Unknown error")
                                )
                        else:
                            self.job_queue.mark_failed(
                                queue_file, result.get("error", "Max retries exceeded")
                            )
                            self._log(
                                f"Job failed permanently after {max_retries} retries"
                            )

            success_count = sum(1 for r in results if r["success"])
            fail_count = len(results) - success_count

            self._log(
                f"Processing complete: {success_count} succeeded, {fail_count} failed"
            )

            if success_count > 0:
                try:
                    from src.rss_generator import RSSGenerator
                    from src.episode_metadata import get_metadata_manager

                    for user_id in users_processed:
                        metadata_manager = get_metadata_manager(user_id)
                        episodes = metadata_manager.get_all_episodes()

                        user_config = self.config._config.copy()
                        user_rss_file = os.path.join(
                            self.paths["episodes_dir"], user_id, "feed.xml"
                        )
                        user_config["paths"]["rss_file"] = user_rss_file

                        rss_gen = RSSGenerator(user_config, user_id=user_id)
                        rss_gen.save_rss(episodes)
                        self._log(
                            f"RSS feed updated for user {user_id} at {user_rss_file}"
                        )
                except Exception as e:
                    self._log(f"Failed to update RSS feed: {e}", "WARNING")

            return results

        finally:
            self._release_lock()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GhostRadio Worker")
    parser.add_argument(
        "--config", "-c", default="config.yaml", help="Config file path"
    )
    parser.add_argument("--once", "-o", action="store_true", help="Run once and exit")

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


if __name__ == "__main__":
    main()
