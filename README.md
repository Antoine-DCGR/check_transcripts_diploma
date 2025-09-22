# Vérificateur de documents PDF

Outil d'analyse de documents PDF pour détecter les documents scannés, re-scannés et potentiellement falsifiés.

## Fonctionnalités

- Détection des documents scannés
- Identification des documents re-scannés (scan -> impression -> re-scan)
- Vérification des métadonnées des documents
- Interface web avec Streamlit pour une utilisation simplifiée
- Génération de rapports d'analyse détaillés

## Prérequis

### Pour une installation locale :
- Python 3.8 ou supérieur
- Poppler (pour la conversion PDF en images)
  - Sur Ubuntu/Debian : `sudo apt-get install poppler-utils`
  - Sur macOS : `brew install poppler`

### Pour Docker :
- Docker Engine
- Docker Compose (si vous utilisez docker-compose)

## Installation

### Installation locale

1. Cloner le dépôt :
   ```bash
   git clone [URL_DU_DEPOT]
   cd check_transcripts_diploma
   ```

2. Créer et activer un environnement virtuel :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Linux/Mac
   # OU
   .\venv\Scripts\activate  # Sur Windows
   ```

3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

### Installation avec Docker

#### Option 1 : Avec Docker uniquement

```bash
# Construire l'image
sudo docker build -t check-transcripts .

# Lancer le conteneur
sudo docker run -p 8501:8501 -v $(pwd):/app check-transcripts
```

#### Option 2 : Avec Docker Compose (recommandé)

```bash
# Démarrer le service
docker-compose up -d

# Arrêter le service
docker-compose down
```

Le service sera disponible sur http://localhost:8501


## Utilisation

### En local

#### Ligne de commande

```bash
python main.py chemin/vers/votre/document.pdf
```

#### Interface Web (Streamlit)

```bash
streamlit run streamlit/app.py
```

### Avec Docker

#### Ligne de commande

```bash
# Avec Docker
sudo docker run -v $(pwd)/chemin/vers/votre:/data check-transcripts python main.py /data/document.pdf

# Avec Docker Compose
docker-compose exec check_transcripts_diploma python main.py /data/document.pdf
```

#### Interface Web

L'interface web est automatiquement disponible sur http://localhost:8501 après le démarrage du conteneur.

## Structure du projet

```
.
├── Dockerfile                 # Configuration Docker
├── docker-compose.yml        # Configuration Docker Compose
├── main.py                   # Point d'entrée principal
├── requirements.txt          # Dépendances du projet
├── metadata/                 # Analyse des métadonnées
│   ├── common_utils.py       # Utilitaires communs
│   ├── native_validator.py   # Validation des documents natifs
│   └── scan_validator.py     # Validation des documents scannés
├── rescan/                   # Détection des re-scans
│   └── rescan_detector.py    # Détection des documents re-scannés
├── revision/                 # Vérification des révisions
│   └── pdf_revision.py       # Analyse des révisions de documents
├── streamlit/                # Interface utilisateur web
│   └── app.py               # Application Streamlit
└── tests/                    # Tests unitaires
    └── res/                 # Fichiers de test
```

## Développement

### Exécution des tests

```bash
pytest -v
```

