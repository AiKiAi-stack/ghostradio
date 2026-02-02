"""
Episode Metadata Manager
Centralized episode metadata storage using JSON
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.audio_utils import get_audio_duration


class EpisodeMetadataManager:
    """Manages episode metadata in a centralized JSON file"""

    def __init__(self, metadata_file: str = "episodes/metadata.json"):
        self.metadata_file = Path(metadata_file)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        if not self.metadata_file.exists():
            self._save_metadata({"episodes": []})

    def _load_metadata(self) -> Dict[str, Any]:
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {"episodes": []}

    def _save_metadata(self, data: Dict[str, Any]):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_episode(self, episode_data: Dict[str, Any]) -> bool:
        try:
            metadata = self._load_metadata()

            episode_id = episode_data.get("id")
            if not episode_id:
                return False

            for i, ep in enumerate(metadata["episodes"]):
                if ep.get("id") == episode_id:
                    metadata["episodes"][i] = episode_data
                    self._save_metadata(metadata)
                    return True

            metadata["episodes"].insert(0, episode_data)
            self._save_metadata(metadata)
            return True

        except Exception as e:
            print(f"Error adding episode: {e}")
            return False

    def get_all_episodes(self) -> List[Dict[str, Any]]:
        metadata = self._load_metadata()
        return metadata.get("episodes", [])

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        episodes = self.get_all_episodes()
        for ep in episodes:
            if ep.get("id") == episode_id:
                return ep
        return None

    def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        try:
            metadata = self._load_metadata()

            for i, ep in enumerate(metadata["episodes"]):
                if ep.get("id") == episode_id:
                    metadata["episodes"][i].update(updates)
                    self._save_metadata(metadata)
                    return True

            return False

        except Exception as e:
            print(f"Error updating episode: {e}")
            return False

    def delete_episode(self, episode_id: str) -> bool:
        try:
            metadata = self._load_metadata()

            metadata["episodes"] = [
                ep for ep in metadata["episodes"] if ep.get("id") != episode_id
            ]

            self._save_metadata(metadata)
            return True

        except Exception as e:
            print(f"Error deleting episode: {e}")
            return False

    @classmethod
    def migrate_from_filesystem(cls, episodes_dir: str = "episodes") -> int:
        manager = cls()
        episodes_path = Path(episodes_dir)

        if not episodes_path.exists():
            return 0

        existing_episodes = {ep["id"]: ep for ep in manager.get_all_episodes()}
        migrated = 0

        for audio_file in episodes_path.glob("*.mp3"):
            episode_id = audio_file.stem

            if (
                episode_id in existing_episodes
                and existing_episodes[episode_id].get("duration_seconds", 0) > 0
            ):
                continue

            stat = audio_file.stat()
            duration = get_audio_duration(str(audio_file))

            episode_data = {
                "id": episode_id,
                "title": episode_id.replace("_", " ").title(),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "audio_file": f"episodes/{audio_file.name}",
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "duration_seconds": duration,
                "source_url": "",
                "tokens_used": {},
                "providers_used": {},
            }

            if manager.add_episode(episode_data):
                migrated += 1

        if migrated > 0:
            print(f"Migrated {migrated} episodes from filesystem")
        return migrated


_metadata_manager_instance: Optional[EpisodeMetadataManager] = None


def get_metadata_manager() -> EpisodeMetadataManager:
    """Get singleton instance of metadata manager"""
    global _metadata_manager_instance
    if _metadata_manager_instance is None:
        _metadata_manager_instance = EpisodeMetadataManager()
    return _metadata_manager_instance
