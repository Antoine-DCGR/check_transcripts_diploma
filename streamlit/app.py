import streamlit as st
import json, subprocess, tempfile, os

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
    st.info("Veuillez entrer le mot de passe pour accéder à l’outil.")

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
st.write("Upload un fichier PDF pour analyser s’il est valide, suspect ou falsifié.")

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
            timeout=30
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                st.subheader("Résultat de l’analyse")
                st.json(data)
                verdict = data.get("overall", {}).get("verdict") or data.get("verdict")

                if verdict == "valid":
                    st.success("✅ Document valide")
                elif verdict == "suspect":
                    st.warning("⚠️ Document suspect")
                elif verdict == "falsified":
                    st.error("❌ Document falsifié")
                else:
                    st.info("ℹ️ Résultat non déterminé")
            except json.JSONDecodeError:
                st.error("Erreur : sortie JSON non valide")
                st.text(result.stdout)
        else:
            st.error("Erreur lors de l’exécution du script")
            st.text(result.stderr)
    except subprocess.TimeoutExpired:
        st.error("⏱️ Analyse trop longue (timeout).")
    finally:
        os.unlink(pdf_path)
