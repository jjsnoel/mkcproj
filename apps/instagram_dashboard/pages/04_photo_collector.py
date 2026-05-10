from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="사진수집기", layout="wide")

st.title("사진수집기")
st.caption("00_INBOX/images의 이미지를 기존 Muenchner Knabenchor 아카이브 규칙으로 정리합니다.")


def toolkit_root() -> Path:
    env_root = os.environ.get("MUNICH_TOOLKIT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    # this file: toolkit/apps/instagram_dashboard/pages/04_photo_collector.py
    return Path(__file__).resolve().parents[3]


ROOT = toolkit_root()
DEFAULT_ARCHIVE_ROOT = ROOT / "modules" / "facebook_archive" / "Muenchner_Knabenchor_Archive"
DEFAULT_MANAGER_DIR = ROOT / "modules" / "facebook_archive"
FALLBACK_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


def load_archive_manager(manager_dir: Path):
    manager_dir = manager_dir.expanduser().resolve()
    if str(manager_dir) not in sys.path:
        sys.path.insert(0, str(manager_dir))
    import archive_manager  # type: ignore

    return archive_manager


def inbox_images(archive_root: Path, image_exts: set[str]) -> list[Path]:
    images_dir = archive_root / "00_INBOX" / "images"
    if not images_dir.exists():
        return []
    return sorted(
        [path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in image_exts],
        key=lambda path: path.name.casefold(),
    )


def default_title(caption: str, image_count: int) -> str:
    compact = " ".join(caption.split())
    if compact:
        return compact[:70].strip(" .,-_/\\")
    return "No Caption Photo" if image_count == 1 else "No Caption Photos"


def unique_destination(images_dir: Path, filename: str) -> Path:
    original = Path(filename)
    stem = original.stem or "uploaded_image"
    suffix = original.suffix.lower()
    candidate = images_dir / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = images_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def save_uploaded_images(archive_root: Path, uploaded_files, image_exts: set[str]) -> list[Path]:
    images_dir = archive_root / "00_INBOX" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for uploaded_file in uploaded_files:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in image_exts:
            raise ValueError(f"지원하지 않는 이미지 형식입니다: {uploaded_file.name}")

        destination = unique_destination(images_dir, uploaded_file.name)
        destination.write_bytes(uploaded_file.getbuffer())
        saved_paths.append(destination)

    return saved_paths


def read_master_index(archive_root: Path) -> pd.DataFrame:
    index_path = archive_root / "03_INDEX" / "master_index.csv"
    if not index_path.exists():
        return pd.DataFrame()
    return pd.read_csv(index_path, dtype=str).fillna("")


with st.sidebar:
    st.subheader("Archive Settings")
    st.caption(f"Toolkit root: {ROOT}")
    archive_root_text = st.text_input("아카이브 루트", value=str(DEFAULT_ARCHIVE_ROOT))
    manager_dir_text = st.text_input("archive_manager.py 폴더", value=str(DEFAULT_MANAGER_DIR))
    clear_inbox = st.checkbox("처리 후 00_INBOX 비우기", value=True)

archive_root = Path(archive_root_text).expanduser()
manager_dir = Path(manager_dir_text).expanduser()

try:
    archive_manager = load_archive_manager(manager_dir)
    image_exts = set(getattr(archive_manager, "IMAGE_EXTENSIONS", FALLBACK_IMAGE_EXTS))
except Exception as exc:
    archive_manager = None
    image_exts = FALLBACK_IMAGE_EXTS
    st.error(f"archive_manager.py를 불러오지 못했습니다: {exc}")

images = inbox_images(archive_root, image_exts)

st.markdown("""
### 사용 흐름
1. 아래 폴더에 새 사진을 넣습니다.  
2. 게시일/제목/캡션을 입력합니다.  
3. 버튼을 누르면 `01_ORIGINAL_BY_YEAR/YYYY/post/images/001.jpg` 구조로 정리됩니다.
""")
st.code(str(archive_root / "00_INBOX" / "images"), language="text")

uploaded_images = st.file_uploader(
    "이미지 업로드",
    type=sorted(ext.lstrip(".") for ext in image_exts),
    accept_multiple_files=True,
    help="선택한 이미지는 00_INBOX/images에 저장됩니다.",
)

upload_col, _ = st.columns([1, 3])
with upload_col:
    save_uploads = st.button(
        "업로드 이미지를 인박스에 저장",
        disabled=not uploaded_images,
        use_container_width=True,
    )

if save_uploads and uploaded_images:
    try:
        saved = save_uploaded_images(archive_root, uploaded_images, image_exts)
    except Exception as exc:
        st.error(f"업로드 저장 실패: {exc}")
        st.exception(exc)
    else:
        st.success(f"{len(saved)}개 이미지를 인박스에 저장했습니다.")
        st.dataframe(
            pd.DataFrame({"saved_to": [str(path) for path in saved]}),
            use_container_width=True,
            hide_index=True,
        )
        images = inbox_images(archive_root, image_exts)

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Inbox Images", len(images))
col_b.metric("Archive Exists", "yes" if archive_root.exists() else "no")
col_c.metric("Manager Exists", "yes" if (manager_dir / "archive_manager.py").exists() else "no")
col_d.metric("Clear Inbox", "yes" if clear_inbox else "no")

with st.expander("현재 인박스 이미지", expanded=True):
    if not (archive_root / "00_INBOX" / "images").exists():
        st.warning("00_INBOX/images 폴더가 없습니다. 아카이브 루트 경로를 확인하세요.")
    elif not images:
        st.info("현재 인박스에 이미지가 없습니다.")
    else:
        rows = [
            {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "size_kb": round(path.stat().st_size / 1024, 1),
                "path": str(path),
            }
            for path in images
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        preview_cols = st.columns(4)
        for idx, img_path in enumerate(images[:12]):
            with preview_cols[idx % 4]:
                try:
                    st.image(str(img_path), caption=img_path.name, use_container_width=True)
                except Exception:
                    st.caption(f"미리보기 실패: {img_path.name}")

st.subheader("새 게시물로 정리")

post_date = st.text_input(
    "게시일",
    value="",
    placeholder="예: 2024년 12월 15일, Dec 15 2024, 15.12.2024",
)
caption_text = st.text_area("원문 캡션 (없으면 비워두기)", height=160)
computed_title = default_title(caption_text, len(images))
post_title = st.text_input("게시물 제목", value=computed_title)
source_url = st.text_input("Source URL", value="TEMP_URL")

with st.expander("선택 메타데이터", expanded=False):
    category = st.text_input("Category", value="Unknown")
    event = st.text_input("Event", value="")
    location = st.text_input("Location", value="")
    mood = st.text_input("Mood", value="")
    reels_usable = st.selectbox("Reels Usable", ["maybe", "yes", "no"], index=0)

process_btn = st.button("기존 아카이브 규칙으로 정리하기", type="primary", use_container_width=True)

if process_btn:
    if archive_manager is None:
        st.error("archive_manager.py를 먼저 불러와야 합니다.")
    elif not archive_root.exists():
        st.error(f"아카이브 루트가 없습니다: {archive_root}")
    elif not post_date.strip():
        st.error("게시일을 입력하세요.")
    elif not images:
        st.warning("처리할 인박스 이미지가 없습니다.")
    else:
        try:
            result = archive_manager.archive_inbox_post(
                archive_root=archive_root,
                date_text=post_date.strip(),
                title=post_title.strip(),
                source_url=source_url.strip(),
                caption_text=caption_text.strip(),
                category=category.strip(),
                event=event.strip(),
                location=location.strip(),
                mood=mood.strip(),
                reels_usable=reels_usable,
                clear_inbox=clear_inbox,
            )
        except Exception as exc:
            st.error(f"처리 실패: {exc}")
            st.exception(exc)
        else:
            st.success("아카이브 정리 완료")
            m1, m2, m3 = st.columns(3)
            m1.metric("처리된 이미지 수", result.get("image_count", 0))
            m2.metric("생성된 게시물 폴더 수", result.get("created_post_folder_count", 0))
            m3.metric("삭제된 인박스 파일", result.get("deleted_inbox_count", 0))
            st.info(f"출력 경로: {result.get('post_folder')}")
            st.caption(f"마스터 인덱스: {result.get('master_index')}")
            copied = result.get("copied_images", [])
            if copied:
                st.dataframe(pd.DataFrame({"copied_images": copied}), use_container_width=True, hide_index=True)

st.subheader("최근 아카이브 인덱스")
index_df = read_master_index(archive_root)
if index_df.empty:
    st.info("master_index.csv가 없거나 비어 있습니다.")
else:
    show_cols = [col for col in ["date", "year", "post_folder", "post_title", "image_count", "category", "caption_summary"] if col in index_df.columns]
    st.dataframe(index_df[show_cols].tail(20), use_container_width=True, hide_index=True)
