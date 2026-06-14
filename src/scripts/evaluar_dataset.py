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
from app.rag.retriever import retrieve

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


def compute_metrics(results: list[dict]) -> dict:
    classes = ["LOW", "MEDIUM", "HIGH"]
    # conf[real][predicho] = cantidad de casos
    conf = {e: {p: 0 for p in classes} for e in classes}
    for r in results:
        exp = r["expected_severity"]
        pred = r["final_risk"]
        if exp in classes and pred in classes:
            conf[exp][pred] += 1

    per_class = {}
    for cls in classes:
        tp = conf[cls][cls]
        fp = sum(conf[e][cls] for e in classes if e != cls)
        fn = sum(conf[cls][p] for p in classes if p != cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[cls] = {"precision": precision, "recall": recall, "f1": f1}

    macro_p = sum(m["precision"] for m in per_class.values()) / len(classes)
    macro_r = sum(m["recall"] for m in per_class.values()) / len(classes)
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(classes)
    return {
        "confusion": conf,
        "per_class": per_class,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
    }


def print_metrics(metrics: dict) -> None:
    classes = ["LOW", "MEDIUM", "HIGH"]
    conf = metrics["confusion"]

    print(f"\n{BOLD}MÉTRICAS DE CLASIFICACIÓN{RESET}\n")
    print(f"  Matriz de confusión  (filas = real, columnas = predicho)\n")
    print(f"  {'':14s}" + "".join(f"{'→ '+cls:>12s}" for cls in classes))
    for exp in classes:
        row = f"  {'Real '+exp:<14s}" + "".join(f"{conf[exp][pred]:>12d}" for pred in classes)
        print(row)

    print(f"\n  {'Clase':<8s} {'Precision':>10s} {'Recall':>10s} {'F1-score':>10s}")
    print(f"  {'-'*42}")
    for cls in classes:
        m = metrics["per_class"][cls]
        print(f"  {cls:<8s} {m['precision']:>10.2%} {m['recall']:>10.2%} {m['f1']:>10.2%}")
    print(f"  {'-'*42}")
    print(f"  {'Macro':<8s} {metrics['macro_precision']:>10.2%} {metrics['macro_recall']:>10.2%} {metrics['macro_f1']:>10.2%}\n")


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

    # RAG: recuperar contexto de conocimiento relevante para el mensaje actual
    last_history_text = history[-1]["texto"] if history else ""
    retrieved_context = retrieve(
        message=current_msg,
        url_reasons=url_result.reasons,
        text_patterns=text_result.patterns_matched,
        extra_context=last_history_text,
    )

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
            retrieved_context=retrieved_context,
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
        "retrieved_fichas": [l.split("\n")[0] for l in retrieved_context.split("\n\n") if l] if retrieved_context else [],
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
        if r.get("retrieved_fichas"):
            print(f"       RAG fichas: {', '.join(r['retrieved_fichas'])}")
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

    metrics = compute_metrics(results)
    print_metrics(metrics)


if __name__ == "__main__":
    asyncio.run(main())
