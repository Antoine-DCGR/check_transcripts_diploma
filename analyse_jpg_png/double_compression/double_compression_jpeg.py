#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
double_compression_jpeg.py

Sortie JSON:
{
  "verdict": "valid"|"falsified",
  "reasons": ["..."]
}

Règles:
- Détection contenu (FFT "peigne" multi-coeffs) DURCIE pour limiter les FP.
- Heuristique DQT (quantization tables) conservée.
- AUCUN verdict forcé : la détection est purement basée sur les données de l'image.

Dépendances: pillow, numpy, scipy, opencv-python
"""

import sys, json, os
import numpy as np
from scipy import fftpack as fftp

try:
    import cv2
except Exception:
    cv2 = None

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


# ---------- I/O ----------
def load_image_any(path: str):
    if cv2 is None:
        if not PIL_OK:
            raise RuntimeError("Installe opencv-python ou Pillow")
        im = Image.open(path).convert("RGB")
        arr = np.asarray(im)
        return arr[:, :, ::-1].copy()  # RGB->BGR
    return cv2.imread(path)


def extract_jpeg_quant_tables(path: str):
    if not PIL_OK:
        return None
    try:
        im = Image.open(path)
        return getattr(im, "quantization", None)
    except Exception:
        return None


# ---------- FFT / DCT ----------
def blockify_y_channel(img_bgr):
    h, w = img_bgr.shape[:2]
    ph = (h + 7) // 8 * 8
    pw = (w + 7) // 8 * 8
    canvas = np.zeros((ph, pw, 3), np.uint8)
    canvas[:h, :w] = img_bgr
    y = cv2.cvtColor(canvas, cv2.COLOR_BGR2YCrCb)[:, :, 0]
    H, W = y.shape
    return y.reshape(H // 8, 8, -1, 8).swapaxes(1, 2).reshape(-1, 8, 8)


def dct_blocks(Y):
    return np.array([cv2.dct(b.astype(np.float32)) for b in Y], dtype=np.float32)


def coeff_histogram(coeffs):
    vals = np.rint(coeffs - np.mean(coeffs)).astype(np.int32)
    vmin, vmax = int(vals.min()), int(vals.max())
    if vmin == vmax:
        return None
    bins = np.arange(vmin, vmax + 1)
    hist, _ = np.histogram(vals, bins=np.append(bins, vmax + 1), density=True)
    return hist


def fft_peigne_score(hist):
    if hist is None or len(hist) < 8:
        return 0, 0.0
    Z = np.abs(fftp.fft(hist))
    Z[0] = 0.0
    Zc = np.roll(Z, len(Z) // 2)
    med = float(np.median(Zc))
    mad = float(np.median(np.abs(Zc - med))) + 1e-9
    th = med + 6.0 * mad
    peaks = [i for i in range(1, len(Zc) - 1)
             if Zc[i] > th and Zc[i] > Zc[i - 1] and Zc[i] > Zc[i + 1]]
    crest = float((Zc.max() + 1e-9) / (med + 1e-9))
    return len(peaks), crest


# ---------- Core ----------
def detect_double_compression(image_path: str):
    reasons = []

    # Chargement image
    img = load_image_any(image_path)
    if img is None:
        raise ValueError("Image non lisible")

    # Heuristique DQT
    qtables = extract_jpeg_quant_tables(image_path)
    dqt_flag = False
    if qtables:
        try:
            all_q = []
            for _, arr in qtables.items():
                all_q.extend(arr)
            all_q = np.array(all_q, dtype=np.float32)
            q_med = float(np.median(all_q))
            q_min = float(np.min(all_q))
            q_max = float(np.max(all_q))
            if (q_min <= 1 and q_max >= 80) or (q_med >= 40):
                dqt_flag = True
                reasons.append(f"QuantizationTables suspectes: min={int(q_min)}, med={int(q_med)}, max={int(q_max)}")
        except Exception:
            pass

    verdict = "valid"

    # Détection FFT/DCT
    if cv2 is not None:
        Y = blockify_y_channel(img)
        D = dct_blocks(Y)
        uv_list = [(1,0), (0,1), (2,0), (0,2), (1,1), (2,1), (1,2), (3,0), (0,3)]
        strong_coeffs = 0
        crests = []
        for (u, v) in uv_list:
            hist = coeff_histogram(D[:, u, v])
            pc, cr = fft_peigne_score(hist)
            if pc >= 8 and cr >= 6.0:
                strong_coeffs += 1
            crests.append(cr if cr > 0 else 0.0)
        median_crest = float(np.median(crests)) if crests else 0.0

        if strong_coeffs >= 4 and median_crest >= 5.5:
            verdict = "falsified"
            reasons.insert(0, f"Vote multi-coeffs: {strong_coeffs} coeffs forts; median_crest={median_crest:.2f}")
        elif dqt_flag:
            verdict = "falsified"
    else:
        # sans OpenCV, fallback sur DQT
        verdict = "falsified" if dqt_flag else "valid"

    return verdict, reasons
