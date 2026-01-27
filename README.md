# NYT Trends Dashboard

A **real-time analytics dashboard** that combines editorial judgment with reader engagement metrics to identify trending news topics across The New York Times.

##  Overview

This dashboard answers: **"What are readers actually engaging with?"** by overlaying engagement data (views, shares, reading time) onto editorial picks (Top Stories).

**Key Insight:** Editors decide what's important → Readers decide what's engaging. This tool shows where they align.

---

##  Features

###  Core Analytics
- **Engagement Scoring** - Combines views, shares, and reading time (user-adjustable weights)
- **Section Analysis** - See which news categories drive engagement
- **Views vs Shares** - Discover what content people consume vs promote
- **Trending Keywords** - Top 10 keywords in highest-engagement articles
- **Top Stories Integration** - Match editorial picks against engagement data

###  Technical Highlights
- **Clean Architecture** - Modular, testable code with separation of concerns
- **Efficient NLP** - Single TF-IDF pass for per-article + global keyword extraction
- **Data Quality** - Clear indicators for articles without engagement data
- **Caching** - 5-minute TTL on API calls to respect rate limits
- **Debug Logging** - Print statements show data flow at each step

---

##  Quick Start

### Prerequisites
- Python 3.8+
- NYT API Key ([Get one here](https://developer.nytimes.com/))

### Installation

```bash
# Clone the repository
git clone https://github.com/jonathanramos/nyt-trends.git
cd nyt-trends

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "NYT_API_KEY=your_api_key_here" > .env
```

### Run the Dashboard

```bash
streamlit run app.py
```

Visit `http://localhost:8501` in your browser.

---

##  How It Works

### Data Flow

```
┌─ fetch_top_stories(section)        Top Stories from NYT (editorial picks)
│                                    ↓
┌─ fetch_most_popular(period)        Most Viewed + Most Shared articles
│                                    ↓
├─ build_engagement_table()          Combine by URL, score by weights
│                                    ↓
├─ extract_keywords_for_articles()   TF-IDF keyword extraction
│                                    ↓
└─ Display & Analyze                 Dashboard charts + tables
```

### Engagement Score Calculation

```
engagement_score = (w_views × views_score) + (w_shares × shares_score) + (w_time × time_score)
```

- **w_views**: Weight for article views (default 0.50)
- **w_shares**: Weight for article shares (default 0.40)
- **w_time**: Weight for reading time proxy (default 0.10)

All scores normalized to 0-100 scale using min-max normalization.

---

##  Configuration

### Sidebar Controls

| Control | Options | Impact |
|---------|---------|--------|
| **Top Stories Section** | home, world, business, tech, science, health, sports, arts, politics | Which editorial section to analyze |
| **Most Popular Period** | 1, 7, 30 days | Historical engagement window |
| **Shares Source** | facebook, email* | Which share metric to use |
| **Engagement Weights** | 0.0-1.0 sliders | Normalize importance of each metric |
| **Keywords per Article** | 3-15 | How many keywords to extract |
| **N-gram Range** | 1-grams, 2-grams | Single words vs 2-word phrases |
| **Refresh Now** | Button | Clear cache and fetch fresh data |

*Note: pynytimes currently supports Facebook shares. Email shares available via direct API.*

---

##  Project Structure

```
nyt-trends/
├── app.py                      # Main Streamlit dashboard
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not in git)
│
├── src/
│   ├── __init__.py
│   ├── engagement.py           # Engagement scoring logic
│   │   └── build_engagement_table()
│   │   └── estimate_read_minutes()
│   │   └── _rank_scores()
│   └── keywords.py             # TF-IDF keyword extraction
│       └── extract_keywords_for_articles()
│
└── README.md                   # This file
```

---

##  Dashboard Sections

### 1. **Most Popular Table** (Left)
Ranked by engagement score. Shows views, shares, time estimates, and extracted keywords.

### 2. **Top Stories Table** (Right)
Editorial picks ranked by engagement. Includes `engagement_source` indicator:
- `"viewed"` - Only in most-viewed list
- `"shared"` - Only in most-shared list
- `"viewed, shared"` - In both lists (strongest signal)
- `"no data"` - Not in any Most Popular list

### 3. **Keywords Chart** (Global)
Top 25 keywords/phrases across entire Top Stories corpus using TF-IDF scoring.

### 4. **Engagement by Section** (Analytics)
Bar chart showing total engagement per news category. Expandable stats with counts.

### 5. **Views vs Shares Analysis** (Analytics)
Scatter plot with bubble size = engagement score, color = section. Reveals:
- Most viewed articles
- Most shared articles
- Correlation between views and shares

### 6. **Trending Keywords** (Analytics)
Top 10 keywords from the 10 highest-engagement articles with full article context.

---

### Analytics
- **Engagement by Section** - Identify which news categories drive engagement
- **Views vs Shares scatter** - See what content people consume vs share
- **Trending Keywords** - Top 10 keywords in high-engagement articles with full context

---

##  License

See [LICENSE](LICENSE) file.

---

##  Authors

Jonathan Ramos & 
Chris Koelsch

---

##  Resources

- [pynytimes Documentation](https://github.com/michadenheijer/pynytimes)
- [NYT API Docs](https://developer.nytimes.com/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [scikit-learn TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)

---

**Last Updated:** January 27, 2026