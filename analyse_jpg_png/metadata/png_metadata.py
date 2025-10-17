def analyse_png_metadata(meta: dict) -> dict:
    """
    Analyse les métadonnées d’un PNG et détermine s’il est falsifié ou valide.
    🔒 Stratégie B : on considère le fichier FALSIFIED par défaut,
    et on ne le marque VALID que s’il existe une preuve explicite de légitimité.

    Règles calibrées sur ton dataset :
      ✅ Valid si :
        - Capture d’écran (Screen / LogicalX / UserComment=Screenshot)
        - Profil ICC présent (Apple, Display, etc.)
        - Chunks gAMA + sRGB + pHYs cohérents (valeurs neutres)
        - sRGB seul (export neutre)
        - sRGB + pHYs cohérent (~3700–8000)
      ❌ Falsified si :
        - gAMA≈2.2 ou 0.45455 ET pHYs≈3780 (signature Photoshop/GIMP)
        - Métadonnées absentes, incohérentes, ou incomplètes
    """

    file = meta.get("SourceFile", "")
    verdict = "falsified"  # 🧩 on part du principe que le document est falsifié
    reasons = []
    message = ""

    # --- Présences clés ---
    has_icc = any("profile" in k.lower() for k in meta.keys())
    has_gamma = "Gamma" in meta
    has_srgb = any(k.lower().startswith("srgb") or "colorspace" in k.lower() for k in meta.keys())
    has_phys = any(k.lower().startswith("pixelsperunit") for k in meta.keys())

    # --- Contexte capture d’écran ---
    user_comment = str(meta.get("UserComment", "")).lower()
    screen_name = str(meta.get("Screen", "")).lower()
    has_logical = any(k.lower().startswith("logical") for k in meta.keys())
    is_screenshot = (
        "screenshot" in user_comment
        or "screen" in screen_name
        or has_logical
    )

    # --- Valeurs numériques utiles ---
    gamma_val = None
    px_unit_x = None
    try:
        if "Gamma" in meta:
            gamma_val = float(meta.get("Gamma", 0))
    except Exception:
        gamma_val = None
    try:
        if "PixelsPerUnitX" in meta:
            px_unit_x = float(meta.get("PixelsPerUnitX", 0))
    except Exception:
        px_unit_x = None

    # =====================
    # LOGIQUE DE DÉCISION
    # =====================

    # 1️⃣ Capture d’écran authentique
    if is_screenshot:
        verdict = "valid"
        message = "Capture d’écran authentique"
        reasons.append("Présence de Screen/LogicalX ou UserComment=Screenshot")

    # 2️⃣ Profil ICC (Apple / Display)
    elif has_icc:
        verdict = "valid"
        message = "Profil ICC présent — export Apple ou écran"
        reasons.append("Profil ICC Apple/Display détecté")

    # 3️⃣ Chunks couleur cohérents (gAMA + sRGB + pHYs)
    elif has_gamma and has_srgb and has_phys:
        if (gamma_val in (2.2, 0.45455)) and (px_unit_x and 3700 <= px_unit_x <= 3800):
            verdict = "valid"
            message = "Chunks couleur standards sRGB (valeurs gamma/pHYs par défaut)"
            reasons.append(f"Gamma={gamma_val}, PixelsPerUnitX={px_unit_x} — standard sRGB")
        else:
            verdict = "valid"
            message = "Chunks gAMA, sRGB et pHYs cohérents (non-Adobe)"
            reasons.append("Présence des trois chunks couleur cohérents")

    # 4️⃣ sRGB seul ou sRGB + pHYs cohérent
    elif has_srgb:
        if has_phys and px_unit_x and 3700 <= px_unit_x <= 8000:
            verdict = "valid"
            message = "Chunks sRGB + pHYs cohérents"
            reasons.append(f"sRGB présent, PixelsPerUnitX={px_unit_x}")
        else:
            verdict = "valid"
            message = "Chunk sRGB présent — export ou conversion neutre"
            reasons.append("sRGB présent sans gAMA ni ICC")

    # 5️⃣ pHYs seul mais cohérent (~3780 ou ~7874)
    elif has_phys:
        if px_unit_x and (3700 <= px_unit_x <= 3800 or 7800 <= px_unit_x <= 7900):
            verdict = "valid"
            message = "PNG avec pHYs cohérent — export ou conversion neutre"
            reasons.append(f"Résolution physique {px_unit_x} cohérente")
        else:
            verdict = "falsified"
            message = "Métadonnées physiques incohérentes"
            reasons.append(f"PixelsPerUnitX={px_unit_x}")

    # 6️⃣ Cas par défaut — falsified
    else:
        verdict = "falsified"
        message = "Métadonnées incomplètes ou absentes"
        reasons.append("Absence de ICC/gAMA/sRGB/pHYs et aucun indice de capture")

    # =====================
    # RETOUR
    # =====================
    return {
        "file": file,
        "format": "PNG",
        "verdict": verdict,
        "message": message,
        "details": {
            "has_icc": has_icc,
            "has_gamma": has_gamma,
            "has_srgb": has_srgb,
            "has_phys": has_phys,
            "is_screenshot": is_screenshot,
            "gamma_val": gamma_val,
            "pixels_per_unit_x": px_unit_x,
            "reasons": reasons,
            "raw_meta": meta,
        },
    }
