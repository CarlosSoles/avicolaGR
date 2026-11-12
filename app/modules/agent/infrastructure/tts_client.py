# ==============================================================================
# CLIENTE DE SÍNTESIS DE VOZ (TTS) PARA ROXI - EDGE TTS (GRATUITO)
# Archivo: backend/app/modules/agent/infrastructure/tts_client.py
# ==============================================================================

import hashlib
import logging
import re
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger("roxi_tts")

DEFAULT_ROXI_VOICE = "es-CO-SalomeNeural"
# Ritmo ligeramente ágil (+4%) y tono sereno (-2Hz) para suavizar el acento regional
DEFAULT_ROXI_RATE = "+4%"
DEFAULT_ROXI_PITCH = "-2Hz"
MAX_CACHE_ITEMS = 64

_AUDIO_CACHE: "OrderedDict[str, bytes]" = OrderedDict()


def clean_text_for_speech(text: str) -> str:
    """Limpia Markdown, emojis y abreviaturas técnicas para una locución natural."""
    if not text:
        return ""
    cleaned = text
    # Quitar enlaces markdown [texto](url) -> texto
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Quitar encabezados, negritas, cursivas y código
    cleaned = re.sub(r"[`*_~#>]+", " ", cleaned)
    # Quitar emojis y símbolos gráficos fuera de texto latino común
    cleaned = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ.,;:!?¿¡/%+\-()°]", " ", cleaned)
    # Reemplazos de unidades para lectura fluida
    cleaned = re.sub(r"\bkg\b", "kilos", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bkm\b", "kilómetros", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 420:
        cleaned = cleaned[:417].rsplit(" ", 1)[0] + "."
    return cleaned


async def synthesize_speech_mp3(
    text: str,
    voice: Optional[str] = None,
    rate: str = DEFAULT_ROXI_RATE,
    pitch: str = DEFAULT_ROXI_PITCH,
) -> bytes:
    """
    Genera audio MP3 usando edge-tts (es-CO-SalomeNeural por defecto).
    Lanza RuntimeError si edge-tts no está instalado o falla la conexión.
    """
    spoken = clean_text_for_speech(text)
    if not spoken:
        raise ValueError("El texto para sintetizar está vacío.")

    selected_voice = (voice or DEFAULT_ROXI_VOICE).strip() or DEFAULT_ROXI_VOICE
    cache_key = hashlib.sha256(f"{selected_voice}|{rate}|{pitch}|{spoken}".encode("utf-8")).hexdigest()

    if cache_key in _AUDIO_CACHE:
        _AUDIO_CACHE.move_to_end(cache_key)
        return _AUDIO_CACHE[cache_key]

    try:
        import edge_tts  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "El paquete 'edge-tts' no está instalado en el entorno Python del backend."
        ) from exc

    try:
        communicate = edge_tts.Communicate(
            text=spoken,
            voice=selected_voice,
            rate=rate,
            pitch=pitch,
        )
        chunks = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                chunks.append(chunk["data"])
        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            raise RuntimeError("edge-tts devolvió un flujo de audio vacío.")
    except Exception as exc:
        logger.warning("Fallo en edge-tts (%s): %s", selected_voice, exc)
        raise RuntimeError(f"No se pudo sintetizar audio con edge-tts: {exc}") from exc

    _AUDIO_CACHE[cache_key] = audio_bytes
    if len(_AUDIO_CACHE) > MAX_CACHE_ITEMS:
        _AUDIO_CACHE.popitem(last=False)

    return audio_bytes

