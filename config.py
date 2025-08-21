# ───────────────────────────────────────────────────────────────────────────
# hydro_pipeline/config.py
# ───────────────────────────────────────────────────────────────────────────
"""Schéma de configuration typé pour le pipeline hydrographique.

Ce module définit la structure de configuration sans valeurs par défaut intégrées,
garantissant que tous les paramètres proviennent des fichiers de configuration YAML.

Attributes:
    Config: Dataclass contenant tous les paramètres configurables du pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Conteneur de configuration pour le pipeline hydrographique.

    Tous les champs sont optionnels et doivent être renseignés via les fichiers
    de configuration YAML. Aucune valeur par défaut n'est codée en dur.

    Champs:
        LAT: Latitude du point central (degrés décimaux)
        LON: Longitude du point central (degrés décimaux)
        BBOX_SIZE_KM: Demi-largeur de la zone d'étude (km)
        SITE_NAME: Nom du site d'étude
        EPSG_CIBLE: Code EPSG pour la projection cible
        NODATA_VALUE: Valeur NoData pour les rasters
        STREAM_THRESHOLD_KM2: Seuil d'accumulation pour les cours d'eau (km²)
        GRASS_GISBASE: Chemin d'installation de GRASS GIS
        QGIS_PATH: Chemin d'installation de QGIS (optionnel)
        GDALWARP_CMD: Commande gdalwarp complète
        GDAL_DATA_EXT: Chemin des données GDAL
        PROJ_LIB_EXT: Chemin de la bibliothèque PROJ
        GDAL_BIN_EXT: Chemin des binaires GDAL
        OUTPUT_DIR: Répertoire de sortie
        TEMP_DIR: Répertoire temporaire
        GRASS_DB_DIR: Répertoire de la base GRASS
        OPENTOPOGRAPHY_API_KEY: Clé API OpenTopography
        DEV_MODE: Active le mode développeur (booléen)
    """

    # Géographie et zone d'étude
    LAT: Optional[float] = None
    LON: Optional[float] = None
    BBOX_SIZE_KM: Optional[float] = None
    SITE_NAME: Optional[str] = None

    # Système de référence et données raster
    EPSG_CIBLE: Optional[int] = None
    NODATA_VALUE: Optional[float] = None

    # Paramètres hydrologiques
    STREAM_THRESHOLD_KM2: Optional[float] = None

    # Environnement logiciel
    GRASS_GISBASE: Optional[str] = None
    QGIS_PATH: Optional[str] = None

    # Configuration GDAL/PROJ
    GDALWARP_CMD: Optional[str] = None
    GDAL_DATA_EXT: Optional[str] = None
    PROJ_LIB_EXT: Optional[str] = None
    GDAL_BIN_EXT: Optional[str] = None

    # Gestion des fichiers
    OUTPUT_DIR: Optional[str] = None
    TEMP_DIR: Optional[str] = None
    GRASS_DB_DIR: Optional[str] = None

    # Accès aux données
    OPENTOPOGRAPHY_API_KEY: Optional[str] = None

    # Développement et débogage
    DEV_MODE: Optional[bool] = None