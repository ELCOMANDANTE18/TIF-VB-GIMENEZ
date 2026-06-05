"""
Evaluación del pipeline de detección contra dataset_evaluacion.json.
Corre los 8 casos de prueba usando URLAnalyzer + TextAnalyzer + UM Cloud AI
sin necesitar la base de datos.

Uso:
    cd src
    .venv/bin/python scripts/evaluar_dataset.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Asegura que src/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai import groq_client
from app.analysis.url_analyzer import URLAnalyzer
from app.analysis.text_analyzer import TextAnalyzer
from app.config import settings

DATASET_PATH = Path(__file__).parent.parent / "tests" / "dataset_evaluacion.json"

# Colores ANSI
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def heuristic_risk(url_score: float, text_score: float) -> str:
    score = url_score * settings.URL_WEIGHT + text_score * settings.TEXT_WEIGHT
    if score >= settings.RISK_THRESHOLD_HIGH:
        return "HIGH"
    elif score >= settings.RISK_THRESHOLD_MEDIUM:
        return "MEDIUM"
    return "LOW"


def combined_risk(heuristic: str, ai_severity: str) -> str:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    if order.get(ai_severity, 0) > order.get(heuristic, 0):
        return ai_severity
    return heuristic


async def run_case(case: dict, url_analyzer: URLAnalyzer, text_analyzer: TextAnalyzer) -> dict:
    mensajes = case["mensajes"]
    # El último mensaje es el "actual", el resto es historial
    current_msg = mensajes[-1]["texto"]
    history = [
        {"texto": m["texto"], "es_entrante": True}
        for m in mensajes[:-1]
    ]

    # Análisis heurístico solo sobre el mensaje actual (igual que el pipeline real)
    url_result = url_analyzer.analyze(current_msg)
    text_result = text_analyzer.analyze(current_msg)

    heuristic = heuristic_risk(url_result.score, text_result.score)

    # Análisis IA
    ai_result = {}
    ai_error = None
    try:
        ai_result = await groq_client.analyze_conversation(
            current_message=current_msg,
            conversation_history=history,
            url_score=url_result.score,
            text_score=text_result.score,
            reasons=url_result.reasons + text_result.patterns_matched,
            conversation_id=case["id"],
        )
    except Exception as exc:
        ai_error = str(exc)

    ai_severity = ai_result.get("severity", heuristic) if ai_result else heuristic
    final_risk = combined_risk(heuristic, ai_severity)

    return {
        "id": case["id"],
        "tipo": case["tipo"],
        "expected_severity": case["expected_severity"],
        "expected_is_phishing": case["expected_is_phishing"],
        "heuristic": heuristic,
        "ai_severity": ai_severity if ai_result else "N/A (sin IA)",
        "final_risk": final_risk,
        "ai_confidence": ai_result.get("confidence", 0.0) if ai_result else 0.0,
        "ai_category": ai_result.get("scam_category", "-") if ai_result else "-",
        "ai_mitre": ai_result.get("mitre_technique", "-") if ai_result else "-",
        "ai_lifecycle": ai_result.get("lifecycle_stage", "-") if ai_result else "-",
        "ai_action": ai_result.get("recommended_action", "-") if ai_result else "-",
        "url_score": url_result.score,
        "text_score": text_result.score,
        "ai_error": ai_error,
        "pass": final_risk == case["expected_severity"],
    }


async def main():
    print(f"\n{BOLD}{CYAN}=== Evaluación del Dataset de Phishing ==={RESET}")
    print(f"Dataset: {DATASET_PATH}")
    print(f"Modelo UM Cloud: {settings.UM_MODEL}")
    print(f"UM_API_KEY configurada: {'Sí' if settings.UM_API_KEY else 'NO - resultados solo heurísticos'}")
    print()

    cases = json.loads(DATASET_PATH.read_text())
    url_analyzer = URLAnalyzer()
    text_analyzer = TextAnalyzer()

    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case['id']} — {case['tipo']}...", end=" ", flush=True)
        result = await run_case(case, url_analyzer, text_analyzer)
        results.append(result)
        status = f"{GREEN}PASS{RESET}" if result["pass"] else f"{RED}FAIL{RESET}"
        print(f"{status} (esperado: {result['expected_severity']}, obtenido: {result['final_risk']})")

    # Resumen
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}RESULTADOS DETALLADOS{RESET}\n")

    for r in results:
        status_color = GREEN if r["pass"] else RED
        status_label = "PASS" if r["pass"] else "FAIL"
        print(f"{status_color}{BOLD}[{status_label}]{RESET} {r['id']} — {r['tipo']}")
        print(f"       Esperado: {r['expected_severity']:6s} | Heurístico: {r['heuristic']:6s} | IA: {r['ai_severity']:6s} | Final: {r['final_risk']}")
        print(f"       URL score: {r['url_score']:.2f} | Text score: {r['text_score']:.2f} | Confianza IA: {r['ai_confidence']:.0%}")
        if r["ai_category"] != "-":
            print(f"       Categoría: {r['ai_category']} | MITRE: {r['ai_mitre']} | Fase: {r['ai_lifecycle']} | Acción: {r['ai_action']}")
        if r["ai_error"]:
            print(f"       {YELLOW}Error IA: {r['ai_error']}{RESET}")
        print()

    pct = passed / total * 100
    color = GREEN if pct >= 80 else YELLOW if pct >= 60 else RED
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}SCORE FINAL: {color}{passed}/{total} ({pct:.0f}%){RESET}\n")

    if pct < 100:
        fallidos = [r["id"] for r in results if not r["pass"]]
        print(f"{YELLOW}Casos fallidos: {', '.join(fallidos)}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
