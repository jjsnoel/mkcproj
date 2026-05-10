import os
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="사진수집기", layout="wide")

st.title("사진수집기")
st.caption("facebook_archive 폴더 안의 이미지 파일을 찾아서 data/collected_photos 폴더로 복사합니다.")

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = BASE_DIR / "facebook_archive"
DEFAULT_OUTPUT = BASE_DIR / "data" / "collected_photos"

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"
}

source_text = st.text_input("원본 폴더", value=str(DEFAULT_SOURCE))
output_text = st.text_input("수집 폴더", value=str(DEFAULT_OUTPUT))

source_dir = Path(source_text)
output_dir = Path(output_text)

col1, col2, col3 = st.columns(3)

with col1:
    scan_btn = st.button("사진 찾기", use_container_width=True)

with col2:
    copy_btn = st.button("사진 수집하기", use_container_width=True)

with col3:
    open_info = st.button("폴더 경로 확인", use_container_width=True)

def find_images(folder: Path):
    if not folder.exists():
        return []
    return [
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]

if open_info:
    st.info(f"원본 폴더: {source_dir}")
    st.info(f"수집 폴더: {output_dir}")

if scan_btn:
    images = find_images(source_dir)

    if not source_dir.exists():
        st.error("원본 폴더가 없습니다. facebook_archive 폴더 위치를 확인해주세요.")
    elif not images:
        st.warning("이미지 파일을 찾지 못했습니다.")
    else:
        st.success(f"이미지 {len(images)}개를 찾았습니다.")

        preview_data = []
        for p in images[:300]:
            preview_data.append({
                "파일명": p.name,
                "확장자": p.suffix.lower(),
                "크기KB": round(p.stat().st_size / 1024, 1),
                "경로": str(p.relative_to(source_dir))
            })

        st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

        st.subheader("미리보기")
        preview_images = images[:24]
        cols = st.columns(4)
        for idx, img_path in enumerate(preview_images):
            with cols[idx % 4]:
                try:
                    st.image(str(img_path), caption=img_path.name, use_container_width=True)
                except Exception:
                    st.caption(f"미리보기 실패: {img_path.name}")

if copy_btn:
    images = find_images(source_dir)

    if not source_dir.exists():
        st.error("원본 폴더가 없습니다. facebook_archive 폴더 위치를 확인해주세요.")
    elif not images:
        st.warning("수집할 이미지가 없습니다.")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0
        rows = []

        for img in images:
            rel = img.relative_to(source_dir)
            safe_name = "__".join(rel.parts)
            dest = output_dir / safe_name

            if dest.exists():
                skipped += 1
            else:
                shutil.copy2(img, dest)
                copied += 1

            rows.append({
                "original_path": str(img),
                "collected_path": str(dest),
                "filename": img.name,
                "extension": img.suffix.lower(),
                "size_bytes": img.stat().st_size,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        index_path = output_dir / "photo_index.csv"
        pd.DataFrame(rows).to_csv(index_path, index=False, encoding="utf-8-sig")

        st.success(f"수집 완료: 새로 복사 {copied}개 / 기존 파일 건너뜀 {skipped}개")
        st.info(f"인덱스 저장: {index_path}")

        st.subheader("수집 결과")
        st.dataframe(pd.DataFrame(rows).head(300), use_container_width=True)
