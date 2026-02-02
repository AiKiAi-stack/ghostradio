"""
音频处理工具模块
提供音频时长提取、格式转换等功能
"""

import os
from pathlib import Path
from typing import Optional
from mutagen import File
from .logger import get_logger

logger = get_logger("audio_utils")


def get_audio_duration(file_path: str) -> float:
    """
    获取音频文件的时长（秒）
    支持 MP3, M4A, WAV 等格式
    """
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return 0.0

    try:
        audio = File(file_path)
        if audio is not None and audio.info is not None:
            return float(audio.info.length)

        # 如果 mutagen 无法自动识别，尝试手动检查
        logger.warning(f"Mutagen could not auto-detect format for {file_path}")
        return 0.0
    except Exception as e:
        logger.error(f"Error extracting duration from {file_path}", error=e)
        return 0.0


def format_duration(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
