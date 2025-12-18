#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Détecteur de documents re-scannés (scan -> impression -> re-scan)

- Calcul de scores qualité / artefacts à partir des images
- Règles par intervalles (core / suspect / none)
- SCORING STRICTEMENT ALIGNÉ SUR LE VERDICT (0 / 1 / 2)
- AUCUN score fantôme
- Compatible detect_pdf.py via analyze_pdf()
"""

import io
import cv2
import fitz
import numpy as np
from PIL import Image
from skimage import measure


# -----------------------------
# INTERVALLES (INCHANGÉS)
# -----------------------------
QUALITY_CORE_MIN, QUALITY_CORE_MAX = 25.0, 42.5
ART_CORE_MIN,    ART_CORE_MAX     = 66.0, 75.0

QUALITY_SUSPECT_MAX = 56.0
ART_SUSPECT_MAX     = 78.0


class RescanDetector:
    def __init__(self):
        pass

    # =================================================
    # EXTRACTION IMAGES
    # =================================================
    def extract_pdf_images(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        images = []

        for page in doc:
            for img in page.get_images():
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                try:
                    if pix.n < 5 and pix.width > 100 and pix.height > 100:
                        img_data = pix.pil_tobytes(format="PNG")
                        pil_img = Image.open(io.BytesIO(img_data))
                        images.append(np.array(pil_img))
                finally:
                    pix = None

        doc.close()
        return images

    # =================================================
    # MÉTRIQUES QUALITÉ
    # =================================================
    def calculate_image_quality_metrics(self, image: np.ndarray):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image

        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist[hist > 0]
        entropy = -np.sum((hist / np.sum(hist)) * np.log2(hist / np.sum(hist)))

        noise_estimate = estimate_noise(gray)
        rms_contrast = np.sqrt(np.mean((gray - np.mean(gray)) ** 2))

        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1)

        hf = np.mean(
            magnitude_spectrum[
                magnitude_spectrum.shape[0] // 4: 3 * magnitude_spectrum.shape[0] // 4,
                magnitude_spectrum.shape[1] // 4: 3 * magnitude_spectrum.shape[1] // 4
            ]
        )

        return {
            "laplacian_variance": float(lap_var),
            "entropy": float(entropy),
            "noise_estimate": float(noise_estimate),
            "rms_contrast": float(rms_contrast),
            "high_frequency_content": float(hf),
        }

    # =================================================
    # MÉTRIQUES ARTEFACTS
    # =================================================
    def detect_printing_artifacts(self, image: np.ndarray):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image

        artifacts = {}

        kernel = np.ones((3, 3), np.uint8)
        closing = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        artifacts["halftone_score"] = float(
            np.mean(np.abs(gray.astype(float) - closing.astype(float)))
        )

        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        edge_irreg = 0.0
        if contours:
            for c in contours:
                if len(c) > 10:
                    perim = cv2.arcLength(c, True)
                    hull = cv2.convexHull(c)
                    hull_perim = cv2.arcLength(hull, True)
                    if hull_perim > 0:
                        edge_irreg += perim / hull_perim

        artifacts["edge_irregularity"] = float(edge_irreg / len(contours)) if contours else 0.0
        artifacts["compression_artifacts"] = float(self.detect_compression_artifacts(gray))
        artifacts["grid_pattern_score"] = float(self.detect_grid_patterns(gray))

        return artifacts

    def detect_compression_artifacts(self, image: np.ndarray) -> float:
        h, w = image.shape
        dct_coeffs = []

        for i in range(0, h - 7, 8):
            for j in range(0, w - 7, 8):
                block = image[i:i + 8, j:j + 8].astype(float)
                dct_block = cv2.dct(block)
                dct_coeffs.extend(dct_block.flatten())

        dct_coeffs = np.array(dct_coeffs)
        hist, _ = np.histogram(dct_coeffs, bins=50, range=(-100, 100))

        return float(np.std(hist) / (np.mean(hist) + 1e-8))

    def detect_grid_patterns(self, image: np.ndarray) -> float:
        f_transform = np.fft.fft2(image)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)

        h, w = magnitude_spectrum.shape
        ch, cw = h // 2, w // 2
        mid = magnitude_spectrum[ch - h // 4: ch + h // 4,
                                 cw - w // 4: cw + w // 4]

        peaks = measure.label(mid > np.percentile(mid, 95))
        return float((len(np.unique(peaks)) - 1) / mid.size)

    # =================================================
    # SCORE QUALITÉ / ARTEFACTS
    # =================================================
    def calculate_quality_score(self, m: dict) -> float:
        score = 0.0
        score += min(m["laplacian_variance"] / 1000, 1.0) * 25
        score += (m["entropy"] / 8.0) * 20
        score += min(m["rms_contrast"] / 100, 1.0) * 20
        score += max(0.0, 1.0 - m["noise_estimate"] / 50.0) * 20
        score += min(m["high_frequency_content"] / 1000, 1.0) * 15
        return score

    def calculate_artifact_score(self, a: dict) -> float:
        score = 0.0
        score += min(a["halftone_score"] / 10, 1.0) * 30
        score += min(a["edge_irregularity"], 1.0) * 25
        score += min(a["compression_artifacts"] / 5, 1.0) * 25
        score += min(a["grid_pattern_score"] * 1000, 1.0) * 20
        return score

    # =================================================
    # API PIPELINE
    # =================================================
    def analyze_pdf(self, pdf_path: str) -> dict:
        images = self.extract_pdf_images(pdf_path)

        if not images:
            return {
                "verdict": "none",
                "score": 0,
                "signal": "none",
                "message": "Aucune image trouvée dans le PDF",
            }

        tot_q, tot_a = 0.0, 0.0

        for im in images:
            q_metrics = self.calculate_image_quality_metrics(im)
            a_metrics = self.detect_printing_artifacts(im)
            tot_q += self.calculate_quality_score(q_metrics)
            tot_a += self.calculate_artifact_score(a_metrics)

        avg_q = tot_q / len(images)
        avg_a = tot_a / len(images)

        return build_rescan_json(avg_q, avg_a)


# =================================================
# HELPERS
# =================================================
def estimate_noise(image: np.ndarray) -> float:
    grad_x = np.abs(np.diff(image, axis=1))
    grad_y = np.abs(np.diff(image, axis=0))
    return float((np.median(grad_x) + np.median(grad_y)) / 2.0)


def build_rescan_json(qualite: float, artefact: float) -> dict:
    in_q_core = QUALITY_CORE_MIN <= qualite <= QUALITY_CORE_MAX
    in_a_core = ART_CORE_MIN     <= artefact <= ART_CORE_MAX

    # -----------------------------
    # LOGIQUE MÉTIER (INCHANGÉE)
    # -----------------------------
    if in_q_core and in_a_core:
        level = "core"
        score = 3
        signal = "strong"
        message = "re-scan détecté (signal fort)"

    elif in_q_core ^ in_a_core:
        level = "partial"
        score = 1
        signal = "weak"
        message = "indice partiel de re-scan (qualité ou artefacts)"

    else:
        level = "none"
        score = 0
        signal = "none"
        message = "aucun indice technique de re-scan"

    return {
        "verdict": level,
        "score": score,
        "signal": signal,
        "message": message,
        "details": {
            "avg_quality": round(qualite, 2),
            "avg_artifact": round(artefact, 2),
        },
    }
