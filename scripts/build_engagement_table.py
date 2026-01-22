import os, sys
print("DEBUG: running build_engagement_table")
print("DEBUG: exe:", sys.executable)
print("DEBUG: cwd:", os.getcwd())
print("DEBUG: sys.path[0]:", sys.path[0])

import os
from dotenv import load_dotenv

from src.nyt_client import NYTClient
from src.engagement import build_engagement_table

print("RUNNING build_engagement_table.py")

def main() -> None:
    load_dotenv()
    api_key = os.getenv("NYT_API_KEY")
    if not api_key:
        raise ValueError("NYT_API_KEY not found in environment (.env)")

    client = NYTClient(api_key=api_key)

    period = 7
    viewed = client.most_viewed(period=period)
    emailed = client.most_emailed(period=period)
    shared = client.most_shared(period=period, share_type="facebook")

    df = build_engagement_table(
        viewed=viewed,
        emailed=emailed,
        shared=shared,
        weights=(0.40, 0.30, 0.20, 0.10),
    )

    # Print a clean preview
    cols = ["engagement_score", "views_score", "shares_score", "emails_score", "time_score", "title", "section", "published_date"]
    print(df[cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()

