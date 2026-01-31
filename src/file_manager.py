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
    
    def __init__(self, config: Dict[str, Any]):
        self.episodes_dir = config.get('episodes_dir', 'episodes')
        self.keep_last_n = config.get('keep_last_n_episodes', 5)
        self.max_disk_mb = config.get('max_disk_usage_mb', 200)
        self.audio_format = config.get('audio_format', 'm4a')
    
    def get_episodes(self) -> List[Dict[str, Any]]:
        """获取所有节目列表"""
        episodes = []
        
        # 查找所有音频文件
        patterns = [
            os.path.join(self.episodes_dir, f'*.{self.audio_format}'),
            os.path.join(self.episodes_dir, '*.mp3'),
            os.path.join(self.episodes_dir, '*.m4a'),
            os.path.join(self.episodes_dir, '*.ogg'),
            os.path.join(self.episodes_dir, '*.opus')
        ]
        
        audio_files = set()
        for pattern in patterns:
            audio_files.update(glob.glob(pattern))
        
        for audio_path in audio_files:
            audio_path = Path(audio_path)
            episode_id = audio_path.stem
            
            # 查找对应的元数据文件
            meta_path = audio_path.with_suffix('.json')
            script_path = audio_path.with_suffix('.txt')
            
            episode = {
                'id': episode_id,
                'audio_file': str(audio_path),
                'created': datetime.fromtimestamp(audio_path.stat().st_mtime),
                'size_mb': audio_path.stat().st_size / (1024 * 1024)
            }
            
            # 加载元数据
            if meta_path.exists():
                try:
                    import json
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        episode.update(meta)
                except:
                    pass
            
            # 从脚本文件提取标题
            if script_path.exists() and 'title' not in episode:
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if first_line.startswith('Title:'):
                            episode['title'] = first_line.replace('Title:', '').strip()
                except:
                    pass
            
            if 'title' not in episode:
                episode['title'] = episode_id
            
            episodes.append(episode)
        
        # 按创建时间排序（最新的在前）
        episodes.sort(key=lambda x: x['created'], reverse=True)
        
        return episodes
    
    def cleanup(self) -> Dict[str, Any]:
        """
        清理旧文件
        
        Returns:
            dict: 清理结果统计
        """
        episodes = self.get_episodes()
        
        deleted_count = 0
        freed_space_mb = 0
        
        # 1. 删除超过保留数量的文件
        if len(episodes) > self.keep_last_n:
            to_delete = episodes[self.keep_last_n:]
            
            for episode in to_delete:
                # 删除音频文件
                audio_file = episode['audio_file']
                if os.path.exists(audio_file):
                    try:
                        size = os.path.getsize(audio_file)
                        os.remove(audio_file)
                        freed_space_mb += size / (1024 * 1024)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete {audio_file}: {e}")
                
                # 删除对应的元数据文件
                base_path = Path(audio_file).with_suffix('')
                for ext in ['.json', '.txt']:
                    meta_file = base_path.with_suffix(ext)
                    if meta_file.exists():
                        try:
                            os.remove(meta_file)
                        except:
                            pass
        
        # 2. 检查总大小，如果超过限制，继续删除最旧的
        episodes = self.get_episodes()  # 重新获取列表
        total_size_mb = sum(e['size_mb'] for e in episodes)
        
        while total_size_mb > self.max_disk_mb and len(episodes) > 1:
            # 删除最旧的
            oldest = episodes.pop()
            audio_file = oldest['audio_file']
            
            if os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    freed_space_mb += oldest['size_mb']
                    deleted_count += 1
                    total_size_mb -= oldest['size_mb']
                except Exception as e:
                    print(f"Failed to delete {audio_file}: {e}")
                    break
            
            # 删除对应的元数据文件
            base_path = Path(audio_file).with_suffix('')
            for ext in ['.json', '.txt']:
                meta_file = base_path.with_suffix(ext)
                if meta_file.exists():
                    try:
                        os.remove(meta_file)
                    except:
                        pass
        
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2),
            'remaining_count': len(episodes),
            'total_size_mb': round(total_size_mb, 2)
        }
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        episodes = self.get_episodes()
        
        total_size_mb = sum(e['size_mb'] for e in episodes)
        
        return {
            'episode_count': len(episodes),
            'total_size_mb': round(total_size_mb, 2),
            'max_size_mb': self.max_disk_mb,
            'usage_percent': round((total_size_mb / self.max_disk_mb) * 100, 1) if self.max_disk_mb > 0 else 0
        }
    
    def save_episode_metadata(self, episode_id: str, metadata: Dict[str, Any]):
        """保存节目元数据"""
        meta_path = os.path.join(self.episodes_dir, f"{episode_id}.json")
        
        # 添加时间戳
        metadata['saved_at'] = datetime.now().isoformat()
        
        import json
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
