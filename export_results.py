# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/export_results.py
# ─────────────────────────────────────────────────────────────────────────────
"""Export des résultats GRASS : couches vecteur et MNT masqué.

Ce module gère l'export des produits finaux de l'analyse hydrologique vers :
* Un GeoPackage contenant le réseau hydrographique, l'exutoire et le bassin versant
* Un GeoTIFF du MNT masqué par le bassin versant.
"""

from __future__ import annotations
import os
from pathlib import Path


def export_grass_results(gi, output_dir: str, logger) -> None:
    """Exporte les produits finaux (GPKG + GeoTIFF) depuis GRASS."""
    g = gi.grass

    try:
        gpkg_path, dem_path = _prepare_output_paths(output_dir, logger)

        # Export vecteur — réduire la verbosité (quiet=True)
        _export_vector_layers(g, gpkg_path, logger)

        # Export raster — idem
        _export_dem_raster(g, dem_path, logger)

        logger.info("Exports finalisés avec succès : %s | %s", gpkg_path, dem_path)

    except gi.GrassError as e:
        logger.error("Erreur GRASS lors de l'export : %s", str(e))
        raise
    except Exception as e:
        logger.critical("Erreur lors de l'export des résultats : %s", str(e))
        raise RuntimeError(f"Échec de l'export des résultats : {e}") from e


def _prepare_output_paths(output_dir: str, logger) -> tuple[str, str]:
    """Prépare les chemins de sortie et nettoie les fichiers existants."""
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Impossible de créer le dossier de sortie {output_dir} : {e}") from e

    gpkg_path = os.path.join(output_dir, "hydro_results.gpkg")
    dem_path = os.path.join(output_dir, "MNT_decoupe_bassin_versant.tif")

    # Nettoyage des exports précédents
    for file_path in (gpkg_path, dem_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Fichier existant supprimé : %s", file_path)
        except OSError as e:
            logger.warning("Impossible de supprimer le fichier %s : %s", file_path, str(e))

    return gpkg_path, dem_path


def _export_vector_layers(g, gpkg_path: str, logger) -> None:
    """Exporte les couches vectorielles vers un GeoPackage (silencieux)."""
    layers = [
            ("rivieres_clipped", "rivieres"),
            ("outlet_point_clipped", "exutoire"),
            ("main_basin_diss", "main_basin"),
    ]

    for i, (input_layer, output_layer) in enumerate(layers):
        try:
            kwargs = dict(
                input=input_layer,
                output=gpkg_path,
                format="GPKG",
                output_layer=output_layer,
                overwrite=True,
                quiet=True,
            )
            if i > 0:
                kwargs["flags"] = "a"  # append
            g.run_command("v.out.ogr", **kwargs)

            logger.debug("Couche exportée : %s → %s", input_layer, output_layer)
        except Exception as e:
            logger.error("Échec export couche %s : %s", input_layer, str(e))
            raise


def _export_dem_raster(g, dem_path: str, logger) -> None:
    """Exporte le raster MNT vers un GeoTIFF compressé (silencieux)."""
    try:
        g.run_command(
            "r.out.gdal",
            input="dem_filled_masked",
            output=dem_path,
            format="GTiff",
            createopt="COMPRESS=DEFLATE,PREDICTOR=2",
            flags="c",
            overwrite=True,
            quiet=True,  # supprime les messages verbeux de GDAL
        )
        logger.debug("MNT exporté : %s", dem_path)
    except Exception as e:
        logger.error("Échec export MNT : %s", str(e))
        raise
