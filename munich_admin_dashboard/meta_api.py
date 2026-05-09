import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from data_utils import EXTERNAL_TAGS_PATH


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v25.0")
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def get_seed_tags():
    return [
        "choir",
        "boyschoir",
        "boychoir",
        "chor",
        "knabenchor",
        "kinderchor",
        "choralmusic",
        "classicalmusic",
        "소년합창단",
        "합창단",
        "성가대",
        "어린이합창단",
        "munich",
        "münchen",
        "germany",
    ]


def extract_hashtags_from_external_caption(caption):
    if pd.isna(caption):
        return []

    tags = []
    caption_text = " ".join(str(caption).splitlines())

    for token in caption_text.split():
        if token.startswith("#"):
            tag = token.strip().lower()
            tag = tag.strip(".,!?;:()[]{}'\"")
            if tag and tag not in tags:
                tags.append(tag)

    return tags


def search_hashtag_id(tag):
    if not META_ACCESS_TOKEN or not IG_USER_ID:
        raise RuntimeError(".env에 META_ACCESS_TOKEN 또는 IG_USER_ID가 없습니다.")

    url = f"{GRAPH_BASE_URL}/ig_hashtag_search"
    params = {
        "user_id": IG_USER_ID,
        "q": tag,
        "access_token": META_ACCESS_TOKEN,
    }

    res = requests.get(url, params=params, timeout=20)
    data = res.json()

    if "error" in data or not data.get("data"):
        return None

    return data["data"][0]["id"]


def fetch_recent_media(hashtag_id, limit=25):
    url = f"{GRAPH_BASE_URL}/{hashtag_id}/recent_media"
    params = {
        "user_id": IG_USER_ID,
        "fields": "id,caption,media_type,permalink,timestamp,like_count,comments_count",
        "access_token": META_ACCESS_TOKEN,
        "limit": limit,
    }

    res = requests.get(url, params=params, timeout=20)
    data = res.json()

    if "error" in data:
        return []

    return data.get("data", [])


def fetch_external_tag_stats_live(candidate_tags=None):
    if candidate_tags is None:
        candidate_tags = get_seed_tags()

    if not META_ACCESS_TOKEN or not IG_USER_ID:
        raise RuntimeError(".env에 META_ACCESS_TOKEN 또는 IG_USER_ID가 없습니다.")

    seed_rows = []
    related_rows = []

    for tag in candidate_tags:
        hashtag_id = search_hashtag_id(tag)
        if not hashtag_id:
            continue

        items = fetch_recent_media(hashtag_id, limit=25)
        post_count = len(items)

        # recent_media는 최신순입니다.
        # 그래서 좋아요 + 댓글×3 점수로 정렬해서 최근 게시물 중 반응 좋은 상위 10개만 씁니다.
        for item in items:
            item["reaction_score"] = (item.get("like_count", 0) or 0) + (
                (item.get("comments_count", 0) or 0) * 3
            )

        popular_recent_items = sorted(
            items,
            key=lambda x: x.get("reaction_score", 0),
            reverse=True
        )[:10]

        sample_count = len(popular_recent_items)
        likes = [item.get("like_count", 0) or 0 for item in popular_recent_items]
        comments = [item.get("comments_count", 0) or 0 for item in popular_recent_items]

        avg_likes = sum(likes) / sample_count if sample_count else 0
        avg_comments = sum(comments) / sample_count if sample_count else 0
        popularity = avg_likes + (avg_comments * 3)

        seed_rows.append({
            "hashtag": tag,
            "popularity": round(popularity, 2),
            "category": "meta_live_seed",
            "recent_post_count": post_count,
            "popular_sample_count": sample_count,
            "avg_likes": round(avg_likes, 2),
            "avg_comments": round(avg_comments, 2),
            "source_seed": tag,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # 연관 태그는 추가 API 검색이 아니라, 반응 좋은 최근 게시물 caption에서 추출합니다.
        for item in popular_recent_items:
            caption = item.get("caption", "")
            co_tags = extract_hashtags_from_external_caption(caption)

            for co_tag in co_tags:
                clean_seed = "#" + tag.lower().replace("#", "")
                if co_tag == clean_seed:
                    continue

                related_rows.append({
                    "hashtag": co_tag.replace("#", ""),
                    "source_seed": tag,
                    "like_count": item.get("like_count", 0) or 0,
                    "comments_count": item.get("comments_count", 0) or 0,
                })

    rows = list(seed_rows)

    related_df = pd.DataFrame(related_rows)
    if not related_df.empty:
        grouped_related = (
            related_df
            .groupby("hashtag", as_index=False)
            .agg(
                recent_post_count=("hashtag", "count"),
                avg_likes=("like_count", "mean"),
                avg_comments=("comments_count", "mean"),
                source_seed=("source_seed", lambda x: ",".join(sorted(set(x))[:5])),
            )
        )

        grouped_related["popular_sample_count"] = grouped_related["recent_post_count"]
        grouped_related["popularity"] = (
            grouped_related["avg_likes"]
            + (grouped_related["avg_comments"] * 3)
            + (grouped_related["recent_post_count"] * 2)
        )
        grouped_related["category"] = "meta_live_related"
        grouped_related["collected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for _, r in grouped_related.iterrows():
            rows.append({
                "hashtag": r["hashtag"],
                "popularity": round(r["popularity"], 2),
                "category": r["category"],
                "recent_post_count": int(r["recent_post_count"]),
                "popular_sample_count": int(r["popular_sample_count"]),
                "avg_likes": round(r["avg_likes"], 2),
                "avg_comments": round(r["avg_comments"], 2),
                "source_seed": r["source_seed"],
                "collected_at": r["collected_at"],
            })

    live_df = pd.DataFrame(rows)

    if not live_df.empty:
        live_df = live_df.sort_values("popularity", ascending=False)
        live_df.to_csv(EXTERNAL_TAGS_PATH, index=False, encoding="utf-8-sig")

    return live_df
