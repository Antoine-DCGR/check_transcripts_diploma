# -*- coding: utf-8 -*-
"""
IA Detector - Version SCORING
Détection IA OCR / image / structure (preuves techniques)
NE DÉCIDE PAS LE VERDICT FINAL
Retourne un score + message explicite
"""

import fitz
import pytesseract
import numpy as np
from PIL import Image


def extract_ocr(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        pix = page.get_pixmap(dpi=180)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        try:
            page_text = pytesseract.image_to_string(img)
        except Exception:
            page_text = ""
        text += page_text + "\n"
    return text


def extract_fonts(pdf_path: str):
    doc = fitz.open(pdf_path)
    fonts = set()
    for page in doc:
        try:
            for f in page.get_fonts():
                fonts.add(f[3])
        except Exception:
            pass
    return list(fonts)


def analyze_pdf_structure(pdf_path: str) -> dict:
    """
    Retour :
    {
      verdict: valid|suspect|falsified (indicatif)
      score: int
      message: str
      details: {}
    }
    """

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {
            "verdict": "unknown",
            "score": 0,
            "message": f"Erreur ouverture PDF: {e}",
            "details": {}
        }

    # ----------------------------
    # STRUCTURE
    # ----------------------------
    object_count = max(len(doc), doc.xref_length())
    fonts = extract_fonts(pdf_path)
    font_count = len(fonts)

    # ----------------------------
    # OCR ANALYSE
    # ----------------------------
    ocr_text = extract_ocr(pdf_path)
    words = [w for w in ocr_text.split() if len(w) <= 20]

    if len(words) > 25:
        std_len = float(np.std([len(w) for w in words]))
    else:
        std_len = 5.0  # neutre

    ocr_ia = std_len < 1.0

    # ----------------------------
    # IMAGE IA SIMPLE HEURISTIQUE
    # ----------------------------
    image_ia = (object_count < 8 and font_count == 0 and len(words) == 0)

    # ----------------------------
    # STRUCTURE IA "JUSTE MILIEU"
    # ----------------------------
    structure_mid = (object_count <= 10 and font_count == 0)

    score = 0
    reasons = []

    if ocr_ia:
        score += 3
        reasons.append("OCR très homogène (signal IA fort)")

    if image_ia:
        score += 3
        reasons.append("PDF image-only ultra-minimaliste (signal IA image)")

    if structure_mid and not ocr_ia:
        score += 0
        reasons.append("Structure PDF anormalement simple (signal faible)")

    if score >= 3:
        verdict = "falsified"
    elif score == 2:
        verdict = "suspect"
    else:
        verdict = "valid"

    return {
        "verdict": verdict,
        "score": score,
        "message": " / ".join(reasons) if reasons else "Aucun signal IA détecté.",
        "details": {
            "object_count": object_count,
            "font_count": font_count,
            "ocr_std_len": std_len,
            "flags": {
                "ocr_ia": ocr_ia,
                "image_ia": image_ia,
                "structure_mid": structure_mid
            }
        }
    }
