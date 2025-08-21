# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/grass_session.py
# ─────────────────────────────────────────────────────────────────────────────
"""Import dynamique des modules GRASS et initialisation d'une session.

Ce module fournit :
* un import sécurisé des modules Python de GRASS depuis un chemin spécifique
* une fonction d'initialisation de LOCATION/MAPSET avec création si nécessaire
* une configuration correcte des variables d'environnement GRASS.

Fonctions publiques
-------------------
init_grass_modules(grass_python_path, logger) → GrassImports
    Charge les modules GRASS depuis le chemin spécifié.
initialiser_grass(gi, grass_cmd, gisdb_path, location_name, mapset_name, epsg_code, logger)
    Initialise une session GRASS avec les paramètres donnés.
"""

from __future__ import annotations
import os
import sys
import subprocess
import importlib
from typing import Optional, Any


class GrassImports:
    """Conteneur pour les imports dynamiques des modules GRASS."""

    def __init__(self):
        self.grass: Any = None   # Module grass.script
        self.gsetup: Any = None  # Module grass.script.setup
        self.GrassError: Optional[type] = None  # Classe d'exception GRASS


def init_grass_modules(grass_python_path: str, logger) -> GrassImports:
    """Importe les modules Python de GRASS depuis le chemin spécifié."""
    normalized_path = os.path.normpath(grass_python_path)
    sys.path = [p for p in sys.path if os.path.normpath(p) != normalized_path]

    if normalized_path not in [os.path.normpath(p) for p in sys.path]:
        sys.path.insert(0, normalized_path)
        logger.info("Ajout à sys.path : %s", normalized_path)

    try:
        grass = importlib.import_module("grass.script")
        gsetup = importlib.import_module("grass.script.setup")
        try:
            GrassError = importlib.import_module("grass.exceptions").GrassError  # type: ignore[attr-defined]
        except Exception:
            GrassError = Exception
            logger.warning("Fallback Exception pour GrassError (grass.exceptions indisponible).")

        gi = GrassImports()
        gi.grass = grass
        gi.gsetup = gsetup
        gi.GrassError = GrassError
        logger.info("Modules GRASS importés avec succès.")
        return gi

    except Exception as e:
        logger.critical("Échec de l'import des modules GRASS : %s", e)
        raise


def _deduire_gisbase_depuis_module_grass(gi: GrassImports) -> str:
    """Déduit le chemin GISBASE à partir du module grass.script."""
    script_file = getattr(gi.grass, "__file__", None)
    if not script_file:
        raise RuntimeError("Impossible de localiser le module 'grass.script'.")

    path = os.path.dirname(script_file)
    for _ in range(15):
        head, tail = os.path.split(path)
        if tail.lower() == "etc":
            gisbase = head
            if os.path.isdir(gisbase):
                return gisbase
            break
        if not head or head == path:
            break
        path = head

    raise RuntimeError("Structure des modules GRASS inattendue - impossible de déduire GISBASE.")


def initialiser_grass(
    gi: GrassImports,
    grass_cmd: str,
    gisdb_path: str,
    location_name: str,
    mapset_name: str,
    epsg_code: int,
    logger,
) -> None:
    """Initialise une session GRASS avec création si nécessaire."""
    os.makedirs(gisdb_path, exist_ok=True)
    location_path = os.path.join(gisdb_path, location_name)

    if not os.path.isdir(location_path):
        logger.info("Création de la LOCATION GRASS : %s", location_path)
        cmd = [grass_cmd, "--text", "-c", f"EPSG:{epsg_code}", location_path]
        subprocess.run(
            cmd, input="exit\n", check=True, capture_output=True, text=True, timeout=300
        )
    else:
        logger.info("LOCATION existante détectée : %s", location_name)

    gisbase = _deduire_gisbase_depuis_module_grass(gi)
    os.environ["GISBASE"] = gisbase
    grass_bin = os.path.join(gisbase, "bin")
    os.environ["PATH"] = f"{grass_bin}{os.pathsep}{os.environ.get('PATH', '')}"

    # Réduction maximale de la verbosité (supprime les 'ATTENTION')
    os.environ["GRASS_VERBOSE"] = "0"  # 0 = erreurs seules

    gi.gsetup.init(gisdb_path, location_name, mapset_name)
    try:
        gi.grass.run_command("g.gisenv", set="VERBOSE=0", quiet=True)
    except Exception:
        pass

    logger.info("Session GRASS initialisée : %s/%s", location_name, mapset_name)
