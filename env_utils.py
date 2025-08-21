# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/env_utils.py
# ─────────────────────────────────────────────────────────────────────────────
"""Gestion robuste de l'environnement d'exécution et des sous-processus.

Ce module assure :
* La validation des dépendances externes (GRASS, GDAL, PROJ)
* La configuration sécurisée des environnements d'exécution
* L'exécution tracée de commandes système avec gestion d'erreurs complète.

Éléments publics
----------------
EnvError
    Exception signalant une anomalie de configuration environnementale.
safe_subprocess(cmd_args, env=None, timeout=600, logger=None)
    Lanceur sécurisé de processus externes avec journalisation détaillée.
validate_environment(cfg, logger) → dict
    Vérifie l'intégrité de l'environnement et construit les contextes d'exécution.
"""

from __future__ import annotations
import os
import subprocess
from typing import Dict, Optional

from .config import Config


class EnvError(RuntimeError):
    """Erreur critique liée à la configuration de l'environnement d'exécution."""
    pass


def safe_subprocess(
        cmd_args: list[str],
        env: Optional[Dict[str, str]] = None,
        timeout: int = 600,
        logger=None,
) -> None:
    """Exécute une commande système avec gestion complète des erreurs."""
    cmd_display = " ".join(cmd_args)[:200] + ("…" if len(" ".join(cmd_args)) > 200 else "")
    if logger:
        logger.info("Lancement sous-processus: %s", cmd_display)

    try:
        result = subprocess.run(
            cmd_args,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )

        if logger:
            if result.stdout:
                logger.debug("Sortie standard:\n%s", result.stdout.strip())
            if result.stderr:
                logger.debug("Sortie erreur:\n%s", result.stderr.strip())

    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(
                "Échec commande (code %d): %s\nSortie erreur:\n%s",
                e.returncode,
                cmd_display,
                (e.stderr or "").strip(),
            )
        raise
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("Timeout dépassé (%ds) sur commande: %s", timeout, cmd_display)
        raise
    except Exception as e:
        if logger:
            logger.error("Erreur système lors de l'exécution: %s", str(e))
        raise


def validate_environment(cfg: Config, logger) -> dict:
    """Vérifie l'intégrité de l'environnement et prépare les contextes d'exécution."""
    # 1) Clé API
    if not cfg.OPENTOPOGRAPHY_API_KEY:
        raise EnvError("Configuration manquante: OPENTOPOGRAPHY_API_KEY requis")

    # 2) GRASS
    if not cfg.GRASS_GISBASE or not os.path.isdir(cfg.GRASS_GISBASE):
        raise EnvError(f"Chemin GRASS invalide: {cfg.GRASS_GISBASE}")

    # Racine OSGeo4W (heuristique Windows)
    osgeo4w_root = os.path.dirname(os.path.dirname(os.path.dirname(cfg.GRASS_GISBASE)))
    grass_candidates = [
        os.path.join(osgeo4w_root, "bin", "grass84.bat"),
        os.path.join(cfg.GRASS_GISBASE, "bin", "grass84.bat"),
    ]
    grass_cmd = next((c for c in grass_candidates if os.path.isfile(c)), None)
    if not grass_cmd:
        raise EnvError(f"Aucun binaire GRASS trouvé parmi: {grass_candidates}")

    # Chemin Python de GRASS
    grass_python_path = os.path.join(cfg.GRASS_GISBASE, "etc", "python")
    if not os.path.isdir(grass_python_path):
        raise EnvError(f"Librairies Python GRASS introuvables: {grass_python_path}")

    # 3) GDAL/PROJ
    required_paths = {
        "GDALWARP_CMD": ("gdalwarp", os.path.isfile),
        "GDAL_DATA_EXT": ("GDAL_DATA", os.path.isdir),
        "PROJ_LIB_EXT": ("PROJ_LIB", os.path.isdir),
        "GDAL_BIN_EXT": ("GDAL BIN", os.path.isdir),
    }
    for attr, (label, check) in required_paths.items():
        path = getattr(cfg, attr)
        if not path or not check(path):
            raise EnvError(f"{label} invalide: {path}")

    logger.info("Environnement validé avec succès (GRASS/GDAL/PROJ)")

    # 4) Construction env GDAL + Python OSGeo4W
    gdal_env = os.environ.copy()
    gdal_env.update({
        "GDAL_DATA": cfg.GDAL_DATA_EXT,
        "PROJ_LIB": cfg.PROJ_LIB_EXT,
        "PATH": f"{cfg.GDAL_BIN_EXT}{os.pathsep}{gdal_env.get('PATH', '')}",
    })

    # Définir un PYTHONHOME cohérent pour calmer "<prefix>"
    python_home_candidates = [
        os.path.join(osgeo4w_root, "apps", "Python312"),
        os.path.join(osgeo4w_root, "apps", "Python311"),
        os.path.join(osgeo4w_root, "apps", "Python310"),
    ]
    python_home = next((p for p in python_home_candidates if os.path.isdir(p)), None)
    if python_home:
        gdal_env["PYTHONHOME"] = python_home

    # Assurer PYTHONPATH incluant les libs GRASS
    grass_py = grass_python_path
    if gdal_env.get("PYTHONPATH"):
        gdal_env["PYTHONPATH"] = os.pathsep.join([grass_py, gdal_env["PYTHONPATH"]])
    else:
        gdal_env["PYTHONPATH"] = grass_py

    # Propager aussi à l'environnement du processus courant (pour GRASS Python)
    os.environ.update(gdal_env)

    return {
        "GRASS_CMD": grass_cmd,
        "GRASS_PYTHON_PATH": grass_python_path,
        "GDAL_ENV": gdal_env,
    }
