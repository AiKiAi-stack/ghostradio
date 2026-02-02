"""
Episode Metadata Manager
Centralized episode metadata storage using JSON
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class EpisodeMetadataManager:
    """Manages episode metadata in a centralized JSON file"""

    def __init__(self, metadata_file: str = "episodes/metadata.json"):
        self.metadata_file = Path(metadata_file)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        """Create metadata file if it doesn't exist"""
        if not self.metadata_file.exists():
            self._save_metadata({"episodes": []})

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file"""
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {"episodes": []}

    def _save_metadata(self, data: Dict[str, Any]):
        """Save metadata to file"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_episode(self, episode_data: Dict[str, Any]) -> bool:
        """Add new episode to metadata"""
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
        """Get all episodes from metadata"""
        metadata = self._load_metadata()
        return metadata.get("episodes", [])

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Get specific episode by ID"""
        episodes = self.get_all_episodes()
        for ep in episodes:
            if ep.get("id") == episode_id:
                return ep
        return None

    def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing episode"""
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
        """Delete episode from metadata"""
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
        """Migrate existing episodes from filesystem to metadata"""
        manager = cls()
        episodes_path = Path(episodes_dir)

        if not episodes_path.exists():
            return 0

        migrated = 0
        for audio_file in episodes_path.glob("*.mp3"):
            episode_id = audio_file.stem

            stat = audio_file.stat()
            episode_data = {
                "id": episode_id,
                "title": episode_id.replace("_", " ").title(),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "audio_file": f"episodes/{audio_file.name}",
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "duration_seconds": 0,
                "source_url": "",
                "tokens_used": {},
                "providers_used": {},
            }

            if manager.add_episode(episode_data):
                migrated += 1

        print(f"Migrated {migrated} episodes from filesystem")
        return migrated


def get_metadata_manager() -> EpisodeMetadataManager:
    """Get singleton instance of metadata manager"""
    if not hasattr(get_metadata_manager, "_instance"):
        get_metadata_manager._instance = EpisodeMetadataManager()
    return get_metadata_manager._instance
