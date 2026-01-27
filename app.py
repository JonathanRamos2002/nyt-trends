from __future__ import annotations

import os
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from pynytimes import NYTAPI

from src.engagement import build_engagement_table
from src.keywords import extract_keywords_for_articles


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="NYT Trends Dashboard", layout="wide")
st.title("NYT Live Trends (Top Stories + Engagement)")
st.caption(
    "Engagement uses NYT 'Most Popular' lists (viewed/shared). "
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
    share_type = st.selectbox("Shares source", ["facebook", ""], index=0)

    st.subheader("Engagement weights")
    w_views = st.slider("Views", 0.0, 1.0, 0.50, 0.05)
    w_shares = st.slider("Shares", 0.0, 1.0, 0.40, 0.05)
    w_time = st.slider("Time (proxy)", 0.0, 1.0, 0.10, 0.05)

    st.subheader("Keywords")
    per_article_k = st.slider("Keywords/phrases per article", 3, 15, 6)
    ngram_min = st.selectbox("N-gram min", [1, 2], index=0)
    ngram_max = st.selectbox("N-gram max", [2, 3], index=0)

    refresh = st.button("Refresh now")

# Normalize weights
wsum = w_views + w_shares + w_time
weights = (0.50, 0.40, 0.10) if wsum == 0 else (w_views / wsum, w_shares / wsum, w_time / wsum)
st.sidebar.caption(f"Normalized → views={weights[0]:.2f}, shares={weights[1]:.2f}, time={weights[2]:.2f}")

# Load environment
load_dotenv()
api_key = os.getenv("NYT_API_KEY")
if not api_key:
    st.error("NYT_API_KEY not found in environment (.env)")
    st.stop()


# Client + caching
@st.cache_resource
def get_client() -> NYTAPI:
    return NYTAPI(key=api_key, parse_dates=True)

TTL = 300

@st.cache_data(ttl=TTL)
def fetch_top_stories(section_name: str) -> list[dict]:
    try:
        articles = get_client().top_stories(section=section_name)
        return articles if isinstance(articles, list) else []
    except Exception as e:
        st.error(f"Error fetching top stories: {e}")
        return []

@st.cache_data(ttl=TTL)
def fetch_most_popular(period_days: int, share_source: str) -> tuple[list[dict], list[dict]]:
    try:
        client = get_client()
        viewed = client.most_viewed(days=period_days) or []
        shared = client.most_shared(days=period_days, method=share_source) or []
        return (viewed, shared)
    except Exception as e:
        st.error(f"Error fetching most popular: {e}")
        return [], []

if refresh:
    st.cache_data.clear()


# ----------------------------- 
# Fetch data
# ----------------------------- 
top_raw = fetch_top_stories(section)
viewed, shared = fetch_most_popular(period, share_type)

# DEBUG: Show data flow
print(f"\nDATA FLOW DEBUG")
print(f"├─ Top Stories ({section}): {len(top_raw)} articles")
if top_raw:
    print(f"│  └─ Sample: {top_raw[0].get('title', 'N/A')[:60]}")
    print(f"│  └─ Keys: {list(top_raw[0].keys())}")
print(f"├─ Most Viewed (last {period} days): {len(viewed)} articles")
if viewed:
    print(f"│  └─ Sample: {viewed[0].get('title', 'N/A')[:60]}")
print(f"└─ Most Shared (last {period} days): {len(shared)} articles")
if shared:
    print(f"   └─ Sample: {shared[0].get('title', 'N/A')[:60]}")

# ----------------------------- 
# Build engagement table from Most Popular
# ----------------------------- 
engagement_df = build_engagement_table(viewed=viewed, shared=shared, weights=weights)

print(f"\nENGAGEMENT TABLE")
print(f"├─ Total articles: {len(engagement_df)}")
print(f"├─ Columns: {list(engagement_df.columns)}")
print(f"├─ Sample row:")
if len(engagement_df) > 0:
    sample = engagement_df.iloc[0]
    print(f"│  ├─ URL: {sample['url'][:80]}...")
    print(f"│  ├─ Title: {sample['title'][:60]}")
    print(f"│  ├─ Scores (views/shares/time): {sample['views_score']}/{sample['shares_score']}/{sample['time_score']}")
    print(f"│  └─ Engagement Score: {sample['engagement_score']} (source: {sample['engagement_source']})")
    
# Check URL coverage
urls_with_data = engagement_df[engagement_df['engagement_source'] != '']['url'].nunique()
print(f"└─ URLs with engagement data: {urls_with_data}/{len(engagement_df)}")

# Ensure title/abstract exist (Most Popular items usually have both, but be safe)
if "abstract" not in engagement_df.columns:
    engagement_df["abstract"] = ""

# Extract keywords once for engagement table and get global top terms
engagement_df["keywords"], global_top_terms = extract_keywords_for_articles(
    engagement_df,
    k=per_article_k,
    ngram_range=(ngram_min, ngram_max),
)

print(f"\nKEYWORDS EXTRACTED")
print(f"└─ Global top terms: {len(global_top_terms)} terms")
print(f"   └─ Sample terms:")
for _, row in global_top_terms.head(5).iterrows():
    print(f"      └─ {row['term']}: {row['score']:.4f}")

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
top_df["keywords"], _ = extract_keywords_for_articles(
    top_df,
    k=per_article_k,
    ngram_range=(ngram_min, ngram_max),
)

# Join engagement scores onto top stories (includes engagement_source indicator)
join_cols = ["url", "engagement_score", "views_score", "shares_score", "time_score", "engagement_source"]
join_cols = [c for c in join_cols if c in engagement_df.columns]
scores = engagement_df[join_cols].copy()

top_scored_df = top_df.merge(scores, on="url", how="left")

for c in ["engagement_score", "views_score", "shares_score", "time_score"]:
    if c in top_scored_df.columns:
        top_scored_df[c] = top_scored_df[c].fillna(0.0)

# Fill engagement_source with indicator for stories without engagement data
top_scored_df["engagement_source"] = top_scored_df["engagement_source"].fillna("no data")

top_scored_df = top_scored_df.sort_values("engagement_score", ascending=False).reset_index(drop=True)

# DEBUG: Show merge results
print(f"\n🔗 TOP STORIES MERGE")
print(f"├─ Top Stories count: {len(top_df)}")
print(f"├─ Matched with engagement data: {(top_scored_df['engagement_source'] != 'no data').sum()}")
print(f"├─ Without engagement data: {(top_scored_df['engagement_source'] == 'no data').sum()}")
if len(top_scored_df) > 0:
    matched = top_scored_df[top_scored_df['engagement_source'] != 'no data']
    if len(matched) > 0:
        print(f"└─ Top matched article:")
        top_match = matched.iloc[0]
        print(f"   ├─ Title: {top_match['title'][:60]}")
        print(f"   ├─ Score: {top_match['engagement_score']}")
        print(f"   └─ From: {top_match['engagement_source']}")
    else:
        print(f"└─ ⚠️  No Top Stories matched engagement data")


# -----------------------------
# Display tables
# -----------------------------
left, right = st.columns(2)

with left:
    st.subheader(f"Most Popular — Ranked by engagement_score (period={period} days)")
    display_cols = [
        "engagement_score", "views_score", "shares_score", "time_score",
        "title", "abstract", "keywords", "section", "published_date", "url"
    ]
    display_cols = [c for c in display_cols if c in engagement_df.columns]
    st.dataframe(engagement_df[display_cols].head(30), use_container_width=True)

with right:
    st.subheader(f"Top Stories ({section}) — Ranked by engagement_score (URL match)")
    st.caption("💡 Tip: 'no data' in source means article didn't appear in Most Popular lists")
    display_cols = [
        "engagement_score", "engagement_source", "views_score", "shares_score", "time_score",
        "title", "abstract", "keywords", "published_date", "byline", "url"
    ]
    display_cols = [c for c in display_cols if c in top_scored_df.columns]
    st.dataframe(top_scored_df[display_cols].head(30), use_container_width=True)

st.divider()


# -----------------------------
# Global keyword/key-phrase chart (across Top Stories)
# -----------------------------
st.subheader("Top Keywords & Key Phrases (Top Stories corpus)")

fig = px.bar(global_top_terms, x="score", y="term", orientation="h", title="TF-IDF Scores")
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ----------------------------- 
# Analytics Dashboard
# ----------------------------- 
st.header("📊 Analytics & Insights")

# Two column layout for main charts
col1, col2 = st.columns(2)

# Chart 1: Engagement by Section
with col1:
    st.subheader("Engagement by Section")
    
    # Calculate total engagement per section
    section_engagement = engagement_df.groupby('section')['engagement_score'].agg(['sum', 'count']).sort_values('sum', ascending=False)
    section_engagement = section_engagement[section_engagement['sum'] > 0]  # Only sections with data
    
    if len(section_engagement) > 0:
        fig_section = px.bar(
            section_engagement.reset_index(),
            x='section',
            y='sum',
            hover_data=['count'],
            title="Total Engagement Score by Section",
            labels={'sum': 'Total Engagement', 'count': 'Article Count'}
        )
        fig_section.update_layout(xaxis_title="Section", yaxis_title="Total Engagement Score")
        st.plotly_chart(fig_section, use_container_width=True)
        
        # Summary stats
        with st.expander("📈 Section Stats"):
            for idx, (section, row) in enumerate(section_engagement.iterrows()):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric(f"{section}", f"{row['sum']:.1f}", delta=f"{int(row['count'])} articles")
    else:
        st.info("No engagement data available for sections")

# Chart 2: Views vs Shares Scatter
with col2:
    st.subheader("Views vs Shares Analysis")
    
    # Filter for articles with data
    plot_df = engagement_df[engagement_df['engagement_source'] != 'no data'].copy()
    
    if len(plot_df) > 0:
        fig_scatter = px.scatter(
            plot_df,
            x='views_score',
            y='shares_score',
            size='engagement_score',
            color='section',
            hover_data=['title', 'engagement_score'],
            title="Views Score vs Shares Score",
            labels={'views_score': 'Views Score', 'shares_score': 'Shares Score'}
        )
        fig_scatter.update_layout(
            xaxis_title="Views Score (0-100)",
            yaxis_title="Shares Score (0-100)",
            height=500
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Key insights
        with st.expander("💡 Key Insights"):
            # Most viewed
            most_viewed = plot_df.nlargest(1, 'views_score').iloc[0]
            st.write(f"**Most Viewed:**")
            st.write(f"- {most_viewed['title'][:80]}")
            st.write(f"- Views: {most_viewed['views_score']:.0f}, Shares: {most_viewed['shares_score']:.0f}")
            
            # Most shared
            most_shared = plot_df.nlargest(1, 'shares_score').iloc[0]
            st.write(f"\n**Most Shared:**")
            st.write(f"- {most_shared['title'][:80]}")
            st.write(f"- Views: {most_shared['views_score']:.0f}, Shares: {most_shared['shares_score']:.0f}")
            
            # Correlation
            correlation = plot_df['views_score'].corr(plot_df['shares_score'])
            st.write(f"\n**Views-Shares Correlation:** {correlation:.2f}")
            if correlation < 0.3:
                st.write("🔍 Low correlation = Different content gets viewed vs shared")
            elif correlation < 0.7:
                st.write("🔍 Moderate correlation = Some alignment between views and shares")
            else:
                st.write("🔍 High correlation = Views and shares move together")
    else:
        st.info("No articles with engagement data to analyze")

