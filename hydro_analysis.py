# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/hydro_analysis.py
# ─────────────────────────────────────────────────────────────────────────────
"""Chaîne d'analyse hydrologique sous GRASS GIS.

Ce module exécute un workflow complet d'analyse hydrologique incluant :
* Import et traitement du MNT
* Extraction du réseau hydrographique
* Délimitation de bassin versant
* Préparation des données pour SWAT+
"""

from __future__ import annotations
import os
from typing import Tuple
from pyproj import Transformer


def analyse_hydro_grass(
        gi,
        cleaned_dem_path: str,
        lat: float,
        lon: float,
        threshold_km2: float,
        epsg_wgs84: int,
        epsg_target: int,
        logger,
) -> Tuple[float, float]:
    g = gi.grass

    try:
        _import_and_setup_dem(g, cleaned_dem_path)
        _run_hydrological_analysis(g, logger)
        seuil = _calculate_threshold(g, threshold_km2, logger)
        _extract_stream_network(g, seuil)

        out_x, out_y = _process_input_point(
            g, gi, lat, lon, epsg_wgs84, epsg_target, cleaned_dem_path, logger
        )

        _delineate_watershed(g, out_x, out_y)
        _prepare_swat_outlet(g, out_x, out_y, cleaned_dem_path)
        _post_processing(g, logger)

        return out_x, out_y

    except gi.GrassError as e:
        logger.error("Erreur GRASS dans l'analyse hydrologique: %s", str(e))
        raise
    except Exception as e:
        logger.critical("Erreur inattendue dans l'analyse hydrologique: %s", str(e))
        raise RuntimeError(f"Échec de l'analyse hydrologique: {e}") from e


def _import_and_setup_dem(g, dem_path: str) -> None:
    g.run_command("r.in.gdal", input=dem_path, output="dem", flags="o", overwrite=True, quiet=True)
    g.run_command("g.region", raster="dem", flags="p", quiet=True)


def _run_hydrological_analysis(g, logger) -> None:
    g.run_command(
        "r.fill.dir",
        input="dem",
        output="dem_filled",
        direction="drain_map_for_outlet",
        overwrite=True,
        quiet=True,
    )
    g.run_command(
        "r.watershed",
        elevation="dem_filled",
        accumulation="flow_acc",
        drainage="drain_map_for_outlet",
        threshold=1,
        overwrite=True,
        quiet=True,
    )
    logger.debug("Traitements hydrologiques de base terminés")


def _calculate_threshold(g, threshold_km2: float, logger) -> int:
    region = g.parse_command("g.region", flags="g", quiet=True)
    cell_area = float(region["ewres"]) * float(region["nsres"])
    seuil = max(1, int(threshold_km2 * 1_000_000.0 / cell_area))
    logger.info("Seuil d'accumulation: %d cellules (%.2f km²)", seuil, threshold_km2)
    return seuil


def _extract_stream_network(g, threshold: int) -> None:
    g.run_command(
        "r.stream.extract",
        elevation="dem_filled",
        accumulation="flow_acc",
        threshold=threshold,
        stream_rast="streams",
        stream_vect="rivieres",
        overwrite=True,
        quiet=True,
    )


def _process_input_point(
        g, gi, lat: float, lon: float, epsg_wgs84: int, epsg_target: int, base_path: str, logger
) -> Tuple[float, float]:
    transformer = Transformer.from_crs(
        f"EPSG:{epsg_wgs84}", f"EPSG:{epsg_target}", always_xy=True
    )
    proj_x, proj_y = transformer.transform(lon, lat)

    csv_path = os.path.join(os.path.dirname(base_path), "input_point_proj.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("x,y,name\n")
        f.write(f"{proj_x},{proj_y},input_location\n")

    g.run_command(
        "v.in.ascii",
        input=csv_path,
        output="input_point_proj",
        x=1,
        y=2,
        separator="comma",
        skip=1,
        overwrite=True,
        quiet=True,
    )

    out = g.read_command(
        "v.distance",
        from_="input_point_proj",
        to="rivieres",
        upload="dist,to_x,to_y",
        to_type="line",
        flags="p",
        quiet=True,
    )
    lines = (out or "").strip().splitlines()
    if len(lines) < 2:
        raise gi.GrassError("Aucun cours d'eau trouvé à proximité du point d'entrée")

    parts = lines[1].split("|")
    out_x, out_y = float(parts[2]), float(parts[3])
    logger.info("Exutoire ajusté: (%.2f, %.2f)", out_x, out_y)
    return out_x, out_y


def _delineate_watershed(g, x: float, y: float) -> None:
    g.run_command(
        "r.water.outlet",
        input="drain_map_for_outlet",
        output="main_basin",
        coordinates=[x, y],
        overwrite=True,
        quiet=True,
    )
    g.run_command(
        "r.to.vect",
        input="main_basin",
        output="main_basin_vect",
        type="area",
        flags="s",
        overwrite=True,
        quiet=True,
    )


def _prepare_swat_outlet(g, x: float, y: float, base_path: str) -> None:
    csv_path = os.path.join(os.path.dirname(base_path), "outlet_point_swat.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("x,y,PointId,RES,INLET,ID,PTSOURCE\n")
        f.write(f"{x},{y},1,0,0,1,0\n")

    g.run_command(
        "v.in.ascii",
        input=csv_path,
        output="outlet_point",
        x=1,
        y=2,
        separator="comma",
        skip=1,
        overwrite=True,
        quiet=True,
    )

    columns = [
        ("PointId", "1"), ("RES", "0"),
        ("INLET", "0"), ("ID", "1"), ("PTSOURCE", "0")
    ]
    g.run_command(
        "v.db.addcolumn",
        map="outlet_point",
        columns=",".join(f"{col} INTEGER" for col, _ in columns),
        quiet=True,
    )
    for col, val in columns:
        g.run_command("v.db.update", map="outlet_point", column=col, value=val, quiet=True)


def _post_processing(g, logger) -> None:
    """Post-traitement silencieux (sans avertissements)."""
    # 1) Réseau lignes uniquement
    g.run_command(
        "v.extract",
        input="rivieres",
        type="line",
        output="rivieres_only_lines",
        overwrite=True,
        quiet=True,
    )
    g.run_command("v.build", map="rivieres_only_lines", quiet=True)

    # 2) Dissoudre le bassin par catégorie pour éviter l'avertissement
    g.run_command(
        "v.dissolve",
        input="main_basin_vect",
        output="main_basin_diss",
        column="cat",          # évite "No 'column' option specified..."
        overwrite=True,
        quiet=True,
    )

    # 3) Clip du réseau par le bassin dissous
    g.run_command(
        "v.clip",
        input="rivieres_only_lines",
        clip="main_basin_diss",
        output="rivieres_clipped",
        overwrite=True,
        quiet=True,
    )

    # 4) Clip du point d'exutoire
    g.run_command(
        "v.select",
        ainput="outlet_point",
        binput="main_basin_diss",
        output="outlet_point_clipped",
        operator="within",
        overwrite=True,
        quiet=True,
    )

    # 5) Masque raster final
    g.run_command("r.mask", vector="main_basin_diss", overwrite=True, quiet=True)
    g.run_command("r.mapcalc", expression="dem_filled_masked=dem_filled", overwrite=True, quiet=True)
    g.run_command("r.mask", flags="r", overwrite=True, quiet=True)

    logger.debug("Post-traitement terminé (silencieux).")
