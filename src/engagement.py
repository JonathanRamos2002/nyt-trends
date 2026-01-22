from __future__ import annotations

from typing import Any, Dict, List, Tuple
import math
import pandas as pd


def _safe_text(article: Dict[str, Any]) -> str:
    title = (article.get("title") or "").strip()
    abstract = (article.get("abstract") or "").strip()
    byline = (article.get("byline") or "").strip()
    return " ".join(x for x in [title, abstract, byline] if x)


def estimate_read_minutes(text: str, words_per_minute: int = 220) -> float:
    words = len(text.split())
    return 0.0 if words == 0 else words / float(words_per_minute)


def _rank_scores(items: List[Dict[str, Any]], key: str = "url") -> Dict[str, float]:
    scores: Dict[str, float] = {}
    n = len(items)
    for i, a in enumerate(items):
        url = a.get(key)
        if url:
            scores[url] = float(n - i)
    return scores


def _minmax(series: pd.Series) -> pd.Series:
    mn = float(series.min())
    mx = float(series.max())
    if math.isclose(mx, mn):
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


def build_engagement_table(
    viewed: List[Dict[str, Any]],
    emailed: List[Dict[str, Any]],
    shared: List[Dict[str, Any]],
    weights: Tuple[float, float, float, float] = (0.40, 0.30, 0.20, 0.10),
) -> pd.DataFrame:
    w_views, w_shares, w_emails, w_time = weights

    views_rank = _rank_scores(viewed)
    emails_rank = _rank_scores(emailed)
    shares_rank = _rank_scores(shared)

    all_urls = sorted(set(views_rank) | set(emails_rank) | set(shares_rank))

    article_by_url: Dict[str, Dict[str, Any]] = {}
    for lst in (viewed, emailed, shared):
        for a in lst:
            u = a.get("url")
            if u and u not in article_by_url:
                article_by_url[u] = a

    rows = []
    for url in all_urls:
        a = article_by_url.get(url, {})
        text = _safe_text(a)
        est_minutes = estimate_read_minutes(text)
        rows.append(
            {
                "url": url,
                "title": a.get("title", ""),
                "section": a.get("section", ""),
                "published_date": a.get("published_date", ""),
                "views_raw": views_rank.get(url, 0.0),
                "shares_raw": shares_rank.get(url, 0.0),
                "emails_raw": emails_rank.get(url, 0.0),
                "time_raw": est_minutes,
            }
        )

    df = pd.DataFrame(rows)

    df["views_score"] = (_minmax(df["views_raw"]) * 100).round(2)
    df["shares_score"] = (_minmax(df["shares_raw"]) * 100).round(2)
    df["emails_score"] = (_minmax(df["emails_raw"]) * 100).round(2)
    df["time_score"] = (_minmax(df["time_raw"]) * 100).round(2)

    df["engagement_score"] = (
        w_views * df["views_score"]
        + w_shares * df["shares_score"]
        + w_emails * df["emails_score"]
        + w_time * df["time_score"]
    ).round(2)

    return df.sort_values("engagement_score", ascending=False).reset_index(drop=True)
