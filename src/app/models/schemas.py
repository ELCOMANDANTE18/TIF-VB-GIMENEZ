from enum import Enum
from pydantic import BaseModel


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IncomingMessage(BaseModel):
    sender_id: str
    text: str


class URLResult(BaseModel):
    score: float
    urls_found: list[str]
    reasons: list[str]


class TextResult(BaseModel):
    score: float
    patterns_matched: list[str]


class AnalysisResult(BaseModel):
    sender_id: str
    text: str
    risk_level: RiskLevel
    final_score: float
    url_result: URLResult
    text_result: TextResult
    ai_explanation: str = ""
    ai_recommendation: str = ""
    ai_confidence: float = 0.0
    ai_patterns: list[str] = []
