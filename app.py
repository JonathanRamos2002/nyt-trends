from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px

from nyt import get_api_key
from src.nyt_client import NYTClient
from src.engagement import build_engagement_table


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="NYT Trends Dashboard", layout="wide")
st.title("NYT Live Trends (Top Stories + Engagement)")
st.caption(
    "Engagement uses NYT 'Most Popular' lists (viewed/shared/emailed). "
    "Time is a reading-time proxy. Keywords are extracted from each article's title + abstract."
)

# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("Controls")

    section = st.selectbox(
        "Top Stories section",
        ["home", "world", "business", "technology", "science", "health", "sports", "arts", "politics"],
        index=0,
    )
    period = st.selectbox("Most Popular period (days)", [1, 7, 30], index=1)
    share_type = st.selectbox("Shares source", ["facebook", "email"], index=0)

    st.subheader("Engagement weights")
    w_views = st.slider("Views", 0.0, 1.0, 0.40, 0.05)
    w_shares = st.slider("Shares", 0.0, 1.0, 0.30, 0.05)
    w_emails = st.slider("Emails", 0.0, 1.0, 0.20, 0.05)
    w_time = st.slider("Time (proxy)", 0.0, 1.0, 0.10, 0.05)

    st.subheader("Keywords")
    per_article_k = st.slider("Keywords/phrases per article", 3, 15, 6)
    ngram_min = st.selectbox("N-gram min", [1, 2], index=0)
    ngram_max = st.selectbox("N-gram max", [2, 3], index=0)

    refresh = st.button("Refresh now")

# Normalize weights
wsum = w_views + w_shares + w_emails + w_time
weights = (0.40, 0.30, 0.20, 0.10) if wsum == 0 else (w_views / wsum, w_shares / wsum, w_emails / wsum, w_time / wsum)
st.sidebar.caption(f"Normalized → views={weights[0]:.2f}, shares={weights[1]:.2f}, emails={weights[2]:.2f}, time={weights[3]:.2f}")


# -----------------------------
# Client + caching
# -----------------------------
@st.cache_resource
def get_client() -> NYTClient:
    return NYTClient(api_key=get_api_key())

TTL = 300

@st.cache_data(ttl=TTL)
def fetch_top_stories(section_name: str) -> list[dict]:
    return get_client().top_stories(section=section_name)

@st.cache_data(ttl=TTL)
def fetch_most_popular(period_days: int, share_source: str) -> tuple[list[dict], list[dict], list[dict]]:
    c = get_client()
    return (
        c.most_viewed(period=period_days),
        c.most_shared(period=period_days, share_type=share_source),
        c.most_emailed(period=period_days),
    )

if refresh:
    st.cache_data.clear()


