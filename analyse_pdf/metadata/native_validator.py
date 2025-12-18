#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, Any
from analyse_pdf.metadata.common_utils import (
    extract_all_metadata,
    is_in_blacklist,
    create_result,
    NATIVE_BLACKLIST,
)


def validate_native_document(pdf_path: str) -> Dict[str, Any]:
    """
    Barème NATIF :
    - blacklist détectée → 2 (falsified)
    - sinon → 0 (valid)
    """

    metadata = extract_all_metadata(pdf_path)
    creator = metadata["creator"]
    producer = metadata["producer"]

    blacklisted, app = is_in_blacklist(creator, producer, NATIVE_BLACKLIST)

    if blacklisted:
        return create_result(
            verdict="falsified",
            score=2,
            message=f"Application interdite détectée ({app})",
            pdf_path=pdf_path,
            confidence="high",
        )

    return create_result(
        verdict="valid",
        score=0,
        message="Aucune application suspecte détectée",
        pdf_path=pdf_path,
        confidence="high",
    )
