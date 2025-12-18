import json
import subprocess
import pytest
from pathlib import Path

# Dossier contenant tous les candidats
# Chaque sous-dossier = 1 candidat
# Chaque sous-dossier contient plusieurs pièces jointes (PDF)
TEST_CANDIDAT_DIR = Path("analyse_pdf/tests/test_document_tri")


def collect_candidate_pdfs():
    """
    Parcourt analyse_pdf/tests/test_candidat/
    et retourne la liste de tous les fichiers PDF
    trouvés dans les sous-dossiers candidats.
    """
    pdf_files = []

    if not TEST_CANDIDAT_DIR.exists():
        pytest.fail(f"Dossier introuvable : {TEST_CANDIDAT_DIR}")

    for candidate_dir in TEST_CANDIDAT_DIR.iterdir():
        if not candidate_dir.is_dir():
            continue

        for file in candidate_dir.iterdir():
            if file.is_file() and file.suffix.lower() == ".pdf":
                pdf_files.append(file)

    if not pdf_files:
        pytest.fail("Aucun fichier PDF trouvé dans test_candidat")

    return pdf_files


@pytest.mark.parametrize("pdf_path", collect_candidate_pdfs())
def test_candidate_documents_are_valid(pdf_path):
    """
    Toutes les pièces jointes de tous les candidats
    doivent être considérées comme VALID.
    """
    result = subprocess.run(
        ["python3", "main.py", str(pdf_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Erreur d'exécution pour {pdf_path}\n"
        f"stderr:\n{result.stderr}"
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"Sortie non JSON pour {pdf_path}\n"
            f"stdout:\n{result.stdout}"
        )

    verdict = output.get("overall", {}).get("verdict")

    assert verdict == "valid", (
        f"{pdf_path}\n"
        f"attendu=valid, obtenu={verdict}\n"
        f"sortie complète:\n{json.dumps(output, indent=2)}"
    )
