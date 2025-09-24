#!/usr/bin/env python3
import sys
import json
import pdfrw

if len(sys.argv) != 2:
    print("Usage: python pdf_meta.py <fichier.pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
pdf = pdfrw.PdfReader(pdf_path)

# pdf.Info contient les métadonnées brutes
meta = {}
if pdf.Info:
    for key, value in pdf.Info.items():
        k = key.strip("/")  # ex: /Author -> Author
        v = str(value).strip("()")  # nettoie les ()
        meta[k] = v

print(json.dumps(meta, indent=2, ensure_ascii=False))
