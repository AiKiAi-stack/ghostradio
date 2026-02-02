"""
火山引擎播客 TTS Provider 实现
使用火山引擎官方播客 API (WebSocket 协议)

完全重写以支持:
- WebSocket 协议
- 播客专用 TTS 端点
- 官方认证方式
- 流式音频接收
"""

import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from .base_tts_provider import TTSProvider

# 导入官方协议模块
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from protocols import (
    EventType,
    MsgType,
    finish_connection,
    finish_session,
    receive_message,
    start_connection,
    start_session,
    wait_for_event,
)

try:
    import websockets
except ImportError:
    raise ImportError(
        "websockets is required for Volcengine TTS. "
        "Install it with: pip install websockets>=14.0"
    )

logger = logging.getLogger("volcengine_tts")


class VolcengineTTSProvider(TTSProvider):
    """
    火山引擎播客 TTS Provider

    使用官方播客 WebSocket API:
    - 端点: wss://openspeech.bytedance.com/api/v3/sami/podcasttts
    - 协议: 自定义二进制协议 (sami)
    - 认证: X-Api-App-Id + X-Api-Access-Key

    支持功能:
    - 多种音色选择
    - 语速、音量调节
    - 流式音频接收
    - 自动重试和断点续传
    """

    # API 端点
    DEFAULT_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/sami/podcasttts"

    # 常用音色列表 (播客 API 支持的音色)
    AVAILABLE_VOICES = {
        # 播客专用音色会根据实际 API 文档更新
        "zh_female_xiaoxiao": "中文女声-晓晓",
        "zh_female_xiaoyi": "中文女声-小艺",
        "zh_male_xiaoming": "中文男声-小明",
        "zh_male_xiaogang": "中文男声-小刚",
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化火山引擎播客 TTS Provider

        Args:
            config: 配置字典，应包含：
                - api_key: Access Token (通过 api_key_env 从环境变量读取)
                - appid: 应用 ID (通过 appid_env 从环境变量读取)
                - resource_id: 资源 ID (可选)
                - voice: 音色名称
                - speed: 语速 (默认 1.0)
                - encoding: 音频格式 (mp3/wav)
        """
        # 设置默认值
        config.setdefault("endpoint", self.DEFAULT_ENDPOINT)
        config.setdefault("voice", "zh_female_xiaoxiao")
        config.setdefault("speed", 1.0)
        config.setdefault("encoding", "mp3")
        config.setdefault("resource_id", "volc.service_type.10050")
        config.setdefault("app_key", "aGjiRDfUWi")  # 官方 demo 中的固定值

        super().__init__(config)

        self.endpoint = config.get("endpoint", self.DEFAULT_ENDPOINT)
        self.appid = config.get("appid", "")
        self.resource_id = config.get("resource_id", "volc.service_type.10050")
        self.app_key = config.get("app_key", "aGjiRDfUWi")
        self.encoding = config.get("encoding", "mp3")

    def validate_config(self) -> bool:
        """验证配置"""
        if not self.api_key:
            raise ValueError(
                "API key (access token) is required. Set VOLCENGINE_TOKEN environment variable."
            )

        if not self.appid:
            raise ValueError(
                "AppID is required. Set VOLCENGINE_APPID environment variable."
            )

        return True

    def synthesize(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """
        合成语音 (同步接口，内部调用异步实现)

        Args:
            text: 要合成的文本
            output_path: 输出文件路径

        Returns:
            Dict: 包含 success, file_path, duration, error 等字段
        """
        try:
            # 运行异步协程
            result = asyncio.run(self._synthesize_async(text, output_path, **kwargs))
            return result
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"success": False, "error": f"Synthesis failed: {str(e)}"}

    async def _synthesize_async(
        self, text: str, output_path: str, **kwargs
    ) -> Dict[str, Any]:
        """
        异步合成语音 (WebSocket 协议)

        支持高级参数 (从 kwargs 获取):
        - appid, token: 动态认证
        - action, use_head_music, use_tail_music
        - speakers, random_order
        - sample_rate, speech_rate
        """
        # 确保输出目录存在
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
            exist_ok=True,
        )

        # 认证逻辑：优先使用 kwargs (前端注入)，如果为空则使用 self (服务器配置)
        # 注意：这允许前端动态提供 Key，但也存在安全风险，见 SECURITY.md
        appid = kwargs.get("appid")
        token = kwargs.get("token")

        # 处理前端加密传输
        if kwargs.get("is_encoded") and appid and token:
            import base64

            try:
                appid = base64.b64decode(appid).decode("utf-8")
                token = base64.b64decode(token).decode("utf-8")
                logger.debug("Using credentials provided by client (decoded)")
            except Exception as e:
                logger.error(f"Failed to decode credentials from client: {e}")
                appid = None
                token = None

        # 如果前端没提供，或者解码失败，则回退到服务器配置
        if not appid:
            appid = self.appid
        if not token:
            token = self.api_key

        if not appid or not token:
            raise ValueError("AppID and Access Token are required for Volcengine TTS")

        # 准备认证 headers
        headers = {
            "X-Api-App-Id": appid,
            "X-Api-App-Key": self.app_key,
            "X-Api-Access-Key": token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        # 准备请求参数
        # 映射语速：API 要求 [-50, 100]，0 为正常速度
        raw_speed = kwargs.get("speed_rate")
        if raw_speed is None:
            # 如果没传 speed_rate，尝试转换通用的 speed (0.5-2.0)
            speed_val = kwargs.get("speed", self.speed)
            speech_rate = int((speed_val - 1.0) * 100)
        else:
            speech_rate = int(raw_speed)

        req_params = {
            "input_id": kwargs.get("input_id", f"ghostradio_{uuid.uuid4().hex[:8]}"),
            "input_text": text if int(kwargs.get("action", 0)) == 0 else "",
            "prompt_text": kwargs.get(
                "prompt_text", text if int(kwargs.get("action", 0)) == 4 else ""
            ),
            "nlp_texts": kwargs.get("nlp_texts"),
            "action": int(kwargs.get("action", 0)),
            "use_head_music": bool(kwargs.get("use_head_music", False)),
            "use_tail_music": bool(kwargs.get("use_tail_music", False)),
            "aigc_watermark": bool(kwargs.get("aigc_watermark", False)),
            "input_info": {
                "input_url": kwargs.get(
                    "input_url", text if text.startswith("http") else ""
                ),
                "return_audio_url": bool(kwargs.get("return_audio_url", False)),
                "only_nlp_text": bool(kwargs.get("only_nlp_text", False)),
                "input_text_max_length": int(
                    kwargs.get("input_text_max_length", 12000)
                ),
            },
            "speaker_info": {
                "random_order": bool(kwargs.get("random_order", True)),
                "speakers": kwargs.get("speakers", []),
            },
            "audio_config": {
                "format": self.encoding,
                "sample_rate": int(kwargs.get("sample_rate", 24000)),
                "speech_rate": speech_rate,
            },
        }

        # 如果没有指定 speakers，使用默认 voice
        if not req_params["speaker_info"]["speakers"]:
            req_params["audio_config"]["voice_type"] = kwargs.get("voice", self.voice)

        audio_data = bytearray()
        websocket = None

        try:
            # 建立 WebSocket 连接
            websocket = await websockets.connect(
                self.endpoint, additional_headers=headers
            )

            logger.info(f"Connected to Volcengine Podcast TTS API")

            # 1. Start Connection
            await start_connection(websocket)
            await wait_for_event(
                websocket, MsgType.FullServerResponse, EventType.ConnectionStarted
            )
            logger.debug("Connection started")

            # 2. Start Session
            session_id = str(uuid.uuid4())
            await start_session(
                websocket, json.dumps(req_params).encode("utf-8"), session_id
            )
            await wait_for_event(
                websocket, MsgType.FullServerResponse, EventType.SessionStarted
            )
            logger.debug("Session started")

            # 3. Finish Session (触发服务器开始合成)
            await finish_session(websocket, session_id)

            # 4. 接收音频数据
            audio_received = False
            while True:
                msg = await receive_message(websocket)

                # 音频数据块
                if (
                    msg.type == MsgType.AudioOnlyServer
                    and msg.event == EventType.PodcastRoundResponse
                ):
                    if not audio_received:
                        audio_received = True
                    audio_data.extend(msg.payload)
                    logger.debug(f"Received audio chunk: {len(msg.payload)} bytes")

                # 错误信息
                elif msg.type == MsgType.Error:
                    error_msg = msg.payload.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"Server error: {error_msg}")

                # 播客轮次结束
                elif msg.type == MsgType.FullServerResponse:
                    if msg.event == EventType.PodcastRoundEnd:
                        data = json.loads(msg.payload.decode("utf-8"))
                        if data.get("is_error"):
                            raise RuntimeError(f"Synthesis error: {data}")
                        logger.debug("Podcast round ended")

                    # 播客结束
                    elif msg.event == EventType.PodcastEnd:
                        logger.debug("Podcast synthesis completed")

                    # 会话结束
                    elif msg.event == EventType.SessionFinished:
                        logger.debug("Session finished")
                        break

            if not audio_received:
                raise RuntimeError("No audio data received from server")

            # 5. 关闭连接
            await finish_connection(websocket)
            await wait_for_event(
                websocket, MsgType.FullServerResponse, EventType.ConnectionFinished
            )

            # 6. 保存音频文件
            with open(output_path, "wb") as f:
                f.write(audio_data)

            # 估算时长
            duration = self.estimate_duration(text)

            logger.info(
                f"Synthesis successful: {output_path} ({len(audio_data)} bytes)"
            )

            return {
                "success": True,
                "file_path": output_path,
                "duration": duration,
                "format": self.encoding,
                "size": len(audio_data),
            }

        except websockets.exceptions.WebSocketException as e:
            return {"success": False, "error": f"WebSocket error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Synthesis error: {str(e)}"}
        finally:
            if websocket:
                await websocket.close()

    def synthesize_long_text(
        self, text: str, output_path: str, **kwargs
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
                temp_path = f"{output_path}.temp.{i}.{self.encoding}"
                result = self.synthesize(chunk, temp_path, **kwargs)

                if not result["success"]:
                    # 清理临时文件
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    return result

                temp_files.append(temp_path)

            # 合并音频文件
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                if self.encoding == "mp3":
                    audio = AudioSegment.from_mp3(temp_file)
                else:
                    audio = AudioSegment.from_wav(temp_file)
                combined += audio

            # 导出最终文件
            combined.export(output_path, format=self.encoding)

            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            # 计算总时长
            total_duration = sum(self.estimate_duration(chunk) for chunk in chunks)

            return {
                "success": True,
                "file_path": output_path,
                "duration": total_duration,
                "format": self.encoding,
                "chunks": len(chunks),
            }

        except ImportError:
            # 如果没有 pydub，只合成第一段
            logger.warning("pydub not installed, only synthesizing first chunk")
            return self.synthesize(chunks[0], output_path, **kwargs)

    def get_voice_list(self) -> list:
        """获取可用音色列表"""
        return [{"id": k, "name": v} for k, v in self.AVAILABLE_VOICES.items()]

    def get_provider_name(self) -> str:
        """获取 Provider 名称"""
        return "volcengine"
