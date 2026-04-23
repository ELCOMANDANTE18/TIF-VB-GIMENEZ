import re
from pathlib import Path

from app.models.schemas import URLResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

_BLACKLIST_PATH = Path(__file__).parent.parent.parent / "data" / "blacklist.txt"

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
        self.blacklist = self._load_blacklist()

    def _load_blacklist(self) -> set[str]:
        try:
            return set(_BLACKLIST_PATH.read_text().splitlines())
        except FileNotFoundError:
            logger.warning("blacklist.txt not found at %s", _BLACKLIST_PATH)
            return set()

    def analyze(self, text: str) -> URLResult:
        urls = _URL_RE.findall(text)
        if not urls:
            return URLResult(score=0.0, urls_found=[], reasons=[])

        scores: list[float] = []
        reasons: list[str] = []

        for url in urls:
            url_score = 0.0
            domain = self._extract_domain(url)

            if domain in self.blacklist:
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

    @staticmethod
    def _extract_domain(url: str) -> str:
        url = re.sub(r'^https?://', '', url)
        return url.split('/')[0].lower()
