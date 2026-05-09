from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
EXPERIMENTS_PATH = BASE_DIR / "data" / "posting_experiments.csv"

COLUMNS = [
    "experiment_id",
    "post_date",
    "topic",
    "post_url",
    "recommended_tags",
    "used_tags",
    "likes_3d",
    "comments_3d",
    "reach_3d",
    "saves_3d",
    "shares_3d",
    "notes",
    "created_at",
]


def ensure_experiment_file():
    EXPERIMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not EXPERIMENTS_PATH.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(
            EXPERIMENTS_PATH,
            index=False,
            encoding="utf-8-sig"
        )


def load_experiments():
    ensure_experiment_file()
    df = pd.read_csv(EXPERIMENTS_PATH)

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[COLUMNS]


def save_experiments(df):
    df.to_csv(EXPERIMENTS_PATH, index=False, encoding="utf-8-sig")


def append_experiment(row):
    df = load_experiments()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_experiments(df)


def make_experiment_id():
    return datetime.now().strftime("EXP_%Y%m%d_%H%M%S")


def render_experiment_tab():
    st.subheader("게시 실험 기록")
    st.caption("추천 태그를 실제 게시물에 썼을 때 성과가 좋았는지 기록하는 공간입니다.")

    with st.form("new_experiment_form"):
        st.markdown("### 새 게시 실험 추가")

        post_date = st.date_input("게시일")
        topic = st.text_area(
            "게시물 주제",
            placeholder="예: 뮌헨 소년합창단 단원들이 목소리로 와인잔 공명음을 맞추는 영상",
            height=80,
        )
        post_url = st.text_input(
            "게시물 링크",
            placeholder="https://www.instagram.com/reel/..."
        )
        recommended_tags = st.text_area(
            "추천받은 태그",
            placeholder="#boyschoir #choir #choralmusic ...",
            height=80,
        )
        used_tags = st.text_area(
            "실제로 사용한 태그",
            placeholder="#boyschoir #choir #munich ...",
            height=80,
        )
        notes = st.text_area(
            "메모",
            placeholder="썸네일, 업로드 시간, 캡션 분위기, 실험 의도 등을 적어두세요.",
            height=80,
        )

        submitted = st.form_submit_button("실험 기록 추가")

        if submitted:
            row = {
                "experiment_id": make_experiment_id(),
                "post_date": str(post_date),
                "topic": topic,
                "post_url": post_url,
                "recommended_tags": recommended_tags,
                "used_tags": used_tags,
                "likes_3d": "",
                "comments_3d": "",
                "reach_3d": "",
                "saves_3d": "",
                "shares_3d": "",
                "notes": notes,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            append_experiment(row)
            st.success("게시 실험 기록을 추가했습니다.")
            st.rerun()

    st.divider()

    df = load_experiments()

    st.markdown("### 실험 기록표")
    st.caption("3일 뒤 성과가 나오면 likes_3d, comments_3d, reach_3d, saves_3d, shares_3d를 직접 입력하고 저장하세요.")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        height=420,
        num_rows="dynamic",
        column_config={
            "experiment_id": st.column_config.TextColumn("실험 ID", disabled=True),
            "post_date": "게시일",
            "topic": "주제",
            "post_url": st.column_config.LinkColumn("게시물 링크"),
            "recommended_tags": "추천 태그",
            "used_tags": "사용 태그",
            "likes_3d": "3일 뒤 좋아요",
            "comments_3d": "3일 뒤 댓글",
            "reach_3d": "3일 뒤 도달",
            "saves_3d": "3일 뒤 저장",
            "shares_3d": "3일 뒤 공유",
            "notes": "메모",
            "created_at": st.column_config.TextColumn("기록 생성일", disabled=True),
        },
    )

    if st.button("수정 내용 저장"):
        save_experiments(edited_df)
        st.success("수정 내용을 저장했습니다.")
        st.rerun()

    if df.empty:
        return

    st.divider()
    st.markdown("### 실험 성과 요약")

    metric_df = df.copy()

    for col in ["likes_3d", "comments_3d", "reach_3d", "saves_3d", "shares_3d"]:
        metric_df[col] = pd.to_numeric(metric_df[col], errors="coerce").fillna(0)

    total_experiments = len(metric_df)
    filled_reach = (metric_df["reach_3d"] > 0).sum()
    avg_likes = metric_df.loc[metric_df["likes_3d"] > 0, "likes_3d"].mean()
    avg_reach = metric_df.loc[metric_df["reach_3d"] > 0, "reach_3d"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 실험 수", f"{total_experiments:,}")
    c2.metric("성과 입력 완료", f"{filled_reach:,}")
    c3.metric("평균 좋아요", "0" if pd.isna(avg_likes) else f"{avg_likes:.1f}")
    c4.metric("평균 도달", "0" if pd.isna(avg_reach) else f"{avg_reach:.1f}")

    scored = metric_df.copy()
    scored["성과점수"] = (
        scored["likes_3d"]
        + scored["comments_3d"] * 3
        + scored["saves_3d"] * 4
        + scored["shares_3d"] * 5
    )

    best = scored.sort_values("성과점수", ascending=False).head(5)

    st.markdown("### 성과 좋은 실험 TOP 5")
    st.dataframe(
        best[
            [
                "post_date",
                "topic",
                "used_tags",
                "likes_3d",
                "comments_3d",
                "reach_3d",
                "saves_3d",
                "shares_3d",
                "성과점수",
                "notes",
            ]
        ],
        use_container_width=True,
        height=260,
    )