from __future__ import annotations

from typing import Iterable, Tuple
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


def build_corpus(rows: pd.DataFrame) -> list[str]:
    """Combine title + abstract into one text field."""
    titles = rows["title"].fillna("")
    abstracts = rows["abstract"].fillna("")
    return (titles + " " + abstracts).tolist()


def top_terms_tfidf(
    texts: Iterable[str],
    top_n: int = 25,
    ngram_range: Tuple[int, int] = (1, 2),
) -> pd.DataFrame:
    """
    TF-IDF over 1-grams + 2-grams gives you:
      - keywords (1-grams)
      - key phrases (2-grams)
    """
    vec = TfidfVectorizer(
        stop_words="english",
        ngram_range=ngram_range,
        min_df=1,
        max_features=5000,
    )
    X = vec.fit_transform(list(texts))
    scores = X.sum(axis=0).A1  # sum TF-IDF across docs
    terms = vec.get_feature_names_out()

    out = (
        pd.DataFrame({"term": terms, "score": scores})
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    return out
