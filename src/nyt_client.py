import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass(frozen=True)
class NYTClient:
    api_key: str
    timeout: int = 20
    session: Optional[requests.Session] = None

    def _get(self, url: str) -> Dict[str, Any]:
        s = self.session or requests.Session()
        resp = s.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # Top Stories (what's on a section front)
    def top_stories(self, section: str = "home") -> List[Dict[str, Any]]:
        url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json?api-key={self.api_key}"
        data = self._get(url)
        return data.get("results", [])

    # Most Popular (ranked engagement lists)
    def most_viewed(self, period: int = 7) -> List[Dict[str, Any]]:
        self._validate_period(period)
        url = f"https://api.nytimes.com/svc/mostpopular/v2/viewed/{period}.json?api-key={self.api_key}"
        data = self._get(url)
        return data.get("results", [])

    def most_emailed(self, period: int = 7) -> List[Dict[str, Any]]:
        self._validate_period(period)
        url = f"https://api.nytimes.com/svc/mostpopular/v2/emailed/{period}.json?api-key={self.api_key}"
        data = self._get(url)
        return data.get("results", [])

    def most_shared(self, period: int = 7, share_type: str = "facebook") -> List[Dict[str, Any]]:
        self._validate_period(period)
        # common share_type values used in docs/examples: "facebook", "email"
        url = f"https://api.nytimes.com/svc/mostpopular/v2/shared/{period}/{share_type}.json?api-key={self.api_key}"
        data = self._get(url)
        return data.get("results", [])

    @staticmethod
    def _validate_period(period: int) -> None:
        if period not in (1, 7, 30):
            raise ValueError("period must be one of: 1, 7, 30")
