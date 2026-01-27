"""
Keyword extraction using TF-IDF for articles.
Efficiently computes keywords once and reuses results.
"""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def extract_keywords_for_articles(
    df: pd.DataFrame,
    k: int = 6,
    ngram_range: tuple[int, int] = (1, 2),
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Extract keywords for each article using TF-IDF.
    
    Args:
        df: DataFrame with 'title' and 'abstract' columns
        k: Number of keywords per article
        ngram_range: (min_ngram, max_ngram)
    
    Returns:
        (per_article_keywords, global_top_terms)
        - per_article_keywords: Series of comma-separated keywords for each row
        - global_top_terms: DataFrame with top 25 terms across corpus
    """
    texts = (
        df["title"].fillna("").astype(str) + " " + df["abstract"].fillna("").astype(str)
    ).tolist()

    # If everything is empty, return blanks
    if not any(t.strip() for t in texts):
        return (
            pd.Series([""] * len(df), index=df.index),
            pd.DataFrame({"term": [], "score": []})
        )

    # Fit TF-IDF on all texts
    vec = TfidfVectorizer(
        stop_words="english",
        ngram_range=ngram_range,
        max_features=8000
    )
    X = vec.fit_transform(texts)
    terms = vec.get_feature_names_out()

    # Extract per-article keywords
    keywords = []
    for i in range(X.shape[0]):
        row = X.getrow(i)
        if row.nnz == 0:
            keywords.append("")
            continue
        # Get top-k indices by tfidf score
        scores = row.data
        idxs = row.indices
        top = np.argsort(scores)[-k:][::-1]
        kws = [terms[idxs[j]] for j in top]
        keywords.append(", ".join(kws))

    per_article = pd.Series(keywords, index=df.index)

    # Compute global top terms (sum TF-IDF across all docs)
    global_scores = X.sum(axis=0).A1
    global_top = (
        pd.DataFrame({"term": terms, "score": global_scores})
        .sort_values("score", ascending=False)
        .head(25)
        .reset_index(drop=True)
    )

    return per_article, global_top
