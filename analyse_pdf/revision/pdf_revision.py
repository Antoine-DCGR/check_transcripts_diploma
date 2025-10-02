#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse de révisions PDF via deux méthodes :
1. CLI 'pdfresurrect' (prioritaire)
2. Comparaison des dates de création/modification (si pdfresurrect ne détecte rien)
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

class PdfResurrectNotFound(RuntimeError):
    pass

def analyze_with_pdfresurrect(pdf_path: str) -> Optional[Dict]:
    """
    Analyse via pdfresurrect CLI.
    
    :param pdf_path: chemin du PDF
    :return: Dict avec résultat ou None si pas de réécriture détectée
    """
    if not shutil.which("pdfresurrect"):
        raise PdfResurrectNotFound(
            "pdfresurrect introuvable dans le PATH. Installe-le (ex: sudo apt-get install pdfresurrect)."
        )
    
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")
    
    try:
        out = subprocess.check_output(
            ["pdfresurrect", "-q", pdf_path],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        
        # Cherche le dernier entier sur la ligne (nombre de versions)
        m = re.search(r"(\d+)\s*$", out)
        versions = int(m.group(1)) if m else 1
        versions = max(1, versions)
        
        rewrites = max(0, versions - 1)
        
        if rewrites > 0:
            return {
                "ok": False,
                "rewrites": rewrites,
                "method": "pdfresurrect",
                "message": f"{rewrites} réécriture{'s' if rewrites > 1 else ''} détectée{'s' if rewrites > 1 else ''} (pdfresurrect)."
            }
        
        return None  # Pas de réécriture détectée
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erreur lors de l'exécution de pdfresurrect: {e}")

def analyze_with_dates(pdf_path: str) -> Dict:
    """
    Analyse via comparaison des dates de création et modification.
    
    :param pdf_path: chemin du PDF
    :return: Dict avec le résultat
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")
    
    try:
        # Dates du système de fichiers
        stat = os.stat(pdf_path)
        file_mtime = stat.st_mtime
        file_ctime = stat.st_ctime  # Sur Unix: dernière modif des métadonnées, sur Windows: création
        
        # Tentative d'extraction des métadonnées PDF
        pdf_creation_date = None
        pdf_modification_date = None
        
        if PYPDF2_AVAILABLE:
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PdfReader(file)
                    if reader.metadata:
                        # Les dates PDF sont au format D:YYYYMMDDHHmmSSOHH'mm'
                        creation_date = reader.metadata.get('/CreationDate')
                        mod_date = reader.metadata.get('/ModDate')
                        
                        # Pour simplification, on compare juste si les dates sont identiques
                        if creation_date and mod_date:
                            pdf_creation_date = creation_date
                            pdf_modification_date = mod_date
            except Exception:
                pass  # Ignore les erreurs de lecture PDF
        
        # Logique de comparaison
        dates_equal = False
        comparison_method = "filesystem"
        
        if pdf_creation_date and pdf_modification_date:
            # Comparaison des métadonnées PDF
            dates_equal = (pdf_creation_date == pdf_modification_date)
            comparison_method = "pdf_metadata"
        else:
            # Fallback: comparaison des dates système (avec tolérance de 1 seconde)
            dates_equal = abs(file_ctime - file_mtime) <= 1.0
            comparison_method = "filesystem"
        
        if dates_equal:
            return {
                "ok": True,
                "rewrites": 0,
                "method": f"dates_{comparison_method}",
                "message": "PDF non falsifié (dates de création/modification identiques)."
            }
        else:
            return {
                "ok": False,
                "rewrites": 1,  # On assume 1 réécriture basée sur les dates
                "method": f"dates_{comparison_method}",
                "message": "Réécriture détectée (dates de création/modification différentes)."
            }
            
    except Exception as e:
        return {
            "ok": False,
            "rewrites": 0,
            "method": "dates_error",
            "message": f"Erreur lors de l'analyse des dates: {str(e)}"
        }

def analyze_pdf_complete(pdf_path: str) -> Dict:
    """
    Analyse complète du PDF avec les deux méthodes.
    pdfresurrect est prioritaire, la comparaison de dates n'est utilisée que si pdfresurrect ne détecte rien.
    
    :param pdf_path: chemin du PDF
    :return: Dict avec le résultat final
    """
    try:
        # 1. Tentative avec pdfresurrect (prioritaire)
        pdfresurrect_result = analyze_with_pdfresurrect(pdf_path)
        
        if pdfresurrect_result is not None:
            # pdfresurrect a détecté une réécriture, on s'arrête là
            return pdfresurrect_result
        
        # 2. pdfresurrect n'a rien détecté, on utilise la comparaison de dates
        return analyze_with_dates(pdf_path)
        
    except PdfResurrectNotFound:
        # pdfresurrect non disponible, on utilise seulement les dates
        return analyze_with_dates(pdf_path)
    
    except Exception as e:
        return {
            "ok": False,
            "rewrites": 0,
            "method": "error",
            "message": f"Erreur lors de l'analyse: {str(e)}"
        }

# Exemple d'utilisation
if __name__ == "__main__":
    pdf_file = "example.pdf"  # Remplace par ton fichier PDF
    result = analyze_pdf_complete(pdf_file)
    
    print(f"Résultat: {result['message']}")
    print(f"OK: {result['ok']}")
    print(f"Réécritures: {result['rewrites']}")
    print(f"Méthode: {result['method']}")