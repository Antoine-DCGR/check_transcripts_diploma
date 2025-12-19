#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Détection de révisions PDF
LOGIQUE UNIQUEMENT FRAUDE (pas de verdict valid ici)

Barème :
- +3 : réécriture PDF détectée (pdfresurrect)
- +3 : dates PDF incohérentes (CreationDate != ModDate)
- +1 : dates système incohérentes
- 0  : aucun signal détecté
"""

import os
import shutil
import subprocess
from typing import Dict, Optional

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class PdfResurrectNotFound(RuntimeError):
    pass


# ---------------------------------------------------------
# pdfresurrect — SIGNAL FORT (+3)
# ---------------------------------------------------------

def analyze_with_pdfresurrect(pdf_path: str) -> Optional[Dict]:
    if not shutil.which("pdfresurrect"):
        raise PdfResurrectNotFound("pdfresurrect introuvable")

    try:
        out = subprocess.check_output(
            ["pdfresurrect", "-q", pdf_path],
            stderr=subprocess.STDOUT,
            text=True
        )

        versions = [
            line for line in out.splitlines()
            if line.strip().lower().startswith("revision")
        ]

        rewrites = max(0, len(versions) - 1)

        if rewrites >= 1:
            return {
                "method": "pdfresurrect",
                "rewrites": rewrites,
                "score": 3,
                "signal": "strong",
                "message": f"{rewrites} réécriture(s) PDF détectée(s) (signal fort)"
            }

        return None

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erreur pdfresurrect: {e}")


# ---------------------------------------------------------
# Dates — SIGNAL FORT (+3) / FAIBLE (+1)
# ---------------------------------------------------------

def analyze_with_dates(pdf_path: str) -> Dict:
    try:
        stat = os.stat(pdf_path)
        file_ctime = stat.st_ctime
        file_mtime = stat.st_mtime

        pdf_creation = None
        pdf_mod = None

        if PYPDF2_AVAILABLE:
            try:
                with open(pdf_path, "rb") as f:
                    reader = PdfReader(f)
                    if reader.metadata:
                        pdf_creation = reader.metadata.get("/CreationDate")
                        pdf_mod = reader.metadata.get("/ModDate")
            except Exception:
                pass

        # 🔴 SIGNAL FORT — dates PDF incohérentes
        if pdf_creation and pdf_mod and pdf_creation != pdf_mod:
            return {
                "method": "pdf_metadata_dates",
                "score": 2 ,
                "signal": "strong",
                "message": "Dates PDF incohérentes (CreationDate ≠ ModDate)"
            }

        # 🟡 SIGNAL FAIBLE — dates système incohérentes
        if abs(file_ctime - file_mtime) > 3.0:
            return {
                "method": "filesystem_dates",
                "score": 0,
                "signal": "weak",
                "message": "Dates système incohérentes (signal faible)"
            }

        return {
            "method": "dates",
            "score": 0,
            "signal": "none",
            "message": "Aucun signal de réécriture détecté"
        }

    except Exception as e:
        return {
            "method": "dates_error",
            "score": 0,
            "signal": "none",
            "message": f"Erreur analyse dates: {e}"
        }


# ---------------------------------------------------------
# Analyse complète (FRAUDE UNIQUEMENT)
# ---------------------------------------------------------

def analyze_pdf_complete(pdf_path: str) -> Dict:
    try:
        # 1️⃣ pdfresurrect (prioritaire)
        pr = analyze_with_pdfresurrect(pdf_path)
        if pr:
            return pr

        # 2️⃣ dates (fort ou faible)
        return analyze_with_dates(pdf_path)

    except PdfResurrectNotFound:
        return analyze_with_dates(pdf_path)

    except Exception as e:
        return {
            "method": "error",
            "score": 0,
            "signal": "none",
            "message": str(e)
        }
