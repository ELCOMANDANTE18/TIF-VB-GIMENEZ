import csv
import re
from pathlib import Path

import httpx

from app.models.schemas import URLResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

_BLACKLIST_PATH = Path(__file__).parent.parent.parent / "data" / "blacklist.txt"
_PHISHTANK_PATH = Path(__file__).parent.parent.parent / "data" / "blacklist" / "phishtank.csv"

_URL_RE = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+', re.IGNORECASE)

_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl",
    "ow.ly", "short.io", "rb.gy", "cutt.ly",
}

_SUSPICIOUS_KEYWORDS = {
    "login", "verify", "account", "secure", "update",
    "confirm", "password", "credential", "banking",
    "paypal", "amazon", "apple", "microsoft",
}


class URLAnalyzer:
    def __init__(self) -> None:
        self.blacklist, self.phishtank_domains = self._load_blacklist()

    def _load_blacklist(self) -> tuple[set[str], set[str]]:
        blacklist: set[str] = set()
        phishtank_domains: set[str] = set()

        try:
            with _PHISHTANK_PATH.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    url = row.get("url", "").strip()
                    if url:
                        domain = self._extract_domain(url)
                        if domain:
                            phishtank_domains.add(domain)
            logger.info("PhishTank: %d domains loaded", len(phishtank_domains))
        except FileNotFoundError:
            logger.warning("phishtank.csv not found at %s", _PHISHTANK_PATH)
        except Exception as exc:
            logger.warning("Failed to load phishtank.csv: %s", exc)

        try:
            blacklist = set(_BLACKLIST_PATH.read_text().splitlines())
            logger.info("blacklist.txt: %d entries loaded", len(blacklist))
        except FileNotFoundError:
            pass

        return blacklist, phishtank_domains

    def analyze(self, text: str) -> URLResult:
        urls = _URL_RE.findall(text)
        if not urls:
            return URLResult(score=0.0, urls_found=[], reasons=[])

        scores: list[float] = []
        reasons: list[str] = []

        for url in urls:
            url_score = 0.0
            domain = self._extract_domain(url)

            if domain in self.blacklist or domain in self.phishtank_domains:
                url_score += 1.0
                reasons.append(f"Blacklisted domain: {domain}")

            if url.startswith("http://"):
                url_score += 0.3
                reasons.append(f"Insecure HTTP: {url}")

            if domain in _SHORTENERS:
                url_score += 0.4
                reasons.append(f"URL shortener detected: {domain}")

            for kw in _SUSPICIOUS_KEYWORDS:
                if kw in url.lower():
                    url_score += 0.2
                    reasons.append(f"Suspicious keyword '{kw}' in URL")
                    break

            if len(url) > 100:
                url_score += 0.2
                reasons.append(f"Suspiciously long URL ({len(url)} chars)")

            scores.append(min(url_score, 1.0))

        return URLResult(
            score=max(scores),
            urls_found=urls,
            reasons=reasons,
        )

    async def analyze_with_urlhaus(self, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    "https://urlhaus-api.abuse.ch/v1/url/",
                    data={"url": url},
                )
                return response.json()
        except Exception:
            return {}

    @staticmethod
    def _extract_domain(url: str) -> str:
        url = re.sub(r'^https?://', '', url)
        return url.split('/')[0].lower()
