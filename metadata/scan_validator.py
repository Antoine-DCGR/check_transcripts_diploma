#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation des métadonnées pour les documents scannés.
Logique inversée : blacklist d'applications interdites.
"""

from typing import Dict, Any
from .common_utils import extract_all_metadata, is_in_blacklist, create_result, SCAN_BLACKLIST


def validate_scan_document(pdf_path: str) -> Dict[str, Any]:
    """
    Valide un document scanné via blacklist inversée.
    
    Logique :
    1. Si Creator/Producer contient un élément de la SCAN_BLACKLIST → FALSIFIÉ
    2. Sinon → VALIDE
    """
    # Extraction des métadonnées
    metadata = extract_all_metadata(pdf_path)
    creator = metadata['creator']
    producer = metadata['producer']
    
    # Vérification blacklist
    blacklisted, detected_app = is_in_blacklist(creator, producer, SCAN_BLACKLIST)
    
    if blacklisted:
        return create_result(
            ok=False,
            message=f"Document falsifié : application interdite détectée ({detected_app})",
            verdict="falsified",
            pdf_path=pdf_path,
            confidence="high"
        )
    
    # Aucun élément blacklisté trouvé → document valide
    return create_result(
        ok=True,
        message="Document valide : aucune application suspecte détectée",
        verdict="valid",
        pdf_path=pdf_path,
        confidence="high"
    )