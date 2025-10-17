import subprocess
import json

def run_exiftool(path: str) -> dict:
    """Exécute ExifTool sur un fichier et renvoie le JSON parsé."""
    try:
        result = subprocess.run(
            ["exiftool", "-j", path],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}
    except subprocess.CalledProcessError as e:
        return {"error": f"ExifTool error: {e.stderr.strip()}"}
    except Exception as e:
        return {"error": str(e)}
