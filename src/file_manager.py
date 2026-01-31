"""
文件生命周期管理模块
管理音频文件的 FIFO 策略和磁盘空间
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class FileManager:
    """文件管理器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.episodes_dir: str = config.get('episodes_dir', 'episodes')
        self.keep_last_n: int = config.get('keep_last_n_episodes', 5)
        self.max_disk_mb: float = config.get('max_disk_usage_mb', 200)
        self.audio_format: str = config.get('audio_format', 'm4a')

    def get_episodes(self) -> List[Dict[str, Any]]:
        """获取所有节目列表"""
        episodes: List[Dict[str, Any]] = []

        patterns: List[str] = [
            os.path.join(self.episodes_dir, f'*.{self.audio_format}'),
            os.path.join(self.episodes_dir, '*.mp3'),
            os.path.join(self.episodes_dir, '*.m4a'),
            os.path.join(self.episodes_dir, '*.ogg'),
            os.path.join(self.episodes_dir, '*.opus')
        ]

        audio_files: set = set()
        for pattern in patterns:
            audio_files.update(glob.glob(pattern))

        for audio_path in audio_files:
            audio_path = Path(audio_path)
            episode_id: str = audio_path.stem

            meta_path: Path = audio_path.with_suffix('.json')
            script_path: Path = audio_path.with_suffix('.txt')

            episode: Dict[str, Any] = {
                'id': episode_id,
                'audio_file': str(audio_path),
                'created': datetime.fromtimestamp(audio_path.stat().st_mtime),
                'size_mb': audio_path.stat().st_size / (1024 * 1024)
            }

            if meta_path.exists():
                try:
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta: Dict[str, Any] = json.load(f)
                        episode.update(meta)
                except Exception:
                    pass

            if script_path.exists() and 'title' not in episode:
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        first_line: str = f.readline()
                        if first_line.startswith('Title:'):
                            episode['title'] = first_line.replace('Title:', '').strip()
                except Exception:
                    pass

            if 'title' not in episode:
                episode['title'] = episode_id

            episodes.append(episode)

        episodes.sort(key=lambda x: x['created'], reverse=True)

        return episodes

    def cleanup(self) -> Dict[str, Any]:
        """
        清理旧文件

        Returns:
            dict: 清理结果统计
        """
        episodes: List[Dict[str, Any]] = self.get_episodes()

        deleted_count: int = 0
        freed_space_mb: float = 0

        if len(episodes) > self.keep_last_n:
            to_delete: List[Dict[str, Any]] = episodes[self.keep_last_n:]

            for episode in to_delete:
                audio_file: str = episode['audio_file']
                if os.path.exists(audio_file):
                    try:
                        size: int = os.path.getsize(audio_file)
                        os.remove(audio_file)
                        freed_space_mb += size / (1024 * 1024)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete {audio_file}: {e}")

                base_path: Path = Path(audio_file).with_suffix('')
                for ext in ['.json', '.txt']:
                    meta_file: Path = base_path.with_suffix(ext)
                    if meta_file.exists():
                        try:
                            os.remove(meta_file)
                        except Exception:
                            pass

        episodes = self.get_episodes()
        total_size_mb: float = sum(e['size_mb'] for e in episodes)

        while total_size_mb > self.max_disk_mb and len(episodes) > 1:
            oldest: Dict[str, Any] = episodes.pop()
            audio_file: str = oldest['audio_file']

            if os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    freed_space_mb += oldest['size_mb']
                    deleted_count += 1
                    total_size_mb -= oldest['size_mb']
                except Exception as e:
                    print(f"Failed to delete {audio_file}: {e}")
                    break

            base_path = Path(audio_file).with_suffix('')
            for ext in ['.json', '.txt']:
                meta_file = base_path.with_suffix(ext)
                if meta_file.exists():
                    try:
                        os.remove(meta_file)
                    except Exception:
                        pass

        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2),
            'remaining_count': len(episodes),
            'total_size_mb': round(total_size_mb, 2)
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        episodes: List[Dict[str, Any]] = self.get_episodes()

        total_size_mb: float = sum(e['size_mb'] for e in episodes)

        return {
            'episode_count': len(episodes),
            'total_size_mb': round(total_size_mb, 2),
            'max_size_mb': self.max_disk_mb,
            'usage_percent': round((total_size_mb / self.max_disk_mb) * 100, 1) if self.max_disk_mb > 0 else 0
        }

    def save_episode_metadata(self, episode_id: str, metadata: Dict[str, Any]) -> None:
        """保存节目元数据"""
        meta_path: str = os.path.join(self.episodes_dir, f"{episode_id}.json")

        metadata['saved_at'] = datetime.now().isoformat()

        import json
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
