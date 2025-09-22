import streamlit as st
import json
import subprocess
import tempfile
import os

st.title("🔍 Vérification automatique de documents PDF")
st.write("Upload un fichier PDF pour analyser s’il est valide, suspect ou falsifié.")

# Upload du fichier PDF
uploaded_file = st.file_uploader("Choisis un fichier PDF", type=["pdf"])

if uploaded_file is not None:
    # Sauvegarde temporaire du fichier uploadé
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        pdf_path = tmp_file.name

    st.info(f"Analyse du fichier : {uploaded_file.name}")

    try:
        # Appel de ton script d’analyse (ici j’imagine que c’est main.py)
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
                st.json(data)  # affichage format JSON
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
        os.unlink(pdf_path)  # nettoyage du fichier temporaire
