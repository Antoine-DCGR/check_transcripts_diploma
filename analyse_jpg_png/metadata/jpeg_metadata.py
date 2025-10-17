#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analyse_jpeg_metadata.py

🎯 Stratégie A : "Valide par défaut"
Le document est considéré comme VALIDE sauf si des éléments explicites indiquent une falsification.

Objectif : réduire au maximum les faux négatifs (ne jamais rejeter un JPEG propre).

✅ VALID si :
  - Aucun logiciel de retouche connu
  - Sous-échantillonnage standard (4:2:0 ou non précisé)
  - DPI basiques ou absents mais cohérents
  - Dimensions suffisantes (≥ 200px)
❌ FALSIFIED uniquement si :
  - Logiciel de retouche ou IA détecté
  - Sous-échantillonnage 4:4:4
  - DPI incohérents + dimensions trop faibles + absence totale d’infos physiques
"""

def analyse_jpeg_metadata(meta: dict) -> dict:
    file = meta.get("SourceFile", "")

    # ---- Helpers ----
    def to_float(v):
        try:
            if isinstance(v, (int, float)):
                return float(v)
            return float(str(v).split()[0])
        except Exception:
            return 0.0

    def to_int(v):
        try:
            return int(float(v))
        except Exception:
            return 0

    # ---- Extraction ----
    res_unit = str(meta.get("ResolutionUnit", "")).lower()
    xres, yres = to_float(meta.get("XResolution", 0)), to_float(meta.get("YResolution", 0))
    width, height = to_int(meta.get("ImageWidth", 0)), to_int(meta.get("ImageHeight", 0))
    subsampling = str(meta.get("YCbCrSubSampling", "")).replace(" ", "")
    compression = str(meta.get("Compression", "")).lower()
    software = (str(meta.get("Software", "")) + " " + str(meta.get("Application", ""))).lower()

    # ---- Flags ----
    suspicious_sw = any(s in software for s in [
        "adobe", "photoshop", "gimp", "canva", "affinity", "corel", "ai", "dall", "remini"
    ])
    is_444 = "4:4:4" in subsampling
    is_420 = "4:2:0" in subsampling
    dpi_scan = (res_unit == "inches" and xres >= 300 and yres >= 300)
    dpi_absent = (xres <= 0 or yres <= 0)  # tolère DPI=1
    has_make = "Make" in meta and "Model" in meta
    has_exif = any(k in meta for k in ["ISO", "ExposureTime", "FNumber", "DateTimeOriginal"])
    big_enough = min(width, height) >= 200

    # ---- Cas explicite : Logiciel ou IA ----
    if suspicious_sw:
        return {
            "file": file,
            "format": "JPEG",
            "verdict": "falsified",
            "message": "Export Photoshop / GIMP / IA détecté",
            "details": {
                "software": software,
                "subsampling": subsampling,
                "dpi": (xres, yres, res_unit),
                "reasons": ["Logiciel suspect détecté"],
                "raw_meta": meta
            }
        }

    # ---- Cas explicite : Sous-échantillonnage anormal ----
    if is_444:
        return {
            "file": file,
            "format": "JPEG",
            "verdict": "falsified",
            "message": "Sous-échantillonnage 4:4:4 (export manuel ou retouche probable)",
            "details": {
                "subsampling": subsampling,
                "dpi": (xres, yres, res_unit),
                "reasons": ["Structure 4:4:4 incompatible avec un export naturel"],
                "raw_meta": meta
            }
        }

    # ---- Cas explicite : Métadonnées incohérentes graves ----
    if (dpi_absent and not big_enough and not has_make and not has_exif):
        return {
            "file": file,
            "format": "JPEG",
            "verdict": "falsified",
            "message": "Métadonnées incohérentes ou incomplètes (probable recompression artificielle)",
            "details": {
                "dpi": (xres, yres, res_unit),
                "dimensions": (width, height),
                "reasons": [
                    "Aucune information Exif ou physique",
                    "Résolution absente ou invalide",
                    "Image trop petite pour être un document original"
                ],
                "raw_meta": meta
            }
        }

    # ---- Cas neutre / scan / photo ----
    if dpi_scan:
        message = "Document scanné (300 DPI ou plus)"
    elif has_make or has_exif:
        message = "Photo issue d’un appareil réel (smartphone ou caméra)"
    else:
        message = "JPEG standard sans anomalie détectée"

    return {
        "file": file,
        "format": "JPEG",
        "verdict": "valid",
        "message": message,
        "details": {
            "dpi": (xres, yres, res_unit),
            "dimensions": (width, height),
            "subsampling": subsampling or "non spécifié",
            "compression": compression,
            "software": software,
            "reasons": [
                "Aucun logiciel d’édition détecté",
                "Sous-échantillonnage standard ou non précisé",
                "Métadonnées minimales mais cohérentes"
            ],
            "raw_meta": meta
        }
    }
