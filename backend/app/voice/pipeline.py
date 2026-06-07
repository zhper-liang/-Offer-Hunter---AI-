"""语音管线编排 - STT → Agent → TTS（带自动 fallback）"""

import logging

from app.config.settings import settings
from app.voice.base import STTProvider, TTSProvider

logger = logging.getLogger(__name__)

# 优先级顺序: 讯飞 → 百度
_STT_PROVIDERS = [
    ("iflytek", lambda: __import__("app.voice.iflytek_stt", fromlist=["IflytekSTT"]).IflytekSTT()),
    ("baidu", lambda: __import__("app.voice.baidu_voice", fromlist=["BaiduSTT"]).BaiduSTT()),
]
_TTS_PROVIDERS = [
    ("iflytek", lambda: __import__("app.voice.iflytek_tts", fromlist=["IflytekTTS"]).IflytekTTS()),
    ("baidu", lambda: __import__("app.voice.baidu_voice", fromlist=["BaiduTTS"]).BaiduTTS()),
]


def _has_config(name: str) -> bool:
    if name == "iflytek":
        return bool(settings.iflytek_app_id)
    if name == "baidu":
        return bool(settings.baidu_api_key)
    return False


def get_stt_provider() -> STTProvider:
    """获取 STT 提供商（按优先级尝试，自动 fallback）"""
    for name, factory in _STT_PROVIDERS:
        if _has_config(name):
            try:
                return factory()
            except Exception as e:
                logger.warning(f"STT 提供商 {name} 初始化失败: {e}")
    raise RuntimeError("未配置语音识别服务 (需要讯飞或百度 API Key)")


def get_tts_provider() -> TTSProvider:
    """获取 TTS 提供商（按优先级尝试，自动 fallback）"""
    for name, factory in _TTS_PROVIDERS:
        if _has_config(name):
            try:
                return factory()
            except Exception as e:
                logger.warning(f"TTS 提供商 {name} 初始化失败: {e}")
    raise RuntimeError("未配置语音合成服务 (需要讯飞或百度 API Key)")


def _fallback_providers(providers: list, current_name: str) -> list:
    """返回当前提供商之后的 fallback 列表"""
    started = False
    result = []
    for name, factory in providers:
        if name == current_name:
            started = True
            continue
        if started and _has_config(name):
            result.append((name, factory))
    return result


class VoicePipeline:
    """语音面试管线: 音频输入 → 文本 → Agent 处理 → 文本 → 音频输出（自动 fallback）"""

    def __init__(self):
        self._stt = get_stt_provider()
        self._tts = get_tts_provider()
        self._stt_name = self._detect_provider_name(self._stt)
        self._tts_name = self._detect_provider_name(self._tts)

    @staticmethod
    def _detect_provider_name(provider) -> str:
        cls_name = type(provider).__name__.lower()
        if "iflytek" in cls_name:
            return "iflytek"
        if "baidu" in cls_name:
            return "baidu"
        return "unknown"

    def _try_fallback_stt(self):
        """尝试 fallback 到下一个 STT 提供商"""
        for name, factory in _fallback_providers(_STT_PROVIDERS, self._stt_name):
            try:
                self._stt = factory()
                old = self._stt_name
                self._stt_name = name
                logger.info(f"STT fallback: {old} → {name}")
                return True
            except Exception as e:
                logger.warning(f"STT fallback {name} 也失败: {e}")
        return False

    def _try_fallback_tts(self):
        """尝试 fallback 到下一个 TTS 提供商"""
        for name, factory in _fallback_providers(_TTS_PROVIDERS, self._tts_name):
            try:
                self._tts = factory()
                old = self._tts_name
                self._tts_name = name
                logger.info(f"TTS fallback: {old} → {name}")
                return True
            except Exception as e:
                logger.warning(f"TTS fallback {name} 也失败: {e}")
        return False

    async def audio_to_text(self, audio_data: bytes) -> str:
        """音频 → 文本（失败自动 fallback）"""
        try:
            return await self._stt.recognize(audio_data)
        except Exception as e:
            logger.warning(f"STT ({self._stt_name}) 失败: {e}")
            if self._try_fallback_stt():
                return await self._stt.recognize(audio_data)
            raise

    async def text_to_audio(self, text: str, voice: str = "xiaoyan") -> bytes:
        """文本 → 音频（失败自动 fallback）"""
        try:
            return await self._tts.synthesize(text, voice)
        except Exception as e:
            logger.warning(f"TTS ({self._tts_name}) 失败: {e}")
            if self._try_fallback_tts():
                return await self._tts.synthesize(text, voice)
            raise

    async def text_to_audio_stream(self, text: str, voice: str = "xiaoyan"):
        """文本 → 流式音频（失败自动 fallback）"""
        try:
            async for chunk in self._tts.synthesize_stream(text, voice):
                yield chunk
        except Exception as e:
            logger.warning(f"TTS stream ({self._tts_name}) 失败: {e}")
            if self._try_fallback_tts():
                async for chunk in self._tts.synthesize_stream(text, voice):
                    yield chunk
            else:
                raise
