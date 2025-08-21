# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/preprocess_dem.py
# ─────────────────────────────────────────────────────────────────────────────
"""Prétraitement du MNT : reprojection et assainissement des valeurs.

Ce module délègue la reprojection à "gdalwarp" (GDAL) et effectue un
nettoyage simple des valeurs aberrantes avec Rasterio :
* reprojection vers l'EPSG cible (interpolation bilinéaire) ;
* remplacement de valeurs évidemment invalides par une valeur NoData cohérente.
"""

from __future__ import annotations
import os
from typing import Any

import numpy as np
import rasterio
from rasterio.io import DatasetWriter
from logging import Logger

from .env_utils import safe_subprocess


def _reprojection_gdalwarp(
        raw_dem_path: str,
        out_path: str,
        epsg_cible: int,
        gdal_env: dict[str, Any],
        gdalwarp_cmd: str,
        logger: Logger
) -> None:
    """Exécute la reprojection du MNT avec gdalwarp.

    Args:
        raw_dem_path: Chemin vers le MNT source
        out_path: Chemin de sortie pour le MNT reprojeté
        epsg_cible: Code EPSG de destination
        gdal_env: Environnement d'exécution GDAL
        gdalwarp_cmd: Chemin vers l'exécutable gdalwarp
        logger: Logger pour le suivi

    Raises:
        RuntimeError: Si l'exécution de gdalwarp échoue
    """
    cmd = [
        gdalwarp_cmd,
        "-overwrite",
        "-t_srs", f"EPSG:{epsg_cible}",
        "-r", "bilinear",
        raw_dem_path,
        out_path,
    ]
    safe_subprocess(cmd, env=gdal_env, timeout=900, logger=logger)


def _nettoyage_valeurs_rasterio(
        out_path: str,
        nodata_value: float,
        logger: Logger
) -> None:
    """Nettoie les valeurs aberrantes du raster et met à jour les métadonnées.

    Args:
        out_path: Chemin vers le fichier raster à nettoyer
        nodata_value: Valeur NoData à utiliser
        logger: Logger pour le suivi

    Raises:
        RuntimeError: En cas d'erreur de traitement du raster
    """
    with rasterio.open(out_path, "r+") as ds:
        arr = ds.read(1, masked=True)
        mask = (arr < -100) | (arr > 10000)
        arr = np.ma.masked_where(mask, arr)

        filled = arr.filled(nodata_value)
        ds.write(filled, 1)

        _mettre_a_jour_metadonnees_nodata(ds, nodata_value)

    logger.info("MNT reprojeté et nettoyé : %s", out_path)


def _mettre_a_jour_metadonnees_nodata(
        ds: DatasetWriter,
        nodata_value: float
) -> None:
    """Met à jour les métadonnées NoData du raster.

    Args:
        ds: Dataset Rasterio en mode écriture
        nodata_value: Valeur NoData à enregistrer
    """
    ds.update_tags(nodata=nodata_value)
    try:
        ds.nodata = nodata_value
    except Exception:
        pass


def pretraiter_mnt(
        raw_dem_path: str,
        temp_dir: str,
        epsg_cible: int,
        nodata_value: float,
        gdal_env: dict[str, Any],
        gdalwarp_cmd: str,
        logger: Logger,
) -> str:
    """Reprojeter et assainir le MNT.

    Étapes:
        1) Reprojection vers l'EPSG cible via gdalwarp (bilinéaire)
        2) Assainissement : détection de valeurs aberrantes et remplacement par NoData

    Args:
        raw_dem_path: Chemin du GeoTIFF brut
        temp_dir: Dossier de travail temporaire
        epsg_cible: Code EPSG de destination
        nodata_value: Valeur NoData cohérente
        gdal_env: Environnement d'exécution GDAL
        gdalwarp_cmd: Chemin vers l'exécutable gdalwarp
        logger: Logger pour le suivi

    Returns:
        Chemin du GeoTIFF reprojeté et nettoyé

    Raises:
        RuntimeError: En cas d'échec de reprojection ou de traitement raster
    """
    out_path = os.path.join(temp_dir, "cleaned_dem_temp.tif")

    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        _reprojection_gdalwarp(raw_dem_path, out_path, epsg_cible, gdal_env, gdalwarp_cmd, logger)
        _nettoyage_valeurs_rasterio(out_path, nodata_value, logger)
        return out_path

    except Exception as e:
        raise RuntimeError(f"Échec du prétraitement du MNT : {e}") from e