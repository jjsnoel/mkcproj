from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import streamlit as st

from facebook_archive.archive_manager import (
    ARCHIVE_ROOT_NAME,
    IMAGE_EXTENSIONS,
    SUPPORTED_THEMES,
    ArchiveError,
    command_clear_inbox,
    command_curate,
    command_dedupe,
    command_new_post,
    command_rebuild_index,
    inbox_files,
    init_archive,
    list_image_files_recursive,
    relative_to_archive,
    scan_posts,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ARCHIVE_ROOT = BASE_DIR / ARCHIVE_ROOT_NAME


def _capture_command(func, args: SimpleNamespace) -> tuple[int, str]:
    """Run an archive_manager command and capture user-facing output."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = func(args)
    return code, output.getvalue().strip()


def _get_archive_root() -> Path:
    with st.sidebar.expander("Facebook 아카이브 경로", expanded=False):
        raw_path = st.text_input(
            "아카이브 폴더",
            value=str(DEFAULT_ARCHIVE_ROOT),
            help="실제 사진 원본은 이 로컬 폴더에 저장됩니다. GitHub에는 올리지 않는 폴더입니다.",
        )
    return Path(raw_path).expanduser().resolve()


def _archive_status(root: Path) -> dict[str, object]:
    rows = scan_posts(root) if root.exists() else []
    image_count = len(list_image_files_recursive(root)) if root.exists() else 0
    return {
        "ready": (root / "00_INBOX").exists() and (root / "01_ORIGINAL_BY_YEAR").exists(),
        "posts": len(rows),
        "images": image_count,
        "index": root / "03_INDEX" / "master_index.csv",
    }


def _save_uploaded_images(uploaded_images, temp_dir: Path) -> Path:
    images_dir = temp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for index, uploaded in enumerate(uploaded_images, start=1):
        original_name = Path(uploaded.name).name
        suffix = Path(original_name).suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            continue
        safe_name = f"{index:03d}_{original_name}"
        (images_dir / safe_name).write_bytes(uploaded.getbuffer())

    return images_dir


def _save_caption_file(caption_text: str, caption_upload, temp_dir: Path) -> Path | None:
    if caption_upload is not None:
        caption_path = temp_dir / Path(caption_upload.name).name
        caption_path.write_bytes(caption_upload.getbuffer())
        return caption_path

    if caption_text.strip():
        caption_path = temp_dir / "caption_original.txt"
        caption_path.write_text(caption_text.strip() + "\n", encoding="utf-8")
        return caption_path

    return None


def _render_setup(root: Path) -> None:
    status = _archive_status(root)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("아카이브 상태", "준비됨" if status["ready"] else "미생성")
    c2.metric("저장 포스트", f"{status['posts']:,}")
    c3.metric("이미지 파일", f"{status['images']:,}")
    c4.metric("GitHub 업로드", "제외 대상")

    st.caption(f"현재 아카이브 경로: `{root}`")

    if st.button("아카이브 폴더 초기화/확인", type="primary"):
        try:
            created_root = init_archive(root)
            st.success(f"아카이브 준비 완료: {created_root}")
        except Exception as exc:  # noqa: BLE001 - user-facing Streamlit error
            st.error(f"아카이브 초기화 실패: {exc}")


def _render_new_post(root: Path) -> None:
    st.markdown("### 새 Facebook 사진 포스트 저장")
    st.caption("브라우저에서 직접 저장한 사진과 수동 복사한 캡션을 로컬 아카이브 구조로 정리합니다.")

    with st.form("facebook_archive_new_post", clear_on_submit=False):
        col_date, col_reels = st.columns([1, 1])
        post_date = col_date.date_input("게시일")
        reels_usable = col_reels.selectbox("릴스 활용 가능성", ["maybe", "yes", "no"], index=0)

        title = st.text_input(
            "포스트 제목",
            placeholder="예: Christmas Concert 2014",
            help="폴더명으로도 쓰이니 짧은 영어 제목이 좋습니다.",
        )
        source_url = st.text_input("원본 Facebook URL", placeholder="https://www.facebook.com/...")

        images = st.file_uploader(
            "사진 파일 업로드",
            type=[ext.lstrip(".") for ext in sorted(IMAGE_EXTENSIONS)],
            accept_multiple_files=True,
        )

        caption_text = st.text_area(
            "원문 캡션 직접 붙여넣기",
            placeholder="Facebook 게시물 캡션을 여기에 붙여넣거나 아래에 txt 파일을 올리세요.",
            height=140,
        )
        caption_file = st.file_uploader("캡션 .txt 파일", type=["txt"], accept_multiple_files=False)

        c1, c2, c3, c4 = st.columns(4)
        category = c1.text_input("카테고리", placeholder="concert")
        event = c2.text_input("행사/공연", placeholder="Christmas Concert")
        location = c3.text_input("장소", placeholder="Munich")
        mood = c4.text_input("분위기", placeholder="warm, sacred")

        submitted = st.form_submit_button("아카이브에 저장", type="primary")

    if not submitted:
        return

    if not title.strip():
        st.error("포스트 제목은 필요합니다.")
        return
    if not images:
        st.error("사진 파일을 최소 1개 올려야 합니다.")
        return

    try:
        init_archive(root)
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            images_dir = _save_uploaded_images(images, temp_dir)
            caption_path = _save_caption_file(caption_text, caption_file, temp_dir)

            args = SimpleNamespace(
                archive_root=str(root),
                date=str(post_date),
                title=title.strip(),
                url=source_url.strip(),
                images=str(images_dir),
                caption=str(caption_path) if caption_path else None,
                category=category.strip(),
                event=event.strip(),
                location=location.strip(),
                mood=mood.strip(),
                reels_usable=reels_usable,
            )
            _, output = _capture_command(command_new_post, args)

        st.success("새 포스트를 아카이브에 저장했습니다.")
        if output:
            st.code(output)
    except ArchiveError as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001
        st.error(f"저장 실패: {exc}")


def _render_post_list(root: Path) -> None:
    st.markdown("### 아카이브 목록/인덱스")

    c1, c2 = st.columns([1, 3])
    if c1.button("master_index.csv 재생성"):
        try:
            args = SimpleNamespace(archive_root=str(root))
            _, output = _capture_command(command_rebuild_index, args)
            st.success("인덱스를 다시 만들었습니다.")
            if output:
                st.code(output)
        except Exception as exc:  # noqa: BLE001
            st.error(f"인덱스 재생성 실패: {exc}")

    rows = scan_posts(root) if root.exists() else []
    if not rows:
        st.info("아직 저장된 포스트가 없습니다. 먼저 새 포스트를 추가하세요.")
        return

    df = pd.DataFrame(rows)
    if "date" in df.columns:
        df = df.sort_values(["date", "post_folder"], ascending=[False, False])

    st.dataframe(df, use_container_width=True, height=420)

    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "현재 아카이브 목록 CSV 다운로드",
        data=csv_data,
        file_name="facebook_archive_master_index.csv",
        mime="text/csv",
    )


def _render_curate(root: Path) -> None:
    st.markdown("### 릴스 후보/테마 폴더로 큐레이션")
    st.caption("원본 이미지는 그대로 두고, 테마 폴더에는 복사본만 만듭니다.")

    original_root = root / "01_ORIGINAL_BY_YEAR"
    images = [p for p in list_image_files_recursive(original_root) if p.is_file()] if original_root.exists() else []

    if not images:
        st.info("큐레이션할 원본 이미지가 아직 없습니다.")
        return

    label_to_path = {relative_to_archive(path, root): path for path in images}
    selected_label = st.selectbox("원본 이미지 선택", list(label_to_path.keys()))
    selected_path = label_to_path[selected_label]

    preview_col, form_col = st.columns([1, 2])
    with preview_col:
        st.caption("선택 이미지 미리보기")
        try:
            st.image(str(selected_path), use_container_width=True)
        except Exception:
            st.info("이 파일 형식은 브라우저 미리보기를 지원하지 않을 수 있습니다.")
        st.code(selected_label)

    with form_col:
        theme = st.selectbox("테마", SUPPORTED_THEMES)
        use_case = st.text_input("릴스 활용 아이디어", placeholder="예: then_and_now_opening")
        notes = st.text_area("메모", height=90)
        mode = st.radio("저장 방식", ["copy", "hardlink"], horizontal=True, index=0)

        if st.button("선택 이미지를 테마 폴더에 추가", type="primary"):
            try:
                args = SimpleNamespace(
                    archive_root=str(root),
                    original=str(selected_path),
                    theme=theme,
                    use_case=use_case.strip(),
                    notes=notes.strip(),
                    mode=mode,
                )
                _, output = _capture_command(command_curate, args)
                st.success("테마 폴더에 추가했습니다.")
                if output:
                    st.code(output)
            except Exception as exc:  # noqa: BLE001
                st.error(f"큐레이션 실패: {exc}")


def _render_maintenance(root: Path) -> None:
    st.markdown("### 중복 검사 / INBOX 정리")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 중복 이미지 검사")
        if st.button("중복 검사 실행"):
            try:
                args = SimpleNamespace(archive_root=str(root))
                _, output = _capture_command(command_dedupe, args)
                st.success("중복 검사를 완료했습니다.")
                if output:
                    st.code(output)
            except Exception as exc:  # noqa: BLE001
                st.error(f"중복 검사 실패: {exc}")

        duplicate_path = root / "03_INDEX" / "duplicate_report.csv"
        if duplicate_path.exists():
            duplicate_df = pd.read_csv(duplicate_path)
            st.dataframe(duplicate_df, use_container_width=True, height=260)

    with c2:
        st.markdown("#### INBOX 파일")
        target = st.selectbox("대상", ["all", "images", "captions"], index=0)
        files = inbox_files(root, target) if root.exists() else []
        st.caption(f"선택 대상 파일: {len(files)}개")
        if files:
            st.code("\n".join(relative_to_archive(path, root) for path in files[:80]))
            if len(files) > 80:
                st.caption("80개까지만 미리보기로 표시했습니다.")

        dry_run = st.checkbox("삭제하지 않고 미리보기만", value=True)
        confirm_delete = st.checkbox("실제 삭제 허용", value=False)

        if st.button("INBOX 정리 실행"):
            if not dry_run and not confirm_delete:
                st.error("실제 삭제하려면 '실제 삭제 허용'을 체크해야 합니다.")
                return
            try:
                args = SimpleNamespace(
                    archive_root=str(root),
                    target=target,
                    dry_run=dry_run,
                    confirm=False,
                    yes=True,
                )
                _, output = _capture_command(command_clear_inbox, args)
                st.success("INBOX 정리 명령을 실행했습니다.")
                if output:
                    st.code(output)
            except Exception as exc:  # noqa: BLE001
                st.error(f"INBOX 정리 실패: {exc}")


def render_archive_tab() -> None:
    st.subheader("Facebook 사진 아카이브")
    st.caption("사진 수집/정리 기능을 대시보드 안에 넣은 공간입니다. 실제 원본 사진 폴더는 GitHub에 올리지 않는 로컬 자료실로 둡니다.")

    root = _get_archive_root()
    _render_setup(root)

    tab_new, tab_list, tab_curate, tab_maint = st.tabs([
        "➕ 새 포스트 저장",
        "📚 목록/인덱스",
        "🎬 릴스 후보 큐레이션",
        "🧹 중복/INBOX 정리",
    ])

    with tab_new:
        _render_new_post(root)

    with tab_list:
        _render_post_list(root)

    with tab_curate:
        _render_curate(root)

    with tab_maint:
        _render_maintenance(root)
