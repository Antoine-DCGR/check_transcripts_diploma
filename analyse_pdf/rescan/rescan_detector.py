#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Détecteur de documents re-scannés (scan -> impression -> re-scan)
- Calcule des scores "qualité" et "artefacts" à partir des images du PDF
- Applique une règle par INTERVALLES (core / suspect / none)
- Ne contient PAS de main() (utilisé par main.py)

Règle:
- core (re-scan clair) si Qualité ∈ [25, 42] ET Artefacts ∈ [65, 75]
- suspect si:
    * Artefacts ∈ [65, 75] ET Qualité ∈ (42, 56)
  OU* Qualité ∈ [25, 42] ET Artefacts ∈ (75, 78]
  OU* Qualité ∈ (42, 43] ET Artefacts ∈ [65, 75]
- none sinon

Mapping métier (retourné dans build_rescan_json):
- level="core"    -> verdict=True,  status="invalid" (falsifié)
- level="suspect" -> verdict=True,  status="invalid" (suspect; on NE hard-fail PAS dans main)
- level="none"    -> verdict=False, status="valid"
"""

import io
import cv2
import fitz
import numpy as np
from PIL import Image
from skimage import measure

# -----------------------------
# INTERVALLES (modifiables)
# -----------------------------
QUALITY_CORE_MIN, QUALITY_CORE_MAX = 25.0, 42.5
ART_CORE_MIN,    ART_CORE_MAX     = 65.0, 75.0

# Zones tampon pour "suspect"
QUALITY_SUSPECT_MAX = 56.0   # borne sup pour "artefacts core" & qualité un peu élevée (inclut Christian 55.3, exclut bulletins ~58-60)
ART_SUSPECT_MAX     = 78.0   # artefacts un peu au-dessus de la zone core


class RescanDetector:
    def __init__(self):
        self.results = {}

    def extract_pdf_images(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        images = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
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

    def analyze_metadata(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        rescan_indicators = {'creator_scanner_apps': ['Scanner', 'CamScanner', 'Adobe Scan', 'HP Scan']}
        creator = (metadata.get('creator') or '').lower()
        producer = (metadata.get('producer') or '').lower()
        scanner_detected = any(app.lower() in creator or app.lower() in producer
                               for app in rescan_indicators['creator_scanner_apps'])
        return {
            'metadata': metadata,
            'scanner_app_detected': scanner_detected,
            'creation_date': metadata.get('creationDate'),
            'modification_date': metadata.get('modDate')
        }

    def calculate_image_quality_metrics(self, image: np.ndarray):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1)

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist[hist > 0]
        entropy = -np.sum((hist / np.sum(hist)) * np.log2(hist / np.sum(hist)))

        noise_estimate = estimate_noise(gray)
        rms_contrast = np.sqrt(np.mean((gray - np.mean(gray)) ** 2))

        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(gx ** 2 + gy ** 2)

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
            "mean_gradient_magnitude": float(np.mean(grad_mag)),
            "high_frequency_content": float(hf),
        }

    def detect_printing_artifacts(self, image: np.ndarray):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        artifacts = {}
        kernel = np.ones((3, 3), np.uint8)
        closing = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        artifacts['halftone_score'] = float(np.mean(np.abs(gray.astype(float) - closing.astype(float))))

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
        artifacts['edge_irregularity'] = float(edge_irreg / len(contours)) if contours else 0.0

        artifacts['compression_artifacts'] = float(self.detect_compression_artifacts(gray))
        artifacts['grid_pattern_score'] = float(self.detect_grid_patterns(gray))
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
        mid = magnitude_spectrum[ch - h // 4: ch + h // 4, cw - w // 4: cw + w // 4]
        peaks = measure.label(mid > np.percentile(mid, 95))
        num_peaks = len(np.unique(peaks)) - 1
        return float(num_peaks / (mid.shape[0] * mid.shape[1]))

    def analyze_pdf(self, pdf_path: str):
        _ = self.analyze_metadata(pdf_path)  # pas utilisé pour la décision
        images = self.extract_pdf_images(pdf_path)
        if not images:
            return {"error": "Aucune image trouvée dans le PDF"}

        tot_q, tot_a = 0.0, 0.0
        for im in images:
            q_metrics = self.calculate_image_quality_metrics(im)
            a_metrics = self.detect_printing_artifacts(im)
            tot_q += self.calculate_quality_score(q_metrics)
            tot_a += self.calculate_artifact_score(a_metrics)

        avg_q = tot_q / len(images)
        avg_a = tot_a / len(images)
        return {"file_path": pdf_path, "avg_quality_score": float(avg_q), "avg_artifact_score": float(avg_a)}

    def calculate_quality_score(self, m: dict) -> float:
        score = 0.0
        score += min(m['laplacian_variance'] / 1000, 1.0) * 25
        score += (m['entropy'] / 8.0) * 20
        score += min(m['rms_contrast'] / 100, 1.0) * 20
        score += max(0, 1 - m['noise_estimate'] / 50) * 20
        score += min(m['high_frequency_content'] / 1000, 1.0) * 15
        return float(score)

    def calculate_artifact_score(self, a: dict) -> float:
        score = 0.0
        score += min(a['halftone_score'] / 10, 1.0) * 30
        score += min(a['edge_irregularity'], 1.0) * 25
        score += min(a['compression_artifacts'] / 5, 1.0) * 25
        score += min(a['grid_pattern_score'] * 1000, 1.0) * 20
        return float(score)


def estimate_noise(image: np.ndarray) -> float:
    grad_x = np.abs(np.diff(image, axis=1))
    grad_y = np.abs(np.diff(image, axis=0))
    return float((np.median(grad_x) + np.median(grad_y)) / 2.0)


def build_rescan_json(file_path: str, qualite: float, artefact: float) -> dict:
    """
    Renvoie verdict booléen + level ("core"/"suspect"/"none") et status.
    """
    in_q_core  = (QUALITY_CORE_MIN <= qualite <= QUALITY_CORE_MAX)
    in_a_core  = (ART_CORE_MIN     <= artefact <= ART_CORE_MAX)

    # core
    if in_q_core and in_a_core:
        level = "core"
        verdict = True
        status  = "invalid"
        message = (f"qualité {qualite:.1f} dans [{QUALITY_CORE_MIN:.0f},{QUALITY_CORE_MAX:.0f}] ET "
                   f"artefacts {artefact:.1f} dans [{ART_CORE_MIN:.0f},{ART_CORE_MAX:.0f}] : "
                   "re-scan détecté (document falsifié)")
    # suspect
    elif (in_a_core and (QUALITY_CORE_MAX < qualite < QUALITY_SUSPECT_MAX)) \
         or (in_q_core and (ART_CORE_MAX < artefact <= ART_SUSPECT_MAX)) \
         or ((QUALITY_CORE_MAX < qualite <= 44.0) and in_a_core):
        level = "suspect"
        verdict = True
        status  = "invalid"
        if in_a_core and (QUALITY_CORE_MAX < qualite < QUALITY_SUSPECT_MAX):
            message = "artefacts dans l'intervalle et qualité légèrement élevée : re-scan suspect"
        elif in_q_core and (ART_CORE_MAX < artefact <= ART_SUSPECT_MAX):
            message = "qualité dans l'intervalle et artefacts légèrement élevés : re-scan suspect"
        else:
            message = "proche des seuils re-scan : re-scan suspect"
    # none
    else:
        level = "none"
        verdict = False
        status  = "valid"
        message = (f"qualité {qualite:.1f} / artefacts {artefact:.1f} hors zones re-scan : document conforme")

    return {
        "file": file_path,
        "qualite": round(qualite, 1),
        "artefact": round(artefact, 1),
        "rescan": {
    "verdict": verdict,
    "status": status,
    "level": level,
    "message": message
    }
    }