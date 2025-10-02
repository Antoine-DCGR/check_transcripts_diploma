import streamlit as st
import json
import subprocess
import tempfile
import os

st.set_page_config(page_title="Vérification PDF", page_icon="🔒", layout="centered")

PASSWORD = st.secrets["app_password"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def do_rerun():
    # compat: si vieille version, on tente experimental_rerun
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()  # fallback pour versions <1.27

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

# ----- zone protégée -----
st.title("🔍 Vérification automatique de documents PDF")
st.write("Upload un fichier PDF pour analyser s'il est valide, suspect ou falsifié.")

uploaded_file = st.file_uploader("Choisis un fichier PDF", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        pdf_path = tmp_file.name

    st.info(f"Analyse du fichier : {uploaded_file.name}")

    try:
        result = subprocess.run(
            ["python3", "main.py", pdf_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)

                # Récupération du verdict et des raisons
                verdict = data.get("overall", {}).get("verdict") or data.get("verdict")
                reasons = (
                    data.get("overall", {}).get("reasons")
                    or data.get("reasons")
                    or []
                )

                st.subheader("📋 Résultat de l'analyse")

                # Message principal
                if verdict == "valid":
                    st.success("✅ **Document valide**")
                    st.write("Le document n'a montré aucun signe de falsification.")
                elif verdict == "suspect":
                    st.warning("⚠️ **Document suspect**")
                    st.write("Le document présente des caractéristiques suspectes qui nécessitent une attention particulière.")
                elif verdict == "falsified":
                    st.error("❌ **Document falsifié**")
                    st.write("Le document présente des signes clairs de falsification ou de modification.")
                else:
                    st.info("ℹ️ **Résultat non déterminé**")
                    st.write("L'analyse n'a pas pu déterminer de façon définitive l'authenticité du document.")

                # ⚠️ N'afficher les raisons que si le document n'est PAS valid
                if reasons and verdict != "valid":
                    st.subheader("🔍 Détails de l'analyse")
                    for i, reason in enumerate(reasons, 1):
                        if verdict == "falsified":
                            st.error(f"**Raison {i}:** {reason}")
                        elif verdict == "suspect":
                            st.warning(f"**Raison {i}:** {reason}")
                        else:
                            st.info(f"**Raison {i}:** {reason}")

                st.divider()

                # JSON complet (mode dev)
                with st.expander("🔧 Détails techniques (JSON complet)", expanded=False):
                    st.json(data)

            except json.JSONDecodeError:
                st.error("Erreur : sortie JSON non valide")
                st.text(result.stdout)
        else:
            st.error("Erreur lors de l'exécution du script")
            st.text(result.stderr)
    except subprocess.TimeoutExpired:
        st.error("⏱️ Analyse trop longue (timeout).")
    finally:
        os.unlink(pdf_path)
