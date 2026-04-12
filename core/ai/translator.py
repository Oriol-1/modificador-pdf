"""Traductor de documentos PDF usando LLM.

Traduce texto preservando contexto semántico mediante
modelos de lenguaje.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable
import logging

from core.ai.ai_config import AIConfig, LLMProvider
from core.ai.chat_engine import call_openai, call_ollama

logger = logging.getLogger(__name__)


class TranslationLanguage(Enum):
    """Idiomas soportados para traducción."""
    SPANISH = "Español"
    ENGLISH = "English"
    FRENCH = "Français"
    GERMAN = "Deutsch"
    ITALIAN = "Italiano"
    PORTUGUESE = "Português"
    CHINESE = "中文"
    JAPANESE = "日本語"
    KOREAN = "한국어"
    ARABIC = "العربية"
    RUSSIAN = "Русский"
    DUTCH = "Nederlands"
    POLISH = "Polski"
    TURKISH = "Türkçe"
    HINDI = "हिन्दी"


@dataclass
class TranslationRequest:
    """Solicitud de traducción de texto.

    Attributes:
        text: Texto a traducir.
        source_lang: Idioma de origen.
        target_lang: Idioma de destino.
        page_num: Número de página (0-based).
    """
    text: str
    source_lang: TranslationLanguage
    target_lang: TranslationLanguage
    page_num: int = 0


@dataclass
class TranslationResult:
    """Resultado de una traducción.

    Attributes:
        original: Texto original.
        translated: Texto traducido.
        source_lang: Idioma de origen.
        target_lang: Idioma de destino.
        page_num: Número de página.
        success: Si la traducción fue exitosa.
        error: Mensaje de error si falló.
    """
    original: str
    translated: str
    source_lang: TranslationLanguage
    target_lang: TranslationLanguage
    page_num: int = 0
    success: bool = True
    error: str = ""


def translate_text(
    request: TranslationRequest,
    config: AIConfig,
) -> TranslationResult:
    """Traduce texto usando el LLM configurado.

    Args:
        request: Solicitud de traducción.
        config: Configuración de IA.

    Returns:
        TranslationResult con el texto traducido.
    """
    messages = [
        {
            "role": "system",
            "content": (
                f"Eres un traductor profesional. Traduce el siguiente texto "
                f"de {request.source_lang.value} a {request.target_lang.value}. "
                f"Mantén el formato original. Solo devuelve la traducción, "
                f"sin explicaciones adicionales."
            ),
        },
        {
            "role": "user",
            "content": request.text,
        },
    ]

    try:
        if config.llm_provider == LLMProvider.OPENAI:
            translated = call_openai(messages, config)
        elif config.llm_provider == LLMProvider.OLLAMA:
            translated = call_ollama(messages, config)
        else:
            return TranslationResult(
                original=request.text,
                translated="",
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                page_num=request.page_num,
                success=False,
                error="No hay proveedor de IA configurado",
            )

        return TranslationResult(
            original=request.text,
            translated=translated.strip(),
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            page_num=request.page_num,
        )
    except Exception as e:
        logger.error(f"Error en traducción: {e}")
        return TranslationResult(
            original=request.text,
            translated="",
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            page_num=request.page_num,
            success=False,
            error=str(e),
        )


def translate_pages(
    page_texts: List[str],
    source_lang: TranslationLanguage,
    target_lang: TranslationLanguage,
    config: AIConfig,
    progress_callback: Optional[Callable] = None,
) -> List[TranslationResult]:
    """Traduce múltiples páginas del documento.

    Args:
        page_texts: Textos de cada página.
        source_lang: Idioma de origen.
        target_lang: Idioma de destino.
        config: Configuración de IA.
        progress_callback: Callback de progreso (page_num, total).

    Returns:
        Lista de TranslationResult, uno por página.
    """
    results = []
    total = len(page_texts)

    for i, text in enumerate(page_texts):
        if progress_callback:
            progress_callback(i, total)

        if not text.strip():
            results.append(TranslationResult(
                original=text,
                translated="",
                source_lang=source_lang,
                target_lang=target_lang,
                page_num=i,
            ))
            continue

        request = TranslationRequest(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            page_num=i,
        )
        result = translate_text(request, config)
        results.append(result)

    if progress_callback:
        progress_callback(total, total)

    logger.info(f"Traducción completada: {total} páginas")
    return results
