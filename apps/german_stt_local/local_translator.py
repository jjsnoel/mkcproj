from __future__ import annotations

import json
import os
from typing import Callable
from urllib import parse, request
from urllib.error import HTTPError, URLError

import torch


Progress = Callable[[str], None]


# Balanced default for local GPU/CPU use.
# First run downloads the model from Hugging Face. After that it is cached locally.
DEFAULT_MODEL = "facebook/nllb-200-distilled-600M"

LANG_CODES = {
    "de": "deu_Latn",
    "en": "eng_Latn",
    "ko": "kor_Hang",
}

DEEPL_SOURCE_LANG_CODES = {
    "de": "DE",
    "en": "EN",
    "ko": "KO",
}

DEEPL_TARGET_LANG_CODES = {
    "de": "DE",
    "en": "EN-US",
    "ko": "KO",
}


class DeepLTranslationError(RuntimeError):
    pass


def deepl_auth_key() -> str:
    for name in ("DEEPL_API_KEY", "DEEPL_AUTH_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            os.environ["DEEPL_API_KEY"] = value
            return value
    return ""


def deepl_api_url(auth_key: str) -> str:
    configured = os.environ.get("DEEPL_API_URL", "").strip().rstrip("/")
    if configured:
        return configured
    plan = os.environ.get("DEEPL_API_PLAN", "").strip().lower()
    if plan == "pro" or auth_key.endswith(":fx") is False:
        return "https://api.deepl.com"
    return "https://api-free.deepl.com"


def translate_texts_deepl(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    batch_size: int = 25,
    progress: Progress | None = None,
) -> list[str]:
    auth_key = deepl_auth_key()
    if not auth_key:
        raise DeepLTranslationError("DEEPL_API_KEY is not set.")

    try:
        source_code = DEEPL_SOURCE_LANG_CODES[source_lang]
        target_code = DEEPL_TARGET_LANG_CODES[target_lang]
    except KeyError as exc:
        raise DeepLTranslationError(f"Unsupported DeepL language: {exc.args[0]}") from exc

    endpoint = f"{deepl_api_url(auth_key)}/v2/translate"
    clean_texts = [str(t or "").strip() for t in texts]
    outputs = [""] * len(clean_texts)

    non_empty = [(i, text) for i, text in enumerate(clean_texts) if text]
    for start in range(0, len(non_empty), batch_size):
        batch = non_empty[start : start + batch_size]
        if progress:
            progress(f"{source_lang} -> {target_lang} DeepL 번역 중... {start + len(batch)}/{len(non_empty)}")

        data = parse.urlencode(
            {
                "source_lang": source_code,
                "target_lang": target_code,
                "preserve_formatting": "1",
                "text": [text for _, text in batch],
            },
            doseq=True,
        ).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={"Authorization": f"DeepL-Auth-Key {auth_key}"},
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeepLTranslationError(f"DeepL HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise DeepLTranslationError(f"DeepL request failed: {exc.reason}") from exc

        translated = [item.get("text", "").strip() for item in payload.get("translations", [])]
        if len(translated) != len(batch):
            raise DeepLTranslationError("DeepL returned an unexpected number of translations.")

        for (index, _), text in zip(batch, translated):
            outputs[index] = text

    return outputs


class LocalNLLBTranslator:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        progress: Progress | None = None,
        require_gpu: bool = True,
    ):
        self.model_name = model_name
        cuda_available = torch.cuda.is_available()
        if require_gpu and not cuda_available:
            raise RuntimeError(
                "CUDA GPU를 사용할 수 없어 Facebook/NLLB 번역을 중단했습니다. CPU 실행은 비활성화되어 있습니다."
            )
        self.device = "cuda" if cuda_available else "cpu"

        if progress:
            progress(f"로컬 번역 모델 로딩 중: {model_name} / 장치: {self.device}")
            progress("처음 실행이면 모델 다운로드 때문에 시간이 오래 걸릴 수 있어요.")

        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=dtype)
        self.model.to(self.device)
        self.model.eval()

    def translate_texts(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        batch_size: int = 4,
        progress: Progress | None = None,
    ) -> list[str]:
        src = LANG_CODES[source_lang]
        tgt = LANG_CODES[target_lang]

        self.tokenizer.src_lang = src

        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt)
        outputs: list[str] = []

        clean_texts = [str(t or "").strip() for t in texts]

        for start in range(0, len(clean_texts), batch_size):
            batch = clean_texts[start : start + batch_size]

            if progress:
                progress(f"{source_lang} → {target_lang} 로컬 번역 중... {start + len(batch)}/{len(clean_texts)}")

            # Empty subtitles stay empty.
            non_empty_indices = [i for i, text in enumerate(batch) if text]
            non_empty_texts = [batch[i] for i in non_empty_indices]

            translated_batch = [""] * len(batch)

            if non_empty_texts:
                encoded = self.tokenizer(
                    non_empty_texts,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=256,
                )
                encoded = {k: v.to(self.device) for k, v in encoded.items()}

                with torch.inference_mode():
                    generated = self.model.generate(
                        **encoded,
                        forced_bos_token_id=forced_bos_token_id,
                        max_new_tokens=160,
                        num_beams=5,
                        no_repeat_ngram_size=3,
                    )

                decoded = self.tokenizer.batch_decode(generated, skip_special_tokens=True)

                for local_i, text in zip(non_empty_indices, decoded):
                    translated_batch[local_i] = text.strip()

            outputs.extend(translated_batch)

        return outputs


def translate_segments_local(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 4,
    require_gpu: bool = True,
    progress: Progress | None = None,
) -> list[dict]:
    translator = LocalNLLBTranslator(model_name=model_name, progress=progress, require_gpu=require_gpu)
    texts = [seg["text"] for seg in segments]

    translated_texts = translator.translate_texts(
        texts,
        source_lang=source_lang,
        target_lang=target_lang,
        batch_size=batch_size,
        progress=progress,
    )

    result = []
    for seg, text in zip(segments, translated_texts):
        new_seg = dict(seg)
        new_seg["text"] = text
        result.append(new_seg)

    return result


def translate_segments_auto(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 4,
    require_gpu: bool = True,
    progress: Progress | None = None,
) -> tuple[list[dict], str]:
    texts = [seg["text"] for seg in segments]

    try:
        if progress:
            progress(f"{source_lang} -> {target_lang} DeepL 번역을 먼저 시도합니다.")
        translated_texts = translate_texts_deepl(
            texts,
            source_lang=source_lang,
            target_lang=target_lang,
            batch_size=25,
            progress=progress,
        )
        provider = "deepl"
    except DeepLTranslationError as exc:
        if progress:
            progress(f"DeepL 번역 실패 또는 한도 소진: {exc}")
            progress("기존 Facebook/NLLB 로컬 번역으로 전환합니다.")
        fallback_segments = translate_segments_local(
            segments,
            source_lang=source_lang,
            target_lang=target_lang,
            model_name=model_name,
            batch_size=batch_size,
            require_gpu=require_gpu,
            progress=progress,
        )
        return fallback_segments, "facebook/nllb"

    result = []
    for seg, text in zip(segments, translated_texts):
        new_seg = dict(seg)
        new_seg["text"] = text
        result.append(new_seg)

    return result, provider
