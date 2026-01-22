import json
import os
import requests
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional

TOP_STORIES_BASE = "https://api.nytimes.com/svc/topstories/v2"
MOST_POPULAR_BASE = "https://api.nytimes.com/svc/mostpopular/v2"


def get_api_key() -> str:
    load_dotenv()
    key = os.getenv("NYT_API_KEY")
    if not key:
        raise ValueError("NYT_API_KEY not found in environment (.env).")
    return key


def fetch_json(url: str, params: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    """Small wrapper so all requests behave consistently."""
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_top_stories(section: str = "home") -> Dict[str, Any]:
    """
    Top Stories endpoint pattern:
    /svc/topstories/v2/{section}.json?api-key=...
    """
    api_key = get_api_key()
    url = f"{TOP_STORIES_BASE}/{section}.json"
    return fetch_json(url, params={"api-key": api_key})


def normalize_top_stories(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert Top Stories JSON to a list of flat rows."""
    rows: List[Dict[str, Any]] = []
    for a in data.get("results", []):
        rows.append(
            {
                "source": "top_stories",
                "section": a.get("section"),
                "subsection": a.get("subsection"),
                "title": a.get("title"),
                "abstract": a.get("abstract"),
                "byline": a.get("byline"),
                "url": a.get("url"),
                "published_date": a.get("published_date"),
                # NYT provides curated facets — very useful as “keywords”
                "des_facet": a.get("des_facet") or [],
                "org_facet": a.get("org_facet") or [],
                "per_facet": a.get("per_facet") or [],
                "geo_facet": a.get("geo_facet") or [],
            }
        )
    return rows


def fetch_most_popular_viewed(period: int = 1) -> Dict[str, Any]:
    """
    Many examples use:
      /svc/mostpopular/v2/viewed/{period}.json
    Some NYT OpenAPI specs also show a by-section variant like:
      /svc/mostpopular/v2/mostviewed/{section}/{period}.json
    We'll try the common one first and fall back to the by-section style.
    """
    api_key = get_api_key()

    # common form (widely used in examples)
    url1 = f"{MOST_POPULAR_BASE}/viewed/{period}.json"
    try:
        return fetch_json(url1, params={"api-key": api_key})
    except requests.HTTPError:
        # fallback: by-section form from the public API spec
        url2 = f"{MOST_POPULAR_BASE}/mostviewed/all-sections/{period}.json"
        return fetch_json(url2, params={"api-key": api_key})


def fetch_most_popular_shared(period: int = 1) -> Dict[str, Any]:
    api_key = get_api_key()
    url1 = f"{MOST_POPULAR_BASE}/shared/{period}.json"
    try:
        return fetch_json(url1, params={"api-key": api_key})
    except requests.HTTPError:
        url2 = f"{MOST_POPULAR_BASE}/mostshared/all-sections/{period}.json"
        return fetch_json(url2, params={"api-key": api_key})


def normalize_most_popular(data: Dict[str, Any], metric: str) -> List[Dict[str, Any]]:
    """
    Flatten Most Popular results.
    'metric' is something like: 'viewed' or 'shared'
    """
    rows: List[Dict[str, Any]] = []
    for a in data.get("results", []):
        rows.append(
            {
                "source": f"most_popular_{metric}",
                "section": a.get("section"),
                "title": a.get("title"),
                "abstract": a.get("abstract"),
                "byline": a.get("byline"),
                "url": a.get("url"),
                "published_date": a.get("published_date"),
                # these fields depend on the route:
                "views": a.get("views"),
                "total_shares": a.get("total_shares"),
                "adx_keywords": a.get("adx_keywords"),
            }
        )
    return rows


if __name__ == "__main__":
    # quick sanity check: run `python nyt.py`
    data = fetch_top_stories("home")
    rows = normalize_top_stories(data)
    print(f"Top Stories rows: {len(rows)}")
    print(rows[0] if rows else "No rows returned.")


    

