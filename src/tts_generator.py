"""
TTS 音频生成模块
支持多种 TTS 提供商 (OpenAI, Azure, Edge-TTS)
"""

import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path


class TTSGenerator:
    """TTS 生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('provider', 'openai')
    
    def generate(self, text: str, output_path: str) -> dict:
        """
        生成音频文件
        
        Args:
            text: 要转换为语音的文本
            output_path: 输出文件路径
            
        Returns:
            dict: {
                'success': bool,
                'file_path': str,
                'duration': float,
                'error': str (if failed)
            }
        """
        try:
            if self.provider == 'openai':
                return self._generate_openai(text, output_path)
            elif self.provider == 'azure':
                return self._generate_azure(text, output_path)
            elif self.provider == 'edge-tts':
                return self._generate_edge_tts(text, output_path)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported TTS provider: {self.provider}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'TTS generation error: {str(e)}'
            }
    
    def _generate_openai(self, text: str, output_path: str) -> dict:
        """使用 OpenAI TTS API 生成音频"""
        from openai import OpenAI
        
        api_key = self.config.get('api_key')
        if not api_key:
            raise ValueError(f"TTS API Key not found in environment variable: {self.config.get('api_key_env', 'TTS_API_KEY')}")
        
        client = OpenAI(api_key=api_key)
        
        voice = self.config.get('voice', 'alloy')
        speed = self.config.get('speed', 1.0)
        
        # 分段处理长文本（OpenAI TTS 有长度限制）
        max_chunk_size = 4000
        chunks = self._split_text(text, max_chunk_size)
        
        temp_files = []
        
        try:
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
            
            # 合并音频文件
            if len(temp_files) == 1:
                # 直接移动文件
                os.rename(temp_files[0], output_path)
            else:
                # 合并多个音频文件
                self._merge_audio_files(temp_files, output_path)
            
            # 估算时长 (假设平均语速 150 字/分钟)
            estimated_duration = len(text) / 150 * 60 / speed
            
            return {
                'success': True,
                'file_path': output_path,
                'duration': estimated_duration
            }
            
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def _generate_azure(self, text: str, output_path: str) -> dict:
        """使用 Azure TTS API 生成音频"""
        # TODO: 实现 Azure TTS 支持
        return {
            'success': False,
            'error': 'Azure TTS not implemented yet'
        }
    
    def _generate_edge_tts(self, text: str, output_path: str) -> dict:
        """使用 Edge-TTS (免费) 生成音频"""
        try:
            import edge_tts
            import asyncio
            
            voice = self.config.get('voice', 'zh-CN-XiaoxiaoNeural')
            speed = self.config.get('speed', 1.0)
            
            # 调整语速参数
            rate = f"+{int((speed - 1) * 100)}%" if speed > 1 else f"{int((speed - 1) * 100)}%"
            
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(output_path)
            
            asyncio.run(generate())
            
            # 估算时长
            estimated_duration = len(text) / 150 * 60 / speed
            
            return {
                'success': True,
                'file_path': output_path,
                'duration': estimated_duration
            }
            
        except ImportError:
            return {
                'success': False,
                'error': 'edge-tts not installed. Run: pip install edge-tts'
            }
    
    def _split_text(self, text: str, max_chunk_size: int) -> list:
        """将长文本分割成多个小块"""
        chunks = []
        current_chunk = ""
        
        # 按句子分割
        sentences = text.replace('。', '。|').replace('！', '！|').replace('？', '？|').split('|')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text[:max_chunk_size]]
    
    def _merge_audio_files(self, file_paths: list, output_path: str):
        """合并多个音频文件"""
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            for file_path in file_paths:
                audio = AudioSegment.from_mp3(file_path)
                combined += audio
            
            combined.export(output_path, format="mp3")
            
        except ImportError:
            # 如果 pydub 不可用，使用 ffmpeg 命令
            import subprocess
            
            # 创建文件列表
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
