#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
detect_jpg_png.py

Analyse JPEG/PNG en pipeline :
  1) Métadonnées (check_metadata)
  2) Copy-move (désactivé pour l’instant)
  3) Double compression JPEG (detect_double_compression)

Court-circuits :
  - Si métadonnées = falsified → on n'exécute PAS copy-move ni double-compression
  - Si copy-move = falsified (cluster net) → on n'exécute PAS la double-compression

Sortie JSON COMPACTE par fichier (pas de "details") :
  - ok, verdict, message, file
  - metadata: {verdict, message}
  - copy_move: {verdict, message}
  - double_compressions: {verdict, message}
  - overall: {verdict, message}
"""

import sys
import json
from pathlib import Path

# ✅ nouvelle importation (architecture mise à jour)
from metadata.check_metadata import check_metadata
from double_compression.double_compression_jpeg import detect_double_compression


# ----------------------------
# Helpers
# ----------------------------

def _is_meta_absence_benign(meta_res: dict, ext: str) -> bool:
    """
    Certains PNG n'ont pas/peu de métadonnées → ne pas traiter cela comme une 'erreur' système.
    On laisse éventuellement 'suspect' côté métadonnées, mais on continue la pipeline.
    """
    if ext == ".png" and not meta_res.get("ok", True):
        msg = str(meta_res.get("message", "")).lower()
        if "métadonnées absentes" in msg or "metadonnees absentes" in msg or "metadata" in msg:
            return True
    return False


def _blk(verdict: str, message: str) -> dict:
    """Bloc compact méthode."""
    return {"verdict": verdict, "message": message}


# ----------------------------
# Main
# ----------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 detect_jpg_png.py <image1> [<image2> ...]")
        sys.exit(1)

    outputs = []

    for path in sys.argv[1:]:
        p = Path(path)
        ext = p.suffix.lower()

        try:
            # --- 1) Métadonnées ---
            meta_res = check_metadata(path)
            meta_verd = str(meta_res.get("verdict", "")).lower() or "error"
            meta_msg = meta_res.get("message", "") or "Analyse métadonnées : résultat indisponible"

            # PNG sans métadonnées : neutraliser l’état 'ok' pour éviter un 'error' global
            if _is_meta_absence_benign(meta_res, ext):
                meta_res["ok"] = True

            # Préparation des blocs
            metadata_block = _blk(meta_verd, meta_msg)
            copy_move_block = _blk("skipped", "En attente (pipeline)")
            dc_block = _blk("skipped", "En attente (pipeline)")

            # Agrégation globale
            overall_verdict = "valid"
            overall_reason = "Aucune anomalie détectée"

            # --- Court-circuit si métadonnées = falsified ---
            if meta_verd == "falsified":
                copy_move_block = _blk("skipped", "Métadonnées concluent déjà — copy-move non exécuté")
                if ext == ".png":
                    dc_block = _blk("skipped", "Format PNG — double compression non applicable")
                else:
                    dc_block = _blk("skipped", "Métadonnées concluent déjà — double compression non exécutée")
                overall_verdict = "falsified"
                overall_reason = meta_msg or "Application/IA/scan détecté"

            else:
                # --- 3) Double compression (JPEG uniquement) ---
                if ext in {".jpg", ".jpeg"}:
                    dc_verdict, dc_reasons = detect_double_compression(path)
                    dc_msg = (dc_reasons[0] if isinstance(dc_reasons, list) and dc_reasons
                              else "Analyse double compression terminée")
                    dc_block = _blk(dc_verdict, dc_msg)
                    if dc_verdict == "falsified":
                        overall_verdict = "falsified"
                        overall_reason = f"Double compression JPEG détectée ({dc_msg})"
                else:
                    dc_block = _blk("skipped", "Format PNG — double compression non applicable")

            # --- Gestion erreurs métadonnées ---
            if not meta_res.get("ok", True) and overall_verdict == "valid":
                overall_verdict = "error"
                overall_reason = meta_msg or "Erreur inconnue"

            # --- Ajout du résultat global ---
            outputs.append({
                "ok": overall_verdict == "valid",
                "verdict": overall_verdict,
                "message": overall_reason,
                "overall": {
                    "verdict": overall_verdict,
                    "reason": overall_reason,
                },
                "file": path,
                "metadata": metadata_block,
                "copy_move": copy_move_block,
                "double_compressions": dc_block
            })

        except Exception as e:
            outputs.append({
                "ok": False,
                "verdict": "error",
                "message": f"Erreur lors de l'analyse de {path}: {e}",
                "overall": {
                    "verdict": "error",
                    "reason": str(e),
                },
                "file": path,
                "metadata": _blk("error", "Échec analyse métadonnées"),
                "copy_move": _blk("skipped", "Erreur amont — copy-move non exécuté"),
                "double_compressions": _blk("skipped", "Erreur amont — double compression non exécutée")
            })

    print(json.dumps(outputs, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
