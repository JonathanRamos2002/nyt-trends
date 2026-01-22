import pandas as pd
import streamlit as st
import plotly.express as px

from nyt import (
    fetch_top_stories,
    normalize_top_stories,
    fetch_most_popular_viewed,
    fetch_most_popular_shared,
    normalize_most_popular,
)
from text_analysis import build_corpus, top_terms_tfidf

st.set_page_config(page_title="NYT Trends Dashboard", layout="wide")

st.title("NYT Live Trends (Top Stories + Most Popular)")

with st.sidebar:
    st.header("Controls")
    section = st.selectbox(
        "Top Stories section",
        ["home", "world", "business", "technology", "science", "health", "sports", "arts", "politics"],
        index=0,
    )
    period = st.selectbox("Most Popular period (days)", [1, 7, 30], index=0)
    top_n = st.slider("Top terms / phrases", 10, 60, 25)
    refresh = st.button("Refresh now")

# Basic caching so you don’t hammer the API while developing
@st.cache_data(ttl=60)  # cache for 60 seconds
def load_data(section: str, period: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    top = fetch_top_stories(section)
    top_rows = pd.DataFrame(normalize_top_stories(top))

    viewed = fetch_most_popular_viewed(period)
    shared = fetch_most_popular_shared(period)

    mp_rows = pd.DataFrame(
        normalize_most_popular(viewed, "viewed") + normalize_most_popular(shared, "shared")
    )

    return top_rows, mp_rows


top_df, mp_df = load_data(section, period)

left, right = st.columns(2)

with left:
    st.subheader(f"Top Stories ({section})")
    st.dataframe(top_df[["published_date", "title", "byline", "url"]], use_container_width=True)

with right:
    st.subheader(f"Most Popular (last {period} day(s))")
    show_cols = [c for c in ["published_date", "title", "section", "views", "total_shares", "url"] if c in mp_df.columns]
    st.dataframe(mp_df[show_cols], use_container_width=True)

st.divider()

# Keyword + key phrase extraction from Top Stories text
st.subheader("Keywords & Key Phrases (from Top Stories)")
corpus = build_corpus(top_df)
terms = top_terms_tfidf(corpus, top_n=top_n, ngram_range=(1, 2))

fig = px.bar(terms, x="score", y="term", orientation="h")
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

st.caption("Tip: 2-word phrases are often more meaningful than single words.")

st.write(f"Streamlit version: {st.__version__}")
