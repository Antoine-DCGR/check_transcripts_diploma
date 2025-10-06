#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json

from revision.pdf_revision import analyze_pdf_complete, PdfResurrectNotFound
from metadata.scan_validator import validate_scan_document
from rescan.rescan_detector import (
    RescanDetector,
    build_rescan_json,
    QUALITY_CORE_MIN, QUALITY_CORE_MAX, ART_CORE_MIN, ART_CORE_MAX
)

# -------------------------
# Helpers
# -------------------------

def _norm_verdict(v: str) -> str:
    v = (v or "").strip().lower()
    if v in ("valid", "ok"):
        return "valid"
    if v in ("borderline", "suspect", "warning", "warn"):
        return "suspect"
    if v in ("invalid", "invalide"):
        return "invalid"
    if v in ("falsified", "forged"):
        return "falsified"
    return "unknown"

def _priority(verdict: str) -> int:
    # ordre: falsified(3) > invalid(2) > suspect(1) > valid/unknown(0)
    v = _norm_verdict(verdict)
    return {"falsified": 3, "invalid": 2, "suspect": 1}.get(v, 0)

def _init_overall():
    return {"verdict": "valid", "reasons": []}

def _update_overall(report: dict, new_verdict: str, reason: str):
    """
    - Met à jour le verdict global s'il est plus grave.
    - N'ajoute une raison que si le verdict est problématique.
      (suspect | invalid | falsified | unknown)
    - La raison est le message détaillé passé par l'appelant.
    """
    if "overall" not in report or not isinstance(report["overall"], dict):
        report["overall"] = _init_overall()
    cur_v = report["overall"].get("verdict", "valid")

    if _priority(new_verdict) > _priority(cur_v):
        report["overall"]["verdict"] = _norm_verdict(new_verdict)

    v_norm = _norm_verdict(new_verdict)
    if reason and v_norm in ("suspect", "invalid", "falsified", "unknown"):
        report["overall"].setdefault("reasons", [])
        report["overall"]["reasons"].append(reason)

# -------------------------
# Main
# -------------------------

def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python3 main.py <fichier.pdf>"}, ensure_ascii=False, indent=2))
        sys.exit(2)

    pdf_path = sys.argv[1]
    file_nature = "scan"

    report = {
        "document": {"path": pdf_path, "type": file_nature},
        "revision": {},
        "metadata": {},
        "criteria": {},
        "overall": _init_overall(),
    }

    # 1) Révisions
    try:
        rev_res = analyze_pdf_complete(pdf_path)
        if isinstance(rev_res, dict):
            rewrites = rev_res.get("rewrites")
            if isinstance(rewrites, int) and rewrites > 0:
                msg = rev_res.get("message", "Réécritures détectées")
                report["revision"] = {"verdict": "falsified", "message": msg}
                _update_overall(report, "falsified", msg)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                sys.exit(0)
            else:
                msg = rev_res.get("message", "Révisions cohérentes")
                report["revision"] = {"verdict": "valid", "message": msg}
                _update_overall(report, "valid", msg)  # pas ajouté aux reasons (verdict non problématique)
        else:
            msg = "Format inattendu analyze_pdf_with_cli"
            report["revision"] = {"verdict": "unknown", "message": msg}
            _update_overall(report, "unknown", msg)
    except PdfResurrectNotFound:
        msg = "pdfresurrect introuvable"
        report["revision"] = {"verdict": "unknown", "message": msg}
        _update_overall(report, "unknown", msg)
    except Exception as e:
        msg = f"Erreur analyse révisions: {e!r}"
        report["revision"] = {"verdict": "invalid", "message": msg}
        _update_overall(report, "invalid", msg)

    # 2) Métadonnées
    try:
        md_res = validate_scan_document(pdf_path)
        if isinstance(md_res, dict):
            v = _norm_verdict(md_res.get("verdict", "unknown"))
            msg = md_res.get("message", "")
            report["metadata"] = {"verdict": v, "message": msg}
            _update_overall(report, v, msg)
            if v in ("falsified", "invalid"):
                print(json.dumps(report, ensure_ascii=False, indent=2))
                sys.exit(0)
        else:
            msg = "Retour inattendu analyse métadonnées"
            report["metadata"] = {"verdict": "invalid", "message": msg}
            _update_overall(report, "invalid", msg)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            sys.exit(0)
    except Exception as e:
        msg = f"Erreur analyse métadonnées: {e!r}"
        report["metadata"] = {"verdict": "invalid", "message": msg}
        _update_overall(report, "invalid", msg)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 3) Re-scan (qualité/artefacts par intervalles)
    try:
        rd = RescanDetector()
        ra = rd.analyze_pdf(pdf_path)
        if isinstance(ra, dict) and "error" in ra:
            msg = ra.get("error") or "Erreur rescan"
            report["criteria"]["rescan"] = {"verdict": "unknown", "message": msg}
            _update_overall(report, "unknown", msg)
        else:
            qual = float(ra["avg_quality_score"])
            art  = float(ra["avg_artifact_score"])
            rz   = build_rescan_json(ra["file_path"], qual, art)

            level = rz["rescan"]["level"]     # "core" | "suspect" | "none"
            message = rz["rescan"]["message"]

            if level == "core":
                vtxt = "falsified"
            elif level == "suspect":
                vtxt = "suspect"
            else:
                vtxt = "valid"

            report["criteria"]["rescan"] = {
                "verdict": vtxt,
                "message": message,
                "scores": {
                    "quality_avg": round(qual, 1),
                    "artifact_avg": round(art, 1),
                    "quality_interval_core": [QUALITY_CORE_MIN, QUALITY_CORE_MAX],
                    "artifact_interval_core": [ART_CORE_MIN, ART_CORE_MAX]
                }
            }

            if level == "core":
                _update_overall(report, "falsified", message)
                print(json.dumps(report, ensure_ascii=False, indent=2))
                sys.exit(0)
            elif level == "suspect":
                _update_overall(report, "suspect", message)
            else:
                _update_overall(report, "valid", message)  # pas ajouté aux reasons
    except Exception as e:
        msg = f"Erreur rescan: {type(e).__name__}: {e}"
        report["criteria"]["rescan"] = {
            "verdict": "unknown",
            "message": msg
        }
        _update_overall(report, "unknown", msg)

    # Sortie finale (statut tel qu'il a évolué)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
