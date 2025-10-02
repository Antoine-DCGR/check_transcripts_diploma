# main.py
# -*- coding: utf-8 -*-

import argparse, json, sys
from double_compression_jpeg import detect_double_compression

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Détection double JPEG (robuste) – JSON")
    ap.add_argument("image", help="Chemin de l'image à tester")
    args = ap.parse_args()

    try:
        res = detect_double_compression(args.image)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
