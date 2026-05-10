import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import (
    EXTERNAL_TAGS_PATH,
    fmt_int,
    load_external_trending_tags,
    load_insights,
    short_text,
)
from meta_api import fetch_external_tag_stats_live, get_seed_tags
from tag_recommender import build_hashtag_performance, build_tag_recommendations
from experiment_tracker import render_experiment_tab


st.set_page_config(
    page_title="Munich Boys Choir Admin Dashboard",
    page_icon="🎼",
    layout="wide",
)


metric_name = {
    "interactions": "상호작용",
    "reach": "도달",
    "impressions": "노출",
    "likes": "좋아요",
    "comments": "댓글",
    "shares": "공유",
    "saves": "저장",
    "profile_visits": "프로필 방문",
    "follows": "팔로우",
    "views": "조회수",
    "engagement_per_reach": "도달 대비 참여율",
}

korean_to_col = {v: k for k, v in metric_name.items()}


@st.cache_data
def cached_load_insights():
    return load_insights()


def apply_sidebar_filters(insights):
    st.sidebar.header("관리자 필터")
    filtered = insights.copy()

    if "source_type" in insights.columns:
        source_options = sorted(insights["source_type"].dropna().unique().tolist())
        selected_sources = st.sidebar.multiselect(
            "콘텐츠 유형",
            source_options,
            default=source_options
        )
        if selected_sources:
            filtered = filtered[filtered["source_type"].isin(selected_sources)]

    if "datetime_kst" in insights.columns:
        valid_dates = insights["datetime_kst"].dropna()

        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            selected_date_range = st.sidebar.date_input(
                "기간 선택",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

            if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
                start_date, end_date = selected_date_range
                filtered = filtered[
                    (filtered["datetime_kst"].dt.date >= start_date)
                    & (filtered["datetime_kst"].dt.date <= end_date)
                ]

    search_keyword = st.sidebar.text_input(
        "캡션 검색",
        placeholder="예: Munich, choir, concert"
    )

    if search_keyword and "caption" in filtered.columns:
        filtered = filtered[
            filtered["caption"].fillna("").str.contains(
                search_keyword,
                case=False,
                na=False
            )
        ]

    return filtered


def render_kpis(filtered):
    st.subheader("핵심 지표")

    col1, col2, col3, col4, col5 = st.columns(5)

    total_posts = len(filtered)
    total_reach = filtered["reach"].sum(skipna=True) if "reach" in filtered.columns else 0
    total_impressions = filtered["impressions"].sum(skipna=True) if "impressions" in filtered.columns else 0
    total_interactions = filtered["interactions"].sum(skipna=True) if "interactions" in filtered.columns else 0
    avg_engagement = (
        filtered["engagement_per_reach"].mean(skipna=True)
        if "engagement_per_reach" in filtered.columns else 0
    )

    col1.metric("분석 콘텐츠", fmt_int(total_posts))
    col2.metric("총 도달", fmt_int(total_reach))
    col3.metric("총 노출", fmt_int(total_impressions))
    col4.metric("총 상호작용", fmt_int(total_interactions))
    col5.metric("평균 참여율", f"{avg_engagement:.2%}" if not pd.isna(avg_engagement) else "0.00%")


def render_monthly_tab(filtered):
    st.subheader("월별 성과 진단")
    st.caption("피크가 게시물 수 때문인지, 게시물당 반응이 좋았기 때문인지 분리해서 봅니다.")

    trend_df = filtered.dropna(subset=["datetime_kst"]).copy() if "datetime_kst" in filtered.columns else pd.DataFrame()

    if trend_df.empty:
        st.warning("선택한 조건에 해당하는 날짜 데이터가 없습니다.")
        return

    trend_df["월"] = trend_df["datetime_kst"].dt.to_period("M").astype(str)

    available_cols = [
        col for col in ["reach", "impressions", "interactions", "likes", "comments", "shares", "saves"]
        if col in trend_df.columns
    ]

    monthly = trend_df.groupby("월", as_index=False)[available_cols].sum()
    monthly_count = trend_df.groupby("월", as_index=False).size().rename(columns={"size": "게시물수"})
    monthly = monthly.merge(monthly_count, on="월", how="left")

    for col in available_cols:
        monthly[f"게시물당_{col}"] = monthly[col] / monthly["게시물수"].replace(0, pd.NA)

    selected_metric_kor = st.selectbox(
        "분석할 지표 선택",
        ["상호작용", "도달", "노출", "좋아요", "댓글", "공유", "저장"],
        index=0
    )

    selected_metric = korean_to_col[selected_metric_kor]
    per_post_col = f"게시물당_{selected_metric}"

    if selected_metric not in monthly.columns:
        st.warning(f"{selected_metric_kor} 컬럼이 없습니다.")
        return

    c1, c2, c3 = st.columns(3)
    peak_total = monthly.sort_values(selected_metric, ascending=False).iloc[0]
    peak_per_post = monthly.sort_values(per_post_col, ascending=False).iloc[0]
    peak_posts = monthly.sort_values("게시물수", ascending=False).iloc[0]

    c1.metric("총합 피크 월", peak_total["월"], fmt_int(peak_total[selected_metric]))
    c2.metric("게시물당 피크 월", peak_per_post["월"], f"{peak_per_post[per_post_col]:.1f}")
    c3.metric("게시물 수 최다 월", peak_posts["월"], fmt_int(peak_posts["게시물수"]))

    a, b = st.columns(2)

    with a:
        fig_count = px.bar(
            monthly,
            x="월",
            y="게시물수",
            title="월별 게시물 수",
            labels={"월": "월", "게시물수": "게시물 수"}
        )
        st.plotly_chart(fig_count, use_container_width=True)

    with b:
        fig_total = px.line(
            monthly,
            x="월",
            y=selected_metric,
            markers=True,
            title=f"월별 총 {selected_metric_kor}",
            labels={"월": "월", selected_metric: f"총 {selected_metric_kor}"}
        )
        st.plotly_chart(fig_total, use_container_width=True)

    fig_per_post = px.line(
        monthly,
        x="월",
        y=per_post_col,
        markers=True,
        title=f"월별 게시물당 {selected_metric_kor}",
        labels={"월": "월", per_post_col: f"게시물당 {selected_metric_kor}"}
    )
    st.plotly_chart(fig_per_post, use_container_width=True)

    st.markdown("### 월별 진단표")
    view_cols = ["월", "게시물수", selected_metric, per_post_col]
    view = monthly[view_cols].copy()
    view = view.rename(columns={
        selected_metric: f"총 {selected_metric_kor}",
        per_post_col: f"게시물당 {selected_metric_kor}"
    })
    st.dataframe(view.sort_values("월"), use_container_width=True, height=350)


def render_top_content_tab(filtered):
    st.subheader("상위 콘텐츠 순위")

    rank_metric_kor = st.selectbox(
        "순위 기준 선택",
        ["상호작용", "도달", "노출", "좋아요", "댓글", "공유", "저장", "프로필 방문"],
        index=0
    )

    rank_metric = korean_to_col[rank_metric_kor]
    top_n = st.slider("상위 몇 개까지 볼까요?", 5, 30, 10)

    if rank_metric not in filtered.columns:
        st.warning(f"{rank_metric_kor} 데이터가 없습니다.")
        return

    if filtered.empty:
        st.warning("선택한 필터에 해당하는 콘텐츠가 없습니다.")
        return

    top_posts = filtered.sort_values(rank_metric, ascending=False).head(top_n).copy()

    top_posts["짧은 캡션"] = (
        top_posts["caption"].apply(short_text)
        if "caption" in top_posts.columns else "캡션 없음"
    )

    fig = px.bar(
        top_posts,
        x="짧은 캡션",
        y=rank_metric,
        title=f"{rank_metric_kor} 기준 상위 콘텐츠",
        labels={"짧은 캡션": "콘텐츠", rank_metric: rank_metric_kor},
        hover_data=[
            col for col in [
                "datetime_kst", "source_type", "reach", "impressions",
                "interactions", "likes", "comments", "shares", "saves"
            ] if col in top_posts.columns
        ]
    )

    fig.update_layout(xaxis_title="콘텐츠", yaxis_title=rank_metric_kor, xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

    show_cols = [
        "datetime_kst", "source_type", "reach", "impressions",
        "interactions", "likes", "comments", "shares", "saves",
        "profile_visits", "caption"
    ]
    show_cols = [col for col in show_cols if col in top_posts.columns]

    rename_cols = {
        "datetime_kst": "게시일",
        "source_type": "콘텐츠 유형",
        "reach": "도달",
        "impressions": "노출",
        "interactions": "상호작용",
        "likes": "좋아요",
        "comments": "댓글",
        "shares": "공유",
        "saves": "저장",
        "profile_visits": "프로필 방문",
        "caption": "캡션",
    }

    st.dataframe(top_posts[show_cols].rename(columns=rename_cols), use_container_width=True, height=350)


def render_hashtag_performance_tab(filtered):
    st.subheader("해시태그 성과 비교")
    st.caption("많이 쓴 태그와 적게 썼지만 반응이 좋은 태그를 분리해서 봅니다.")

    hashtag_perf, _ = build_hashtag_performance(filtered)

    if hashtag_perf.empty:
        st.warning("선택한 조건에 해당하는 해시태그 성과 데이터가 없습니다.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        min_posts = st.slider("최소 사용 콘텐츠 수", 1, 20, 1)

    with c2:
        rare_max_posts = st.slider("희소 태그 기준: 최대 사용 수", 1, 10, 2)

    with c3:
        frequent_min_posts = st.slider("빈출 태그 기준: 최소 사용 수", 2, 30, 5)

    tag_base = hashtag_perf[hashtag_perf["사용_콘텐츠_수"] >= min_posts].copy()

    if tag_base.empty:
        st.warning("최소 사용 콘텐츠 수 조건을 낮춰보세요.")
        return

    overall_avg_interaction = tag_base["평균_상호작용"].mean()
    overall_avg_reach = tag_base["평균_도달"].mean()

    tag_base["상호작용_지수"] = (
        tag_base["평균_상호작용"] / overall_avg_interaction
        if overall_avg_interaction else 0
    )
    tag_base["도달_지수"] = (
        tag_base["평균_도달"] / overall_avg_reach
        if overall_avg_reach else 0
    )

    tag_base["추천_구분"] = "관찰 필요"
    tag_base.loc[
        (tag_base["사용_콘텐츠_수"] <= rare_max_posts)
        & (tag_base["상호작용_지수"] >= 1.2),
        "추천_구분"
    ] = "적게 썼지만 반응 좋음"
    tag_base.loc[
        (tag_base["사용_콘텐츠_수"] >= frequent_min_posts)
        & (tag_base["상호작용_지수"] >= 1.0),
        "추천_구분"
    ] = "많이 쓰고 안정적"
    tag_base.loc[
        (tag_base["사용_콘텐츠_수"] >= frequent_min_posts)
        & (tag_base["상호작용_지수"] < 0.8),
        "추천_구분"
    ] = "많이 썼지만 효율 낮음"

    a, b = st.columns(2)

    with a:
        st.markdown("### 적게 썼지만 반응 좋은 태그")
        rare_winners = (
            tag_base[tag_base["사용_콘텐츠_수"] <= rare_max_posts]
            .sort_values(["상호작용_지수", "평균_상호작용"], ascending=False)
            .head(15)
        )

        fig_rare = px.bar(
            rare_winners,
            x="해시태그",
            y="상호작용_지수",
            title="희소 태그 반응 지수 TOP 15",
            labels={"해시태그": "해시태그", "상호작용_지수": "상호작용 지수"},
            hover_data=["사용_콘텐츠_수", "평균_상호작용", "평균_도달", "평균_저장", "평균_공유"]
        )
        fig_rare.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_rare, use_container_width=True)

    with b:
        st.markdown("### 많이 쓴 태그의 안정성")
        frequent_tags = (
            tag_base[tag_base["사용_콘텐츠_수"] >= frequent_min_posts]
            .sort_values(["상호작용_지수", "평균_상호작용"], ascending=False)
            .head(15)
        )

        fig_freq = px.bar(
            frequent_tags,
            x="해시태그",
            y="상호작용_지수",
            title="빈출 태그 반응 지수 TOP 15",
            labels={"해시태그": "해시태그", "상호작용_지수": "상호작용 지수"},
            hover_data=["사용_콘텐츠_수", "평균_상호작용", "평균_도달", "평균_저장", "평균_공유"]
        )
        fig_freq.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_freq, use_container_width=True)

    st.markdown("### 해시태그 성과표")
    show_cols = [
        "해시태그", "추천_구분", "사용_콘텐츠_수",
        "총_상호작용", "평균_상호작용", "중앙값_상호작용", "최고_상호작용",
        "총_도달", "평균_도달", "평균_저장", "평균_공유", "평균_참여율",
        "상호작용_지수", "도달_지수"
    ]
    st.dataframe(
        tag_base[show_cols].sort_values(["추천_구분", "상호작용_지수"], ascending=[True, False]),
        use_container_width=True,
        height=420
    )


def render_tag_recommendation_tab(filtered):
    st.subheader("맞춤형 태그 추천")
    st.caption("내 계정 성과 + Meta API 외부 인기 후보 + 자동 주제연관 필터를 섞어서 추천합니다.")

    external_debug = load_external_trending_tags()
    st.info(f"외부 인기태그 CSV 읽음: {len(external_debug)}개 / 경로: data/external_trending_tags.csv")

    with st.expander("Meta API 외부 수집 태그 확인"):
        st.dataframe(
            external_debug.sort_values("외부_인기도", ascending=False),
            use_container_width=True,
            height=260
        )

    planned_caption = st.text_area(
        "올릴 게시물 캡션/주제 입력",
        placeholder="예: 뮌헨 소년합창단 단원들이 목소리로 와인잔의 공명음을 맞추는 영상",
        height=120
    )

    max_tags = st.slider("추천 태그 개수", 5, 30, 15)

    st.markdown("### 실시간 외부 태그 갱신")
    st.caption("큰 범위 시드 태그를 조회하고, 각 태그의 최근 게시물 중 반응 좋은 게시물에서 연관 태그를 추출합니다.")

    candidate_tags = get_seed_tags()
    st.write("이번에 조회할 시드 태그 15개:", " ".join(["#" + tag for tag in candidate_tags]))
    st.caption("recent_media로 가져온 뒤, 각 시드 태그별로 좋아요+댓글×3 기준 상위 10개 최근 게시물만 연관 태그 추출에 사용합니다.")

    if st.button("Meta API로 오늘 외부 태그 갱신", type="primary"):
        with st.spinner("Meta API에서 외부 최근 게시물 반응을 수집하는 중..."):
            try:
                live_df = fetch_external_tag_stats_live(candidate_tags)
                if live_df.empty:
                    st.warning("외부 태그 데이터를 가져오지 못했습니다. 토큰 권한이나 후보 태그를 확인해보세요.")
                else:
                    st.success(f"외부 태그 {len(live_df)}개 갱신 완료")
                    st.dataframe(
                        live_df.sort_values("popularity", ascending=False),
                        use_container_width=True,
                        height=260
                    )
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"외부 태그 갱신 실패: {e}")

    hashtag_perf, _ = build_hashtag_performance(filtered)
    rec_tags = build_tag_recommendations(hashtag_perf, planned_caption, max_tags=max_tags)

    st.markdown("### 추천 결과")
    st.dataframe(
        rec_tags[[
            "해시태그", "추천점수", "주제적합도", "자동필터", "필터근거",
            "추천이유", "데이터출처", "카테고리", "외부_인기도",
            "사용_콘텐츠_수", "평균_상호작용", "평균_도달", "평균_저장", "캡션_관련성"
        ]],
        use_container_width=True,
        height=420
    )

    c_external, c_own = st.columns(2)

    with c_external:
        st.markdown("### 외부 API 기반 추천")
        st.dataframe(
            rec_tags[rec_tags["데이터출처"].isin(["외부 API 수집 태그", "외부+내 계정 공통 태그"])][[
                "해시태그", "추천점수", "주제적합도", "자동필터", "외부_인기도", "추천이유"
            ]],
            use_container_width=True,
            height=260
        )

    with c_own:
        st.markdown("### 내 계정 성과 기반 추천")
        st.dataframe(
            rec_tags[rec_tags["사용_콘텐츠_수"] > 0][[
                "해시태그", "추천점수", "주제적합도", "자동필터", "사용_콘텐츠_수", "평균_상호작용", "추천이유"
            ]],
            use_container_width=True,
            height=260
        )

    tag_text = " ".join(rec_tags["해시태그"].head(max_tags).tolist())
    st.text_area("복사용 추천 태그", value=tag_text, height=100)

    with st.expander("외부 인기 태그 CSV 연결 상태"):
        st.write("CSV 경로:", str(EXTERNAL_TAGS_PATH))
        st.write("실시간 갱신 버튼을 누르면 이 CSV가 자동 갱신됩니다.")


