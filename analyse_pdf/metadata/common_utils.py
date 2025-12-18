#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilitaires communs pour l'analyse des métadonnées PDF.
"""

from typing import Dict, Any, Optional
import re
import unicodedata

# PyPDF2 (pypdf) en priorité
try:
    from PyPDF2 import PdfReader as _PdfReader
except Exception:
    _PdfReader = None

# PyMuPDF (fitz) en complément
try:
    import fitz  # type: ignore
except Exception:
    fitz = None


# ========================================
# BLACKLISTS
# ========================================

SCAN_BLACKLIST = [
    "photoshop", "adobe photoshop", "gimp", "affinity photo",
    "illustrator", "adobe illustrator", "corel", "inkscape",
    "paint", "photopea", "pixlr", "krita", "canva", "figma","reportlab","ilovepdf"
]

NATIVE_BLACKLIST = [
    "photoshop", "adobe photoshop", "gimp", "illustrator",
    "canva", "figma", "adobe scan", "camscanner",
]

WEB_TO_PDF_BLACKLIST = [
    "chrome", "chromium", "headlesschrome",
    "wkhtmltopdf", "dompdf", "weasyprint",
    "puppeteer", "playwright", "electron",
]


# ========================================
# METADATA EXTRACTION
# ========================================

def extract_metadata_pypdf(pdf_path: str) -> Dict[str, Any]:
    meta = {}
    if not _PdfReader:
        return meta
    try:
        reader = _PdfReader(pdf_path)
        info = reader.metadata
        if info:
            for k, v in info.items():
                meta[str(k).strip("/").lower()] = str(v)
    except Exception:
        pass
    return meta


def extract_metadata_fitz(pdf_path: str) -> Dict[str, Any]:
    meta = {}
    if not fitz:
        return meta
    try:
        with fitz.open(pdf_path) as doc:
            for k, v in (doc.metadata or {}).items():
                meta[k.lower()] = str(v)
    except Exception:
        pass
    return meta


def extract_all_metadata(pdf_path: str) -> Dict[str, str]:
    meta = extract_metadata_pypdf(pdf_path)
    meta = {**extract_metadata_fitz(pdf_path), **meta}

    return {
        "creator": meta.get("creator", "").lower(),
        "producer": meta.get("producer", "").lower(),
    }


# ========================================
# HELPERS
# ========================================

def normalize_string(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return value.strip()


def is_in_blacklist(creator: str, producer: str, blacklist: list) -> tuple[bool, str]:
    combined = f"{creator} {producer}"
    for item in blacklist:
        if item in combined:
            return True, item
    return False, ""


def create_result(
    verdict: str,
    score: int,
    message: str,
    pdf_path: str,
    confidence: str = "medium",
) -> Dict[str, Any]:
    return {
        "verdict": verdict,
        "score": score,
        "message": message,
        "file": pdf_path,
        "confidence": confidence,
    }
