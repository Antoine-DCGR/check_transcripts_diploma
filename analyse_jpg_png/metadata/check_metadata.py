import os
from .exif_utils import run_exiftool
from .png_metadata import analyse_png_metadata
from .jpeg_metadata import analyse_jpeg_metadata

def check_metadata(path: str) -> dict:
    """
    Point d’entrée : détecte le format (JPEG/PNG)
    et applique la bonne méthode d’analyse.
    """
    if not os.path.exists(path):
        return {"error": f"Fichier introuvable: {path}"}

    meta = run_exiftool(path)
    if "error" in meta:
        return {"error": meta["error"]}

    ftype = meta.get("FileType", "").upper()

    if ftype == "PNG":
        return analyse_png_metadata(meta)
    elif ftype in ("JPEG", "JPG"):
        return analyse_jpeg_metadata(meta)
    else:
        return {
            "file": path,
            "format": ftype,
            "verdict": "error",
            "message": "Format non supporté (uniquement PNG/JPEG)",
            "details": {}
        }
