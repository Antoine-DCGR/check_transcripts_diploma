#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilitaires communs pour l'analyse des métadonnées PDF.
"""

from typing import Dict, Any, Optional
import re

# PyPDF2 (pypdf) en priorité
try:
    from PyPDF2 import PdfReader as _PdfReader
except Exception:
    _PdfReader = None

# PyMuPDF (fitz) en complément, si disponible
try:
    import fitz  # type: ignore
except Exception:
    fitz = None


# ========================================
# BLACKLISTS - Applications interdites
# ========================================

# Blacklist pour les documents scannés
SCAN_BLACKLIST = [
    # Éditeurs d'images
    "photoshop", "adobe photoshop", "gimp", "affinity photo",
    "illustrator", "adobe illustrator", "corel", "paintshop", "inkscape",
    "paint", "paint 3d", "photopea", "pixlr", "krita", "canva", "figma",
    # Autres éditeurs suspects
    "sketch", "procreate", "clip studio paint", "sai", "artrage",'adobe acrobat 25.1 image conversion plug-in'
]

# Blacklist pour les documents natifs  
NATIVE_BLACKLIST = [
    # Éditeurs d'images (même liste)
    "photoshop", "adobe photoshop", "gimp", "affinity photo",
    "illustrator", "adobe illustrator", "corel", "paintshop", "inkscape", 
    "paint", "paint 3d", "photopea", "pixlr", "krita", "canva", "figma",
    # Applications de scan (suspectes pour un natif)
    "adobe scan", "camscanner", "microsoft lens", "office lens",
    "scanbot", "genius scan", "turboscan", "notebloc", "tap scanner",
    "scanner", "scanned", "scanné",
    # Autres éditeurs suspects
    "sketch", "procreate", "clip studio paint", "sai", "artrage",
]


def extract_metadata_pypdf(pdf_path: str) -> Dict[str, Any]:
    """Récupère les champs courants via PyPDF2/pypdf."""
    meta: Dict[str, Any] = {}
    if not _PdfReader:
        return meta
    try:
        reader = _PdfReader(pdf_path)
        info = getattr(reader, "metadata", None) or getattr(reader, "getDocumentInfo", lambda: None)()
        if info:
            for k in info:
                kk = str(k).strip("/")
                meta[kk.lower()] = str(info[k])
    except Exception:
        pass
    return meta


def extract_metadata_fitz(pdf_path: str) -> Dict[str, Any]:
    """Récupère les métadonnées via PyMuPDF si disponible."""
    meta: Dict[str, Any] = {}
    if not fitz:
        return meta
    try:
        with fitz.open(pdf_path) as doc:
            info = doc.metadata or {}
            for k, v in info.items():
                if isinstance(k, str):
                    meta[k.lower()] = str(v)
    except Exception:
        pass
    return meta


def merge_metadata(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Fusion simple, sans écraser les clés déjà présentes dans a (priorité à PyPDF2)."""
    out = dict(a)
    for k, v in b.items():
        if k not in out or not out[k]:
            out[k] = v
    return out


def lower_or_empty(x: Optional[str]) -> str:
    """Convertit en minuscules ou retourne une chaîne vide."""
    return (x or "").strip().lower()


def is_in_blacklist(creator: str, producer: str, blacklist: list) -> tuple[bool, str]:
    """
    Vérifie si Creator ou Producer contient un élément de la blacklist.
    Retourne (found, detected_item).
    """
    # Combiner creator et producer pour la recherche
    combined_text = f"{creator} {producer}".lower()
    
    for blacklisted_item in blacklist:
        if blacklisted_item.lower() in combined_text:
            return True, blacklisted_item
    
    return False, ""


def extract_all_metadata(pdf_path: str) -> Dict[str, str]:
    """Extrait toutes les métadonnées du PDF et retourne les champs principaux."""
    # Extraction via les deux backends
    meta_pypdf = extract_metadata_pypdf(pdf_path)
    meta_fitz = extract_metadata_fitz(pdf_path)
    meta_all = merge_metadata(meta_pypdf, meta_fitz)

    # Normalisation des champs principaux
    return {
        "producer": lower_or_empty(meta_all.get("producer")),
        "creator": lower_or_empty(meta_all.get("creator")),
        "application": lower_or_empty(meta_all.get("application") or meta_all.get("app")),
        "title": lower_or_empty(meta_all.get("title")),
        "author": lower_or_empty(meta_all.get("author")),
        "moddate": lower_or_empty(meta_all.get("moddate") or meta_all.get("modified") or meta_all.get("mod_date")),
    }


def create_result(ok: bool, message: str, verdict: str, pdf_path: str, 
                  confidence: str = "medium") -> Dict[str, Any]:
    """Crée un dictionnaire de résultat standardisé."""
    return {
        "ok": ok,
        "message": message,
        "verdict": verdict,
        "file": pdf_path,
        "confidence": confidence,
    }