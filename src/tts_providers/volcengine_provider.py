"""
火山引擎 TTS Provider 实现
使用火山引擎（豆包语音）API 进行语音合成
"""

import os
import base64
import json
import requests
import uuid
from typing import Dict, Any, Optional
from .base_tts_provider import TTSProvider


class VolcengineProvider(TTSProvider):
    """
    火山引擎（豆包语音）TTS Provider
    
    文档: https://www.volcengine.com/docs/6561/79820
    
    支持功能:
    - 多种音色选择
    - 语速、音量、音调调节
    - 长文本自动分段合成
    """
    
    # API 端点
    DEFAULT_BASE_URL = "https://openspeech.bytedance.com/api/v1/tts"
    
    # 常用音色列表
    AVAILABLE_VOICES = {
        # 中文音色
        "zh_female_xiaoxiao": "中文女声-晓晓",
        "zh_female_xiaoyi": "中文女声-小艺",
        "zh_male_xiaoming": "中文男声-小明",
        "zh_male_xiaogang": "中文男声-小刚",
        # 英文音色
        "en_female_linda": "英文女声-Linda",
        "en_male_mike": "英文男声-Mike",
        # 特色音色
        "zh_male_M392_conversation_wvae_bigtts": "中文男声-对话风格",
        "zh_female_M393_conversation_wvae_bigtts": "中文女声-对话风格",
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化火山引擎 Provider
        
        Args:
            config: 配置字典，应包含：
                - api_key: API 密钥 (Token)
                - appid: 应用 ID
                - cluster: 集群 ID (如 volcano_tts)
                - voice: 音色名称
                - speed: 语速 (0.5-2.0)
                - volume: 音量 (0.5-2.0)
                - pitch: 音调 (0.5-2.0)
        """
        # 设置默认值
        config.setdefault('base_url', self.DEFAULT_BASE_URL)
        config.setdefault('voice', 'zh_female_xiaoxiao')
        config.setdefault('speed', 1.0)
        config.setdefault('volume', 1.0)
        config.setdefault('pitch', 1.0)
        config.setdefault('cluster', 'volcano_tts')
        
        super().__init__(config)
        
        self.base_url = config.get('base_url', self.DEFAULT_BASE_URL)
        self.appid = config.get('appid', '')
        self.cluster = config.get('cluster', 'volcano_tts')
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.api_key:
            raise ValueError("API key (token) is required")
        
        if not self.appid:
            raise ValueError("AppID is required")
        
        return True
    
    def synthesize(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            
        Returns:
            Dict: 包含 success, file_path, duration, error 等字段
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer;{self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体
            payload = {
                "app": {
                    "appid": self.appid,
                    "token": self.api_key,
                    "cluster": kwargs.get('cluster', self.cluster)
                },
                "user": {
                    "uid": str(uuid.uuid4())
                },
                "audio": {
                    "voice_type": kwargs.get('voice', self.voice),
                    "encoding": "mp3",
                    "speed_ratio": kwargs.get('speed', self.speed),
                    "volume_ratio": kwargs.get('volume', self.volume),
                    "pitch_ratio": kwargs.get('pitch', self.pitch),
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "text_type": "plain",
                    "operation": "sync"
                }
            }
            
            # 发送请求
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # 检查响应
            response.raise_for_status()
            result = response.json()
            
            # 检查业务错误码
            if result.get('code') != 0:
                return {
                    'success': False,
                    'error': f"API error: {result.get('message', 'Unknown error')} (code: {result.get('code')})"
                }
            
            # 解码音频数据
            audio_data = result.get('data', '')
            if not audio_data:
                return {
                    'success': False,
                    'error': 'No audio data in response'
                }
            
            # Base64 解码并保存
            audio_bytes = base64.b64decode(audio_data)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            
            # 估算时长
            duration = self.estimate_duration(text)
            
            return {
                'success': True,
                'file_path': output_path,
                'duration': duration,
                'format': 'mp3'
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def synthesize_long_text(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        合成长文本（自动分段）
        
        Args:
            text: 长文本内容
            output_path: 输出文件路径
            
        Returns:
            Dict: 合成结果
        """
        # 分割文本
        chunks = self.split_text(text, max_length=1000)
        
        if len(chunks) == 1:
            # 短文本直接合成
            return self.synthesize(text, output_path, **kwargs)
        
        # 长文本分段合成
        temp_files = []
        
        try:
            from pydub import AudioSegment
            
            for i, chunk in enumerate(chunks):
                temp_path = f"{output_path}.temp.{i}.mp3"
                result = self.synthesize(chunk, temp_path, **kwargs)
                
                if not result['success']:
                    # 清理临时文件
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    return result
                
                temp_files.append(temp_path)
            
            # 合并音频文件
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                audio = AudioSegment.from_mp3(temp_file)
                combined += audio
            
            # 导出最终文件
            combined.export(output_path, format="mp3")
            
            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            # 计算总时长
            total_duration = sum(self.estimate_duration(chunk) for chunk in chunks)
            
            return {
                'success': True,
                'file_path': output_path,
                'duration': total_duration,
                'format': 'mp3',
                'chunks': len(chunks)
            }
            
        except ImportError:
            # 如果没有 pydub，只合成第一段
            print("Warning: pydub not installed, only synthesizing first chunk")
            return self.synthesize(chunks[0], output_path, **kwargs)
    
    def get_voice_list(self) -> list:
        """获取可用音色列表"""
        return [
            {"id": k, "name": v}
            for k, v in self.AVAILABLE_VOICES.items()
        ]
    
    def get_provider_name(self) -> str:
        """获取 Provider 名称"""
        return "volcengine"
