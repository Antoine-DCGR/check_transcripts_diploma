#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse de révisions PDF via le CLI 'pdfresurrect'.
- Calcule le nombre de réécritures = (versions - 1), borné à >= 0
- Retourne: (rewrites:int, ok:bool, message:str) où ok = (rewrites <= 1)
"""

import re
import shutil
import subprocess
from typing import Tuple

class PdfResurrectNotFound(RuntimeError):
    pass

def _get_versions_via_pdfresurrect(pdf_path: str) -> int:
    """
    Appelle 'pdfresurrect -q <fichier>' et extrait le nombre de versions.
    Format typique: '<nom_fichier>: <N>'
    """
    if not shutil.which("pdfresurrect"):
        raise PdfResurrectNotFound(
            "pdfresurrect introuvable dans le PATH. Installe-le (ex: sudo apt-get install pdfresurrect)."
        )

    out = subprocess.check_output(
        ["pdfresurrect", "-q", pdf_path],
        stderr=subprocess.STDOUT,
        text=True
    ).strip()

    # Cherche le dernier entier sur la ligne (robuste au nom de fichier)
    m = re.search(r"(\d+)\s*$", out)
    versions = int(m.group(1)) if m else 1
    return max(1, versions)

def analyze_pdf_with_cli(pdf_path: str) -> dict:
    """
    :param pdf_path: chemin du PDF
    :return: Dictionnaire avec les clés 'ok', 'message', 'rewrites'
    """
    try:
        versions = _get_versions_via_pdfresurrect(pdf_path)
        rewrites = max(0, versions - 1)
        ok = rewrites == 0
        
        return {
            "ok": ok,
            "rewrites": rewrites,
            "message": "PDF non falsifié (0 réécriture détectée)." if ok else f"{rewrites} réécritures détectées."
        }
    except Exception as e:
        return {
            "ok": False,
            "rewrites": 0,
            "message": f"Erreur lors de l'analyse des révisions: {str(e)}"
        }