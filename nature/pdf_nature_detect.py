#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import importlib
from typing import Literal, Tuple, Optional

def _detect_with_pymupdf(pdf_path: str) -> Optional[Tuple[int, int, float]]:
    """
    Retourne (pages_scannées, pages_total, ratio_scanné) ou None si PyMuPDF absent/erreur.
    Heuristique: une page est 'scannée' si couverture d'image >= 0.85,
    ou >= 0.70 avec <= 800 caractères texte (OCR toléré).
    """
    try:
        fitz = importlib.import_module("fitz")  # PyMuPDF
    except ModuleNotFoundError:
        return None
    except Exception:
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    n = len(doc)
    if n == 0:
        return (0, 0, 0.0)

    scanned_pages = 0
    for page in doc:
        rect = page.rect
        page_area = max(1.0, rect.width * rect.height)

        raw = page.get_text("rawdict")
        blocks = raw.get("blocks", []) if isinstance(raw, dict) else []

        image_area = 0.0
        text_chars = 0

        for b in blocks:
            btype = b.get("type", None)
            if btype == 0:  # texte
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text_chars += len(span.get("text", "") or "")
            elif btype == 1:  # image
                x0, y0, x1, y1 = b.get("bbox", (0, 0, 0, 0))
                image_area += max(0.0, (x1 - x0) * (y1 - y0))

        coverage = image_area / page_area

        page_scanned = False
        if coverage >= 0.85:
            page_scanned = True
        elif coverage >= 0.70 and text_chars <= 800:
            page_scanned = True

        if page_scanned:
            scanned_pages += 1

    ratio = scanned_pages / n
    return (scanned_pages, n, ratio)

def _detect_with_pypdf(pdf_path: str) -> Optional[Tuple[int, int]]:
    """
    Compte caractères texte extraits + nb d'images XObject (/Subtype /Image).
    Retourne (text_chars, image_count) ou None si lib absente/erreur.
    """
    PdfReader = None
    try:
        pypdf_mod = importlib.import_module("pypdf")
        PdfReader = getattr(pypdf_mod, "PdfReader", None)
    except ModuleNotFoundError:
        pass
    except Exception:
        pass

    if PdfReader is None:
        try:
            p2 = importlib.import_module("PyPDF2")
            PdfReader = getattr(p2, "PdfReader", None)
        except ModuleNotFoundError:
            return None
        except Exception:
            return None

    if PdfReader is None:
        return None

    try:
        reader = PdfReader(pdf_path)
    except Exception:
        return None

    text_chars = 0
    image_count = 0

    for page in reader.pages:
        # Texte
        try:
            txt = page.extract_text() or ""
            text_chars += len(txt.strip())
        except Exception:
            pass

        # Images (XObject /Image)
        try:
            res = page.get("/Resources")
            if res and "/XObject" in res:
                xobjs = res["/XObject"]
                for obj in xobjs.values():
                    try:
                        o = obj.get_object()
                        if o.get("/Subtype") == "/Image":
                            image_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

    return (text_chars, image_count)

def _fallback_detect_bytes(pdf_path: str) -> Tuple[int, int]:
    """
    Heuristique sans dépendance : cherche '/Font', '/Subtype /Image', 'BT' (Begin Text)
    dans le binaire (ne voit pas ce qui est compressé).
    """
    with open(pdf_path, "rb") as f:
        data = f.read()
    fonts = len(re.findall(rb'/Font\b', data))
    images = len(re.findall(rb'/Subtype\s*/Image\b', data))
    bt_ops = len(re.findall(rb'\bBT\b', data))  # 'Begin Text' non compressé
    text_chars = 10 * bt_ops if bt_ops > 0 else (50 if fonts > 0 else 0)
    return text_chars, images

def detect_pdf_nature(pdf_path: str) -> Literal["scanné", "natif"]:
    """
    Détermine si le PDF est un scan (images pleine page) ou un PDF natif (texte).
    Ordre: PyMuPDF -> pypdf/PyPDF2 -> heuristique binaire.
    """
    # 1) PyMuPDF : décision par ratio de pages scannées
    res_cov = _detect_with_pymupdf(pdf_path)
    if res_cov is not None:
        scanned_pages, total, ratio = res_cov
        if total > 0 and ratio >= 0.60:
            return "scanné"
        # Sinon on affine avec les heuristiques suivantes

    # 2) pypdf/PyPDF2
    res = _detect_with_pypdf(pdf_path)
    if res is not None:
        text_chars, image_count = res
        if text_chars >= 20:
            if image_count >= 3 and text_chars < 15:
                return "scanné"
            return "natif"
        if text_chars <= 3 and image_count >= 1:
            return "scanné"
        if image_count >= 3 and text_chars < 15:
            return "scanné"
        return "natif"

    # 3) Fallback binaire
    text_chars, image_count = _fallback_detect_bytes(pdf_path)
    if text_chars <= 3 and image_count >= 1:
        return "scanné"
    if image_count >= 3 and text_chars < 15:
        return "scanné"
    return "natif"
