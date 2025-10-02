import subprocess
import pytest
import json
from pathlib import Path

# Dossiers contenant les fichiers triés
JPEG_ORIGINAL_DIR = Path("tests/jpg/original")
JPEG_FALSIFIED_DIR = Path("tests/jpg/falsified")


def expected_bool(verdict: str) -> bool:
    """Map string verdict ('falsified'/'original' ou 'True'/'False') -> bool attendu."""
    return True if verdict == "True" else False


# Récupère les 50 premiers fichiers falsified
original_files = sorted(JPEG_ORIGINAL_DIR.glob("*.jpg"))
falsified_files = sorted(JPEG_FALSIFIED_DIR.glob("*.jpg"))

# Cas de test (fichier, verdict attendu)
TEST_CASES = [(f, "False") for f in original_files] + [(f, "True") for f in falsified_files]



@pytest.mark.parametrize(
    "img_path,expected_verdict",
    TEST_CASES,
    ids=[f"{f.name}-{v}" for f, v in TEST_CASES],
)
def test_jpeg_png(img_path: Path, expected_verdict: str):
    # Appel du main en mode JSON-only
    result = subprocess.run(
        ["python3", "double_compression_jpeg.py",str(img_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Erreur d'exécution: {result.stderr}"

    try:
        data = json.loads(result.stdout)
    except Exception:
        pytest.fail(f"Impossible de parser JSON: {result.stdout!r}")

    assert "verdict" in data, f"Aucun champ 'verdict' dans la sortie: {data}"
    assert "reasons" in data, f"Aucun champ 'reasons' dans la sortie: {data}"

    expected = expected_bool(expected_verdict)
    actual = bool(data["verdict"])

    # Si échec, on affiche la raison
    assert actual == expected, (
        f"{img_path.name}: attendu={expected}, obtenu={actual}. "
        f"Raison: {data['reasons']}"
    )