# -----------------------------
# Keyword extraction per article (minimal, local)
# -----------------------------
def per_article_keywords(df: pd.DataFrame, k: int, ngram_range=(1, 2)) -> pd.Series:
    """
    Returns a Series of comma-separated keywords/phrases for each row based on that row's text.
    Uses TF-IDF fitted on the full set, then takes top-k terms for each document.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np

    texts = (
        df["title"].fillna("").astype(str) + " " + df["abstract"].fillna("").astype(str)
    ).tolist()

    # If everything is empty, just return blanks
    if not any(t.strip() for t in texts):
        return pd.Series([""] * len(df), index=df.index)

    vec = TfidfVectorizer(stop_words="english", ngram_range=ngram_range, max_features=8000)
    X = vec.fit_transform(texts)  # shape = (n_docs, n_terms)
    terms = vec.get_feature_names_out()

    keywords = []
    for i in range(X.shape[0]):
        row = X.getrow(i)
        if row.nnz == 0:
            keywords.append("")
            continue
        # Get top-k indices by tfidf score for this document
        scores = row.data
        idxs = row.indices
        top = np.argsort(scores)[-k:][::-1]
        kws = [terms[idxs[j]] for j in top]
        keywords.append(", ".join(kws))

    return pd.Series(keywords, index=df.index)


# -----------------------------
# Fetch data
# -----------------------------
top_raw = fetch_top_stories(section)
viewed, shared, emailed = fetch_most_popular(period, share_type)

# -----------------------------
# Build engagement table from Most Popular
# -----------------------------
engagement_df = build_engagement_table(viewed=viewed, emailed=emailed, shared=shared, weights=weights)

# Ensure title/abstract exist (Most Popular items usually have both, but be safe)
if "abstract" not in engagement_df.columns:
    engagement_df["abstract"] = ""

# Add per-article keywords to engagement table
engagement_df["keywords"] = per_article_keywords(
    engagement_df.rename(columns={"title": "title", "abstract": "abstract"}),
    k=per_article_k,
    ngram_range=(ngram_min, ngram_max),
)

# -----------------------------
# Build Top Stories DF and score via URL join
# -----------------------------
top_df = pd.DataFrame(
    {
        "published_date": [a.get("published_date", "") for a in top_raw],
        "title": [a.get("title", "") for a in top_raw],
        "abstract": [a.get("abstract", "") for a in top_raw],
        "byline": [a.get("byline", "") for a in top_raw],
        "section": [a.get("section", "") for a in top_raw],
        "url": [a.get("url", "") for a in top_raw],
    }
)

# Add per-article keywords to top stories table
top_df["keywords"] = per_article_keywords(top_df, k=per_article_k, ngram_range=(ngram_min, ngram_max))

# Join engagement scores onto top stories
join_cols = ["url", "engagement_score", "views_score", "shares_score", "emails_score", "time_score"]
join_cols = [c for c in join_cols if c in engagement_df.columns]
scores = engagement_df[join_cols].copy()

top_scored_df = top_df.merge(scores, on="url", how="left")

for c in ["engagement_score", "views_score", "shares_score", "emails_score", "time_score"]:
    if c in top_scored_df.columns:
        top_scored_df[c] = top_scored_df[c].fillna(0.0)

top_scored_df = top_scored_df.sort_values("engagement_score", ascending=False).reset_index(drop=True)


# -----------------------------
# Display tables
# -----------------------------
left, right = st.columns(2)

with left:
    st.subheader(f"Most Popular — Ranked by engagement_score (period={period}, shares={share_type})")
    display_cols = [
        "engagement_score", "views_score", "shares_score", "emails_score", "time_score",
        "title", "abstract", "keywords", "section", "published_date", "url"
    ]
    display_cols = [c for c in display_cols if c in engagement_df.columns]
    st.dataframe(engagement_df[display_cols].head(30), use_container_width=True)

with right:
    st.subheader(f"Top Stories ({section}) — Ranked by engagement_score (URL match)")
    display_cols = [
        "engagement_score", "views_score", "shares_score", "emails_score", "time_score",
        "title", "abstract", "keywords", "published_date", "byline", "url"
    ]
    display_cols = [c for c in display_cols if c in top_scored_df.columns]
    st.dataframe(top_scored_df[display_cols].head(30), use_container_width=True)

st.divider()


# -----------------------------
# Global keyword/key-phrase chart (across Top Stories)
# -----------------------------
st.subheader("Top Keywords & Key Phrases (Top Stories corpus)")

# Build corpus for chart
texts = (top_df["title"].fillna("").astype(str) + " " + top_df["abstract"].fillna("").astype(str)).tolist()

# Compute global TF-IDF terms (sum across docs)
from sklearn.feature_extraction.text import TfidfVectorizer
vec = TfidfVectorizer(stop_words="english", ngram_range=(ngram_min, ngram_max), max_features=8000)
X = vec.fit_transform(texts)
scores = X.sum(axis=0).A1
terms = vec.get_feature_names_out()

terms_df = (
    pd.DataFrame({"term": terms, "score": scores})
    .sort_values("score", ascending=False)
    .head(25)
    .reset_index(drop=True)
)

fig = px.bar(terms_df, x="score", y="term", orientation="h")
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

