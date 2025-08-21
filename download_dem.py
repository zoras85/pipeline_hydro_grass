# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/download_dem.py
# ─────────────────────────────────────────────────────────────────────────────
"""Gestion du téléchargement de MNT ALOS AW3D30 depuis OpenTopography.

Ce module fournit :
- Un calcul précis de bounding box WGS84 géodésiquement correct
- Un téléchargement robuste de données raster avec :
  * Gestion des gros fichiers par flux
  * Journalisation détaillée
  * Gestion complète des erreurs réseau/IO

Fonctions publiques
-------------------
calculate_bbox_wgs84(lat, lon, size_km) -> (west, south, east, north)
    Calcule une emprise géographique centrée sur un point.
telecharger_mnt(bbox, temp_dir, api_key, logger) -> str
    Télécharge un MNT AW3D30 et retourne le chemin du fichier local.
"""

from __future__ import annotations
import os
from typing import Tuple

import numpy as np
import requests


def calculate_bbox_wgs84(lat: float, lon: float, size_km: float) -> Tuple[float, float, float, float]:
    """Calcule une emprise géographique centrée sur (lat, lon).

    La bounding box est calculée en tenant compte de :
    * La courbure terrestre (approximation sphérique)
    * La réduction des distances longitudinales aux hautes latitudes.

    Paramètres
    ----------
    lat : float
        Latitude du centre en degrés décimaux (WGS84)
    lon : float
        Longitude du centre en degrés décimaux (WGS84)
    size_km : float
        Demi-côté de la zone carrée en kilomètres

    Retour
    ------
    Tuple[float, float, float, float]
        Coordonnées (ouest, sud, est, nord) en degrés décimaux

    Notes
    -----
    Utilise une approximation sphérique de la Terre (rayon = 6371 km)
    avec 1 degré ≈ 111 km. La précision est suffisante pour des zones
    de quelques centaines de kilomètres.
    """
    EARTH_DEGREE_KM = 111.0  # Approximation km par degré

    # Conversion latitude
    dlat = size_km / EARTH_DEGREE_KM

    # Conversion longitude avec correction cos(latitude)
    coslat = np.cos(np.radians(lat))
    dlon = size_km / (EARTH_DEGREE_KM * max(coslat, 0.01))  # Seuil à 0.01 pour éviter les valeurs extrêmes

    return (
        lon - dlon,  # ouest
        lat - dlat,  # sud
        lon + dlon,  # est
        lat + dlat  # nord
    )


def telecharger_mnt(bbox: Tuple[float, float, float, float], temp_dir: str, api_key: str, logger) -> str:
    """Télécharge un MNT ALOS AW3D30 depuis l'API OpenTopography.

    Features clés :
    * Téléchargement par blocs pour économiser la mémoire
    * Gestion des timeouts et erreurs réseau
    * Vérification du dossier de destination
    * Journalisation complète du processus.

    Paramètres
    ----------
    bbox : Tuple[float, float, float, float]
        Emprise géographique (ouest, sud, est, nord) en degrés WGS84
    temp_dir : str
        Chemin absolu du dossier de destination
    api_key : str
        Clé d'API OpenTopography valide
    logger : logging.Logger
        Logger pour le suivi d'exécution

    Retour
    ------
    str
        Chemin absolu du fichier GeoTIFF téléchargé

    Exceptions
    ----------
    requests.RequestException
        Pour les erreurs HTTP/timeout
    OSError
        Pour les problèmes d'accès au filesystem
    RuntimeError
        Si le dossier de destination ne peut être créé
    """
    west, south, east, north = bbox
    OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"
    OUTPUT_FILENAME = "alos_raw.tif"

    # Préparation du dossier de destination
    try:
        os.makedirs(temp_dir, exist_ok=True)
    except OSError as e:
        logger.error("Erreur création dossier %s: %s", temp_dir, str(e))
        raise RuntimeError(f"Impossible de créer le dossier {temp_dir}") from e

    out_path = os.path.join(temp_dir, OUTPUT_FILENAME)
    logger.info(
        "Début téléchargement AW3D30 - Emprise: W=%.5f S=%.5f E=%.5f N=%.5f",
        west, south, east, north
    )

    # Configuration requête
    params = {
        "demtype": "AW3D30",
        "south": south,
        "north": north,
        "west": west,
        "east": east,
        "outputFormat": "GTiff",
        "API_Key": api_key,
    }

    try:
        with requests.get(
                OPENTOPO_URL,
                params=params,
                stream=True,
                timeout=300  # 5 minutes timeout
        ) as response:
            response.raise_for_status()

            # Écriture progressive par blocs de 1MB
            with open(out_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1 << 20):  # 1MB
                    if chunk:  # Filtrer les keep-alive chunks vides
                        f.write(chunk)

        logger.info("Téléchargement terminé: %s (%.1f MB)",
                    out_path,
                    os.path.getsize(out_path) / (1024 * 1024))
        return out_path

    except requests.RequestException as e:
        logger.error("Erreur API OpenTopography: %s", str(e))
        raise
    except OSError as e:
        logger.error("Erreur écriture fichier %s: %s", out_path, str(e))
        raise