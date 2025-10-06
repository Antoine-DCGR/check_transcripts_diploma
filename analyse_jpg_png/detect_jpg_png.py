# analyse_jpg_png/detect_jpg_png.py
# -*- coding: utf-8 -*-

import sys
import os

# S'assurer que les imports marchent même lancé depuis n'importe où
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# On importe le main du détecteur JPEG
from double_compression.double_compression_jpeg import main as double_jpeg_main

def main():
    """
    Point d'entrée importable par main.py (routeur).
    Délègue simplement au main() du détecteur JPEG/PNG.
    """
    # double_jpeg_main() gère lui-même argparse/sys.argv et la sortie JSON
    double_jpeg_main()

if __name__ == "__main__":
    main()
