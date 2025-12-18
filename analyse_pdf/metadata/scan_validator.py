#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, Any
from analyse_pdf.metadata.common_utils import (
    extract_all_metadata,
    is_in_blacklist,
    create_result,
    SCAN_BLACKLIST,
    WEB_TO_PDF_BLACKLIST,
)


def _is_web_pdf(creator: str, producer: str) -> tuple[bool, str]:
    combined = f"{creator} {producer}"
    for item in WEB_TO_PDF_BLACKLIST:
        if item in combined:
            return True, item
    return False, ""


def validate_scan_document(pdf_path: str) -> Dict[str, Any]:
    """
    Barème SCAN (métadonnées) :
    - éditeur image (Photoshop, Canva…) → falsified (score 3)
    - générateur Web/HTML-to-PDF       → falsified (score 3)  ✅ (règle métier)
    - sinon                            → valid (score 0)
    """

    metadata = extract_all_metadata(pdf_path)
    creator = metadata.get("creator", "") or ""
    producer = metadata.get("producer", "") or ""

    # 1) Éditeurs interdits (très fort)
    blacklisted, app = is_in_blacklist(creator, producer, SCAN_BLACKLIST)
    if blacklisted:
        return create_result(
            verdict="falsified",
            score=3,
            message=f"Application interdite détectée ({app})",
            pdf_path=pdf_path,
            confidence="high",
        )

    # 2) Web / HTML-to-PDF (fort selon ton besoin)
    web, tool = _is_web_pdf(creator, producer)
    if web:
        return create_result(
            verdict="falsified",
            score=3,
            message=f"Généré par un outil Web/HTML-to-PDF ({tool})",
            pdf_path=pdf_path,
            confidence="high",
        )

    # 3) Rien à signaler
    return create_result(
        verdict="valid",
        score=0,
        message="Aucune application suspecte détectée",
        pdf_path=pdf_path,
        confidence="high",
    )
