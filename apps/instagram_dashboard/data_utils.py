from pathlib import Path
import json

import pandas as pd


DATA_DIR = Path("data")
INSIGHTS_PATH = DATA_DIR / "content_insights_clean.csv"
POSTS_PATH = DATA_DIR / "activity_posts_inventory.csv"
ZIP_PATH = DATA_DIR / "zip_inventory.csv"
SUMMARY_PATH = DATA_DIR / "stage1_summary.json"
EXTERNAL_TAGS_PATH = DATA_DIR / "external_trending_tags.csv"


def load_insights():
    if not INSIGHTS_PATH.exists():
        raise FileNotFoundError("data/content_insights_clean.csv 파일을 찾을 수 없습니다.")

    df = pd.read_csv(INSIGHTS_PATH)

    if "datetime_kst" in df.columns:
        df["datetime_kst"] = pd.to_datetime(df["datetime_kst"], errors="coerce")

    number_cols = [
        "likes", "comments", "shares", "saves",
        "interactions", "reach", "impressions",
        "profile_visits", "follows", "views",
        "engagement_per_reach", "save_rate_per_reach",
        "share_rate_per_reach", "caption_word_count", "hashtag_count"
    ]

    for col in number_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_summary():
    if not SUMMARY_PATH.exists():
        return {}

    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_int(value):
    if pd.isna(value):
        return "0"
    return f"{int(value):,}"


def short_text(text, limit=80):
    if pd.isna(text):
        return ""
    text = str(text).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def safe_rate(numerator, denominator):
    if pd.isna(denominator) or denominator == 0:
        return 0
    return numerator / denominator


def load_external_trending_tags():
    default_tags = pd.DataFrame([
        {"해시태그": "#boyschoir", "외부_인기도": 70, "카테고리": "choir", "source_seed": "default"},
        {"해시태그": "#choir", "외부_인기도": 75, "카테고리": "choir", "source_seed": "default"},
        {"해시태그": "#classicalmusic", "외부_인기도": 65, "카테고리": "music", "source_seed": "default"},
        {"해시태그": "#choralmusic", "외부_인기도": 62, "카테고리": "choir", "source_seed": "default"},
        {"해시태그": "#munich", "외부_인기도": 60, "카테고리": "location", "source_seed": "default"},
        {"해시태그": "#münchen", "외부_인기도": 60, "카테고리": "location", "source_seed": "default"},
        {"해시태그": "#germany", "외부_인기도": 55, "카테고리": "location", "source_seed": "default"},
        {"해시태그": "#reels", "외부_인기도": 80, "카테고리": "format", "source_seed": "default"},
        {"해시태그": "#musicreels", "외부_인기도": 68, "카테고리": "format", "source_seed": "default"},
        {"해시태그": "#concert", "외부_인기도": 58, "카테고리": "performance", "source_seed": "default"},
        {"해시태그": "#liveperformance", "외부_인기도": 56, "카테고리": "performance", "source_seed": "default"},
        {"해시태그": "#churchmusic", "외부_인기도": 45, "카테고리": "music", "source_seed": "default"},
        {"해시태그": "#vocalmusic", "외부_인기도": 50, "카테고리": "music", "source_seed": "default"},
        {"해시태그": "#soprano", "외부_인기도": 48, "카테고리": "voice", "source_seed": "default"},
    ])

    if not EXTERNAL_TAGS_PATH.exists():
        return default_tags

    try:
        external = pd.read_csv(EXTERNAL_TAGS_PATH)

        if "hashtag" in external.columns:
            external = external.rename(columns={"hashtag": "해시태그"})
        if "popularity" in external.columns:
            external = external.rename(columns={"popularity": "외부_인기도"})
        if "category" in external.columns:
            external = external.rename(columns={"category": "카테고리"})

        if "해시태그" not in external.columns:
            return default_tags
        if "외부_인기도" not in external.columns:
            external["외부_인기도"] = 50
        if "카테고리" not in external.columns:
            external["카테고리"] = "external"
        if "source_seed" not in external.columns:
            external["source_seed"] = ""

        external["외부_인기도"] = pd.to_numeric(external["외부_인기도"], errors="coerce").fillna(50)
        external["해시태그"] = external["해시태그"].astype(str).apply(
            lambda x: x if x.startswith("#") else "#" + x
        )

        return external[["해시태그", "외부_인기도", "카테고리", "source_seed"]].drop_duplicates("해시태그")
    except Exception:
        return default_tags
