# ───────────────────────────────────────────────────────────────────────────
# hydro_pipeline/__init__.py
# ───────────────────────────────────────────────────────────────────────────
"""Package principal du pipeline hydrographique ALOS → GRASS.

Fournit une interface unifiée pour l'analyse hydrographique complète :
1. Téléchargement des MNT ALOS AW3D30
2. Prétraitement des données raster
3. Analyse hydrologique sous GRASS GIS
4. Export des résultats pour SWAT+ et SIG

API publique:
    Config: Schéma de configuration principal
    from_yaml_pair() : Charge les configurations YAML
    merge_config() : Fusionne les configurations
    setup_logging() : Configure le système de logs
    validate_environment() : Vérifie les dépendances
    calculate_bbox_wgs84() : Calcule l'emprise de travail
    pretraiter_mnt() : Prétraitement du MNT
    analyse_hydro_grass() : Workflow hydrologique complet
    export_grass_results() : Export des résultats finaux.

Version : 3.2.0 (Reproductible - Configuration 100% YAML)
"""

from __future__ import annotations

# Metadata
__version__ = "3.2.0"
__author__ = "Zo RASOANAIVO"
__contact__ = "<razorivo85@gmail.com>"
__license__ = "MIT"
__copyright__ = "2025"

# Imports principaux
from .config import Config
from .config_io import (
    from_yaml_pair,
    merge_config,
    save_editable_yaml,
)
from .logging_setup import setup_logging
from .env_utils import validate_environment, safe_subprocess
from .download_dem import calculate_bbox_wgs84, telecharger_mnt
from .preprocess_dem import pretraiter_mnt
from .grass_session import init_grass_modules, initialiser_grass
from .hydro_analysis import analyse_hydro_grass
from .export_results import export_grass_results

# Structure du package
__all__ = [
    # Modules
    "config",
    "config_io",
    "logging_setup",
    "env_utils",
    "download_dem",
    "preprocess_dem",
    "grass_session",
    "hydro_analysis",
    "export_results",
    "gui",

    # Fonctions principales
    "Config",
    "from_yaml_pair",
    "merge_config",
    "save_editable_yaml",
    "setup_logging",
    "validate_environment",
    "safe_subprocess",
    "calculate_bbox_wgs84",
    "telecharger_mnt",
    "pretraiter_mnt",
    "init_grass_modules",
    "initialiser_grass",
    "analyse_hydro_grass",
    "export_grass_results",

    # Metadata
    "__version__"
]

# Documentation supplémentaire
__doc__ += """
Workflow typique:
    1. Charger la configuration (from_yaml_pair)
    2. Valider l'environnement (validate_environment)
    3. Télécharger le MNT (telecharger_mnt)
    4. Prétraiter les données (pretraiter_mnt)
    5. Lancer l'analyse (analyse_hydro_grass)
    6. Exporter les résultats (export_grass_results)

Référence:
    Rasoanaivo, Z. (2025) - ORCID: 0009-0003-0725-3764
    Pipeline modulaire et reproductible pour l'hydrographie
    avec ALOS AW3D30 et GRASS GIS.
"""