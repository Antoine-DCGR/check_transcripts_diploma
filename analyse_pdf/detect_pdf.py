#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys

from analyse_pdf.revision.pdf_revision import analyze_pdf_complete
from analyse_pdf.metadata.scan_validator import validate_scan_document
from analyse_pdf.ia_detector.ia_detector import analyze_pdf_structure
from analyse_pdf.rescan.rescan_detector import RescanDetector


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def init_overall():
    return {"verdict": "valid", "reasons": [], "score": 0}


def add_reason(report, reason):
    if reason and reason not in report["overall"]["reasons"]:
        report["overall"]["reasons"].append(reason)


# -------------------------------------------------
# CORE ANALYSIS
# -------------------------------------------------

def analyse_pdf(file_path: str) -> dict:
    report = {
        "document": {"path": file_path, "type": "scan"},
        "revision": {},
        "metadata": {},
        "criteria": {},
        "overall": init_overall(),
    }

    global_score = 0

    # =================================================
    # 1️⃣ PDF REVISION
    # =================================================
    rev = analyze_pdf_complete(file_path)
    report["revision"] = rev

    rev_score = rev.get("score", 0)
    global_score += rev_score
    if rev_score > 0:
        add_reason(report, rev.get("message"))

    # =================================================
    # 2️⃣ METADATA
    # =================================================
    md = validate_scan_document(file_path)
    report["metadata"] = md

    md_score = md.get("score", 0)
    global_score += md_score
    if md_score > 0:
        add_reason(report, md.get("message"))

  

    # =================================================
    # 4️⃣ RESCAN
    # =================================================
    try:
        rd = RescanDetector()
        rescan = rd.analyze_pdf(file_path)
        report["criteria"]["rescan"] = rescan

        rescan_score = rescan.get("score", 0)
        global_score += rescan_score
        if rescan_score > 0:
            add_reason(report, rescan.get("message"))

    except Exception as e:
        report["criteria"]["rescan"] = {
            "verdict": "unknown",
            "score": 0,
            "message": str(e),
        }

    

    # =================================================
    # 🧠 VERDICT FINAL — RÈGLE UNIQUE PAR SCORE
    # =================================================
    report["overall"]["score"] = global_score

    if global_score >= 3:
        report["overall"]["verdict"] = "falsified"
    elif global_score == 2:
        report["overall"]["verdict"] = "suspect"
    else:
        report["overall"]["verdict"] = "valid"

    return report


# -------------------------------------------------
# CLI
# -------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python detect_pdf.py <file.pdf>"}))
        sys.exit(2)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(json.dumps({"error": "File not found"}))
        sys.exit(1)

    result = analyse_pdf(pdf_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
