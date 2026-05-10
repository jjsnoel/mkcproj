import re

import pandas as pd

from data_utils import load_external_trending_tags, safe_rate


def normalize_hashtags(text):
    if pd.isna(text):
        return []
    tags = re.findall(r"#[^\s#,\]\['\"]+", str(text))
    return sorted(set(tags))


def build_hashtag_post_rows(df):
    rows = []

    if "hashtags" not in df.columns:
        return pd.DataFrame()

    for _, row in df.iterrows():
        tags = normalize_hashtags(row.get("hashtags", ""))

        for tag in tags:
            rows.append({
                "해시태그": tag,
                "게시일": row.get("datetime_kst"),
                "콘텐츠 유형": row.get("source_type"),
                "캡션": row.get("caption", ""),
                "상호작용": row.get("interactions", 0),
                "도달": row.get("reach", 0),
                "노출": row.get("impressions", 0),
                "좋아요": row.get("likes", 0),
                "댓글": row.get("comments", 0),
                "공유": row.get("shares", 0),
                "저장": row.get("saves", 0),
                "참여율": row.get("engagement_per_reach", 0),
            })

    return pd.DataFrame(rows)


def build_hashtag_performance(df):
    tag_rows = build_hashtag_post_rows(df)

    if tag_rows.empty:
        return pd.DataFrame(), tag_rows

    result = (
        tag_rows
        .groupby("해시태그", as_index=False)
        .agg(
            사용_콘텐츠_수=("해시태그", "count"),
            총_상호작용=("상호작용", "sum"),
            평균_상호작용=("상호작용", "mean"),
            중앙값_상호작용=("상호작용", "median"),
            최고_상호작용=("상호작용", "max"),
            총_도달=("도달", "sum"),
            평균_도달=("도달", "mean"),
            중앙값_도달=("도달", "median"),
            최고_도달=("도달", "max"),
            총_노출=("노출", "sum"),
            평균_저장=("저장", "mean"),
            평균_공유=("공유", "mean"),
            평균_댓글=("댓글", "mean"),
            평균_참여율=("참여율", "mean"),
        )
    )

    result["효율_점수"] = result.apply(
        lambda r: safe_rate(r["총_상호작용"], r["사용_콘텐츠_수"]),
        axis=1
    )
    result["도달_효율"] = result.apply(
        lambda r: safe_rate(r["총_도달"], r["사용_콘텐츠_수"]),
        axis=1
    )

    return result, tag_rows


def caption_keyword_score(caption, tag):
    caption = str(caption).lower()
    clean_tag = tag.replace("#", "").lower()

    keyword_map = {
        "munich": ["munich", "münchen", "muenchen", "뮌헨"],
        "münchen": ["munich", "münchen", "muenchen", "뮌헨"],
        "boyschoir": ["boy", "boys", "choir", "chor", "소년", "합창단"],
        "boychoir": ["boy", "boys", "choir", "chor", "소년", "합창단"],
        "choir": ["choir", "chor", "합창", "합창단"],
        "chor": ["choir", "chor", "합창", "합창단"],
        "knabenchor": ["knabenchor", "chor", "boys", "소년", "합창단"],
        "kinderchor": ["kinderchor", "children", "어린이", "합창단"],
        "classicalmusic": ["classical", "classic", "클래식", "bach", "mozart", "schubert"],
        "choralmusic": ["choral", "choir", "합창"],
        "concert": ["concert", "performance", "공연", "연주", "무대"],
        "liveperformance": ["live", "performance", "공연", "무대"],
        "churchmusic": ["church", "sacred", "성당", "교회", "미사", "가톨릭"],
        "soprano": ["soprano", "treble", "voice", "고음", "소프라노"],
        "musicreels": ["reels", "릴스", "shorts", "music", "음악"],
        "reels": ["reels", "릴스", "shorts", "short"],
    }

    candidates = keyword_map.get(clean_tag, [clean_tag])
    return 1 if any(word in caption for word in candidates) else 0


