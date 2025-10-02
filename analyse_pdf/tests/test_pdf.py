import json
import subprocess
import pytest
from pathlib import Path

# Répertoire où sont stockés tes PDF de test
PDF_DIR = Path("tests/res")

# Mapping PDF -> verdict attendu
TEST_CASES = {
    "Diplome_1.pdf": "valid",
    "Diplome_2.pdf": "valid",
    "Diplome_1_2.pdf": "falsified",
    "Diplome_1_image_blanche.pdf": "falsified",
    "Diplome_1_supp.pdf": "falsified",
    "Relevé_de_notes_URENA.pdf": "valid",
    "Relevé_de_notes_URENA1.pdf": "falsified",
    "Relevé_de_notes_URENA2.pdf": "falsified",
    "bulletin_S1.pdf": "valid",
    "bulletin_scan_1.pdf": "valid",
    "bulletin_scan_2.pdf": "valid",
    "re_scan.pdf": "falsified",
    "re_scan_1.pdf": "falsified",
    "re_scan_2.pdf": "falsified",
    "re_scan_3.pdf": "falsified",
    "re_scan_4.pdf": "falsified",
    "re_scan_5.pdf": "falsified",
    "re_scan_christian.pdf": "suspect",
    "re_scan_estelle_1.pdf": "suspect",
    "re_scan_estelle_2.pdf": "suspect",
    "re_scan_estelle_3.pdf": "falsified",
    "re_scan_estelle_4.pdf": "falsified",
    "re_scan_estelle_5.pdf": "falsified",
    "re_scan_abdoul.pdf": "falsified",
    "re_scan_jingyi.pdf": "falsified",
    "re_scan_romain.pdf": "falsified",
    "re_scan_stationF.pdf": "falsified",
    "re_scan_canon_1.pdf": "falsified",
    "re_scan_canon_2.pdf": "falsified",
    "png_to_pdf.pdf": "valid",
    
}


@pytest.mark.parametrize("filename,expected_verdict", TEST_CASES.items())
def test_pdf_verdict(filename, expected_verdict):
    pdf_path = PDF_DIR / filename

    # Appel du script main.py
    result = subprocess.run(
        ["python3", "main.py", str(pdf_path)],
        capture_output=True,
        text=True,
    )

    # Vérifie que le script s'est exécuté
    assert result.returncode == 0, f"Erreur d'exécution: {result.stderr}"

    # Parse le JSON de sortie
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Sortie non JSON: {result.stdout}")

    # Vérifie le verdict global
    assert output.get("overall", {}).get("verdict") == expected_verdict, (
        f"{filename}: attendu={expected_verdict}, obtenu={output}"
    )