def render_export_tab(filtered):
    st.subheader("관리자용 CSV 내보내기")

    download_csv = filtered.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="현재 필터 결과 CSV 다운로드",
        data=download_csv,
        file_name="filtered_munich_dashboard_data.csv",
        mime="text/csv"
    )

    st.divider()

    st.subheader("필터 적용된 데이터 미리보기")
    st.caption("화면이 너무 길어지지 않게 10개만 보여줍니다.")

    preview = filtered.head(10).copy()

    preview = preview.rename(columns={
        "datetime_kst": "게시일",
        "source_type": "콘텐츠 유형",
        "reach": "도달",
        "impressions": "노출",
        "interactions": "상호작용",
        "likes": "좋아요",
        "comments": "댓글",
        "shares": "공유",
        "saves": "저장",
        "profile_visits": "프로필 방문",
        "caption": "캡션",
    })

    st.dataframe(preview, use_container_width=True, height=300)


def main():
    st.title("🎼 Munich Boys Choir Admin Dashboard")
    st.caption("Instagram export data 관리자 대시보드")

    try:
        insights = cached_load_insights()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    filtered = apply_sidebar_filters(insights)
    render_kpis(filtered)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 월별 추세",
    "🏆 상위 콘텐츠",
    "🏷 해시태그 성과",
    "🧠 태그 추천",
    "🧪 게시 실험 기록",
    "📄 데이터/내보내기"
    ])

    with tab1:
        render_monthly_tab(filtered)

    with tab2:
        render_top_content_tab(filtered)

    with tab3:
        render_hashtag_performance_tab(filtered)

    with tab4:
        render_tag_recommendation_tab(filtered)

    with tab5:
        render_experiment_tab()

    with tab6:
        render_export_tab(filtered)


if __name__ == "__main__":
    main()
