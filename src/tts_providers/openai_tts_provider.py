"""
OpenAI TTS Provider 实现
"""

import os
import tempfile
from typing import Dict, Any, List
from .base_tts_provider import TTSProvider


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS Provider"""
    
    AVAILABLE_VOICES = [
        'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer',
        'coral', 'verse', 'ballad', 'ash', 'sage', 'amuch'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        config.setdefault('voice', 'alloy')
        config.setdefault('speed', 1.0)
        super().__init__(config)
    
    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        return True
    
    def synthesize(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        temp_files: List[str] = []
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            voice = kwargs.get('voice', self.voice)
            speed = kwargs.get('speed', self.speed)

            max_chunk_size = 4000
            chunks = self.split_text(text, max_chunk_size)

            for i, chunk in enumerate(chunks):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_files.append(temp_file.name)

                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=chunk,
                    speed=speed
                )

                response.stream_to_file(temp_file.name)
                temp_file.close()

            if len(temp_files) == 1:
                os.rename(temp_files[0], output_path)
            else:
                self._merge_audio_files(temp_files, output_path)

            duration = self.estimate_duration(text) / speed

            return {
                'success': True,
                'file_path': output_path,
                'duration': duration,
                'format': 'mp3'
            }

        except ImportError:
            return {'success': False, 'error': 'openai package not installed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def _merge_audio_files(self, file_paths: List[str], output_path: str):
        """合并多个音频文件"""
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            for file_path in file_paths:
                audio = AudioSegment.from_mp3(file_path)
                combined += audio
            
            combined.export(output_path, format="mp3")
        except ImportError:
            # 如果没有 pydub，使用 ffmpeg
            import subprocess
            
            list_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            for file_path in file_paths:
                list_file.write(f"file '{file_path}'\n")
            list_file.close()
            
            try:
                subprocess.run([
                    'ffmpeg', '-f', 'concat', '-safe', '0',
                    '-i', list_file.name,
                    '-acodec', 'copy',
                    output_path
                ], check=True, capture_output=True)
            finally:
                os.remove(list_file.name)
    
    def get_voice_list(self) -> list:
        return self.AVAILABLE_VOICES
    
    def get_provider_name(self) -> str:
        return "openai"
