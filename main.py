#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import pathlib

# -- Paths --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "analyse_pdf")
IMG_DIR = os.path.join(BASE_DIR, "analyse_jpg_png")

# Rendez les modules importables sans __init__.py
for p in (BASE_DIR, PDF_DIR, IMG_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

# Imports des "main" spécifiques
from detect_pdf import main as detect_pdf_main
from detect_jpg_png import main as detect_jpg_png_main


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python3 main.py <fichier>"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    input_path = sys.argv[1]
    ext = pathlib.Path(input_path).suffix.lower()

    if not os.path.exists(input_path):
        print(json.dumps({"error": f"Fichier introuvable: {input_path}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Routage par extension
    if ext == ".pdf":
        detect_pdf_main()         # appelle analyse_pdf/detect_pdf.py:main()
    elif ext in (".jpg", ".jpeg", ".png"):
        detect_jpg_png_main()     # appelle analyse_jpg_png/detect_jpg_png.py:main()
    else:
        print(json.dumps({"error": f"Type de fichier non pris en charge: {ext}"}, ensure_ascii=False, indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()
