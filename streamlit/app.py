#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import json
import subprocess
import tempfile
import os
from pathlib import Path
from io import BytesIO
from PIL import Image

# ------------------ CONFIGURATION ------------------
st.set_page_config(page_title="Vérification de documents", page_icon="🔒", layout="centered")

PASSWORD = st.secrets["app_password"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def do_rerun():
    """Compatibilité rerun (selon version Streamlit)."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# ------------------ AUTHENTIFICATION ------------------
if not st.session_state.authenticated:
    st.title("🔒 Connexion requise")
    st.info("Veuillez entrer le mot de passe pour accéder à l'outil.")

    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.success("Connexion réussie ✅")
            do_rerun()
        else:
            st.error("Mot de passe incorrect ❌")
    st.stop()


# ------------------ PAGE PRINCIPALE ------------------
st.title("🔍 Vérification automatique de documents")
st.write("Uploade un fichier PDF ou image (PNG/JPG/JPEG) pour analyser s'il est valide, suspect ou falsifié.")

uploaded_file = st.file_uploader("Choisis un fichier", type=["pdf", "png", "jpg", "jpeg"])


def _safe_json_parse(s: str):
    try:
        return json.loads(s), None
    except json.JSONDecodeError as e:
        return None, str(e)


def _derive_suffix(name: str) -> str:
    ext = Path(name).suffix
    return ext.lower() if ext else ".bin"


def _verdict_msg(verdict: str | bool):
    """
    Normalise le verdict et retourne (verdict_norm, niveau_streamlit)
    verdict_norm ∈ {"valid","suspect","falsified","invalid","unknown"}
    niveau_streamlit ∈ {"success","warning","error","info"}
    """
    if isinstance(verdict, bool):
        return ("falsified" if verdict else "valid",
                "error" if verdict else "success")

    v = (verdict or "").strip().lower()
    if v in ("valid", "ok"):
        return "valid", "success"
    if v in ("suspect", "warning", "warn", "borderline"):
        return "suspect", "warning"
    if v in ("falsified", "forged"):
        return "falsified", "error"
    if v in ("invalid", "invalide"):
        return "invalid", "error"
    return "unknown", "info"


# ------------------ TRAITEMENT DU FICHIER ------------------
if uploaded_file is not None:
    suffix = _derive_suffix(uploaded_file.name)

    # Aperçu si image
    if suffix in [".png", ".jpg", ".jpeg"]:
        try:
            img = Image.open(BytesIO(uploaded_file.getvalue()))
            st.image(img, caption=f"Aperçu: {uploaded_file.name}", width="stretch")
        except Exception:
            st.info("Aperçu non disponible pour cette image.")

    # Sauvegarde temporaire
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        input_path = tmp_file.name

    st.info(f"Analyse du fichier : {uploaded_file.name}")

    try:
        result = subprocess.run(
            ["python3", "main.py", input_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # --- Logs éventuels ---
        if stderr:
            with st.expander("📄 Logs (stderr)", expanded=False):
                st.code(stderr, language="bash")

        # --- Sortie principale ---
        if result.returncode == 0:
            data, json_err = _safe_json_parse(stdout)
            if json_err:
                st.error("Erreur : sortie JSON non valide")
                with st.expander("Sortie brute (stdout)", expanded=True):
                    st.text(stdout)
            else:
                # --- Normalisation de la structure JSON ---
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]  # le script renvoie une liste -> on prend le premier résultat

                # --- Unification du schéma ---
                overall = data.get("overall", {})
                verdict = overall.get("verdict") or data.get("verdict")
                reasons = overall.get("reasons") or data.get("reasons", [])

                v_norm, level = _verdict_msg(verdict)

                # --- Affichage principal ---
                st.subheader("📋 Résultat de l'analyse")

                if level == "success":
                    st.success("✅ **Document valide**")
                    st.write("Aucun signe de falsification détecté.")
                elif level == "warning":
                    st.warning("⚠️ **Document suspect**")
                    st.write("Le document présente des caractéristiques suspectes à examiner.")
                elif level == "error":
                    st.error("❌ **Document falsifié / invalide**")
                    st.write("Le document présente des signes clairs de falsification ou d'invalidité.")
                else:
                    st.info("ℹ️ **Résultat non déterminé**")
                    st.write("L'analyse n'a pas pu conclure de façon certaine.")

                # --- Raisons détaillées ---
                if reasons and v_norm != "valid":
                    st.subheader("🔍 Détails de l'analyse")
                    for i, reason in enumerate(reasons, 1):
                        if not reason:
                            continue
                        if level == "error":
                            st.error(f"**Raison {i}:** {reason}")
                        elif level == "warning":
                            st.warning(f"**Raison {i}:** {reason}")
                        else:
                            st.info(f"**Raison {i}:** {reason}")

                st.divider()
                with st.expander("🔧 Détails techniques (JSON complet)", expanded=False):
                    st.json(data)

        else:
            st.error("Erreur lors de l'exécution du script")
            # Tenter de parser stdout quand même
            data, json_err = _safe_json_parse(stdout)
            if data is not None:
                st.json(data)
            else:
                st.text(stdout)

    except subprocess.TimeoutExpired:
        st.error("⏱️ Analyse trop longue (timeout).")

    finally:
        try:
            os.unlink(input_path)
        except Exception:
            pass
