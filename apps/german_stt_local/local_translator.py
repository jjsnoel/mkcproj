from __future__ import annotations

from typing import Callable

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


Progress = Callable[[str], None]


# Balanced default for local GPU/CPU use.
# First run downloads the model from Hugging Face. After that it is cached locally.
DEFAULT_MODEL = "facebook/nllb-200-distilled-600M"

LANG_CODES = {
    "de": "deu_Latn",
    "en": "eng_Latn",
    "ko": "kor_Hang",
}


class LocalNLLBTranslator:
    def __init__(self, model_name: str = DEFAULT_MODEL, progress: Progress | None = None):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if progress:
            progress(f"로컬 번역 모델 로딩 중: {model_name} / 장치: {self.device}")
            progress("처음 실행이면 모델 다운로드 때문에 시간이 오래 걸릴 수 있어요.")

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
    progress: Progress | None = None,
) -> list[dict]:
    translator = LocalNLLBTranslator(model_name=model_name, progress=progress)
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