def topic_relevance_score(tag, category="", source_seed="", planned_caption=""):
    text = f"{tag} {category} {source_seed}".replace("#", "").lower()
    caption = str(planned_caption).lower()

    strong_roots = [
        "choir", "chor", "choral", "knaben", "kinderchor", "boyschoir", "boychoir",
        "soprano", "vocal", "voice", "singing", "singer", "treble",
        "classical", "music", "concert", "performance", "church", "sacred", "hymn",
        "munich", "münchen", "muenchen", "germany", "bavaria",
        "합창", "합창단", "소년", "성가", "성가대", "어린이합창단",
        "교회", "성당", "클래식", "음악", "공연", "연주", "미사"
    ]

    weak_roots = ["reels", "musicreels", "instareels", "artist", "culture", "europe"]

    spam_roots = [
        "follow", "likeforlike", "like4like", "fyp", "viral", "instagood", "photooftheday",
        "love", "beautiful", "happy", "cute", "selfie", "fashion", "makeup", "fitness", "gym",
        "food", "breakfast", "lunch", "dinner", "travel", "ucla", "losangeles", "newyork",
        "sale", "shop", "crypto", "giveaway"
    ]

    score = 0
    reasons = []

    if any(root in text for root in strong_roots):
        score += 4
        reasons.append("합창/음악/지역 관련")

    if any(root in text for root in weak_roots):
        score += 1
        reasons.append("문화/형식 약한 관련")

    if caption_keyword_score(caption, tag):
        score += 2
        reasons.append("입력 주제와 관련")

    if any(root in text for root in spam_roots):
        score -= 3
        reasons.append("너무 일반적이거나 주제 이탈 가능")

    clean = tag.replace("#", "").strip()
    if len(clean) <= 2:
        score -= 2
        reasons.append("너무 짧음")

    if category in ["meta_live_seed", "choir", "music", "performance", "voice", "location"]:
        score += 1
        reasons.append("신뢰 가능한 시드/분류")

    if score >= 3:
        label = "추천 가능"
    elif score >= 1:
        label = "보류"
    else:
        label = "자동 제외"

    return score, label, " / ".join(reasons) if reasons else "근거 약함"


def build_tag_recommendations(hashtag_perf, planned_caption, max_tags=20):
    external = load_external_trending_tags()

    if hashtag_perf.empty:
        own = pd.DataFrame(columns=[
            "해시태그", "사용_콘텐츠_수", "평균_상호작용", "평균_도달", "평균_저장", "상호작용_지수"
        ])
    else:
        own = hashtag_perf.copy()
        avg_interaction = own["평균_상호작용"].mean()
        own["상호작용_지수"] = own["평균_상호작용"] / avg_interaction if avg_interaction else 0

    rec = external.merge(own, on="해시태그", how="outer", indicator=True)

    rec["데이터출처"] = rec["_merge"].map({
        "left_only": "외부 API 수집 태그",
        "right_only": "내 계정 사용 태그",
        "both": "외부+내 계정 공통 태그",
    })
    rec = rec.drop(columns=["_merge"])

    rec["외부_인기도"] = rec["외부_인기도"].fillna(0)
    rec["카테고리"] = rec["카테고리"].fillna("내 계정 사용 태그")
    if "source_seed" not in rec.columns:
        rec["source_seed"] = ""
    rec["source_seed"] = rec["source_seed"].fillna("")

    rec["사용_콘텐츠_수"] = rec["사용_콘텐츠_수"].fillna(0)
    rec["평균_상호작용"] = rec["평균_상호작용"].fillna(0)
    rec["평균_도달"] = rec["평균_도달"].fillna(0)
    rec["평균_저장"] = rec["평균_저장"].fillna(0)
    rec["상호작용_지수"] = rec["상호작용_지수"].fillna(0)

    max_external = rec["외부_인기도"].max() or 1
    max_avg_interaction = rec["평균_상호작용"].max() or 1
    max_avg_reach = rec["평균_도달"].max() or 1

    rec["외부_점수"] = rec["외부_인기도"] / max_external
    rec["내계정_상호작용_점수"] = rec["평균_상호작용"] / max_avg_interaction
    rec["내계정_도달_점수"] = rec["평균_도달"] / max_avg_reach
    rec["캡션_관련성"] = rec["해시태그"].apply(lambda tag: caption_keyword_score(planned_caption, tag))

    rec["추천점수"] = (
        rec["외부_점수"] * 0.45
        + rec["내계정_상호작용_점수"] * 0.25
        + rec["내계정_도달_점수"] * 0.15
        + rec["캡션_관련성"] * 0.15
    )

    rec.loc[
        rec["데이터출처"].isin(["외부 API 수집 태그", "외부+내 계정 공통 태그"]),
        "추천점수"
    ] += 0.05

    rec["추천이유"] = ""
    rec.loc[rec["캡션_관련성"] > 0, "추천이유"] += "캡션 관련성 있음 / "
    rec.loc[rec["사용_콘텐츠_수"] > 0, "추천이유"] += "내 계정 사용 이력 있음 / "
    rec.loc[rec["외부_인기도"] > 0, "추천이유"] += "Meta API 외부 최근 반응 반영 / "
    rec.loc[rec["상호작용_지수"] >= 1.2, "추천이유"] += "내 계정 평균 대비 반응 좋음 / "
    rec["추천이유"] = rec["추천이유"].str.rstrip(" / ").replace("", "보조 후보")

    relevance = rec.apply(
        lambda r: topic_relevance_score(
            r["해시태그"],
            r.get("카테고리", ""),
            r.get("source_seed", ""),
            planned_caption,
        ),
        axis=1,
        result_type="expand"
    )
    rec[["주제적합도", "자동필터", "필터근거"]] = relevance

    filtered_rec = rec[rec["자동필터"] != "자동 제외"].copy()
    if filtered_rec.empty:
        filtered_rec = rec.copy()

    return filtered_rec.sort_values(
        ["추천점수", "주제적합도"],
        ascending=False
    ).head(max_tags)
