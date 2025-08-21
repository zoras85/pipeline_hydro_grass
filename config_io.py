# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/config_io.py
# ─────────────────────────────────────────────────────────────────────────────
"""Gestion robuste des configurations YAML pour le pipeline hydrographique.

Ce module implémente la lecture/écriture sécurisée des fichiers de configuration
avec résolution des variables d'environnement et fusion intelligente des valeurs.
"""

from __future__ import annotations
from dataclasses import asdict
from typing import Any, Mapping, Dict
import os
import re
import logging
from pathlib import Path

try:
    import yaml
except ImportError as e:
    raise RuntimeError(
        "Le package PyYAML est requis pour ce module. "
        "Installez-le avec: pip install pyyaml"
    ) from e

from .config import Config

# Configuration du logger
logger = logging.getLogger(__name__)

# Pattern pour la détection des variables d'environnement
_ENV_VAR_PATTERN = re.compile(r"^\$\{env:([A-Za-z_][A-Za-z0-9_]*)}$")


class ConfigIOError(RuntimeError):
    """Exception personnalisée pour les erreurs de gestion de configuration."""
    pass


def _resolve_env_vars(value: Any) -> Any:
    """Résout les variables d'environnement dans les valeurs de configuration.

    Args:
        value: Valeur à analyser (peut être de n'importe quel type)

    Returns:
        La valeur originale ou la valeur résolue depuis l'environnement

    Note:
        Seules les chaînes au format exact ${env:VAR} sont résolues.
        Les autres valeurs sont retournées inchangées.
    """
    if isinstance(value, str):
        match = _ENV_VAR_PATTERN.match(value.strip())
        if match:
            env_var = match.group(1)
            resolved_value = os.getenv(env_var, "")
            logger.debug(f"Résolution variable d'environnement: {env_var} -> {resolved_value}")
            return resolved_value
    return value


def _load_single_config(file_path: str) -> Dict[str, Any]:
    """Charge un fichier YAML et résout ses variables d'environnement.

    Args:
        file_path: Chemin vers le fichier YAML

    Returns:
        Dictionnaire contenant la configuration lue

    Raises:
        ConfigIOError: Si le fichier est inaccessible ou invalide
    """
    try:
        path = Path(file_path).absolute()
        logger.info(f"Chargement configuration depuis: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f) or {}

        return {
            key: _resolve_env_vars(value)
            for key, value in raw_config.items()
        }

    except yaml.YAMLError as e:
        error_msg = f"Erreur de syntaxe YAML dans {file_path}: {str(e)}"
        logger.error(error_msg)
        raise ConfigIOError(error_msg) from e
    except OSError as e:
        error_msg = f"Erreur d'accès au fichier {file_path}: {str(e)}"
        logger.error(error_msg)
        raise ConfigIOError(error_msg) from e


def _is_valid_config_value(value: Any) -> bool:
    """Détermine si une valeur de configuration est considérée comme valide.

    Args:
        value: Valeur à évaluer

    Returns:
        True si la valeur est non-nulle et non-vide, False sinon

    Note:
        Une valeur est considérée valide si :.
        * Elle n'est pas None
        * Pour les strings: non vide après strip()
        * Pour les collections (list, dict, set) : non vides
    """
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict, set)) and not value:
        return False
    return True


def merge_configs(
        user_config: Mapping[str, Any],
        default_config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Fusionne deux configurations selon la politique 'empty-is-missing'.

    Args:
        user_config: Configuration utilisateur (prioritaire)
        default_config: Configuration par défaut (fallback)

    Returns:
        Dictionnaire contenant la configuration fusionnée

    Raises:
        ConfigIOError: Si la fusion échoue

    Note:
        Pour chaque clé, la valeur d'user_config est utilisée si elle est valide
        (selon _is_valid_config_value), sinon la valeur de default_config est utilisée.
    """
    try:
        merged_config = {}
        all_keys = set(default_config.keys()) | set(user_config.keys())

        for key in all_keys:
            user_value = user_config.get(key)
            merged_config[key] = (
                user_value
                if _is_valid_config_value(user_value)
                else default_config.get(key)
            )

        logger.debug(f"Fusion config terminée. Clés fusionnées: {len(merged_config)}")
        return merged_config

    except Exception as e:
        error_msg = f"Erreur lors de la fusion des configurations: {str(e)}"
        logger.error(error_msg)
        raise ConfigIOError(error_msg) from e


def load_config_pair(
        user_config_path: str,
        default_config_path: str
) -> Config:
    """Charge et fusionne les configurations utilisateur et par défaut.

    Args:
        user_config_path: Chemin vers config.yaml (prioritaire)
        default_config_path: Chemin vers default_config.yaml (fallback)

    Returns:
        Instance de Config initialisée avec les valeurs fusionnées

    Raises:
        ConfigIOError: Si le chargement ou la fusion échoue
    """
    try:
        logger.info(
            f"Chargement paire de configurations:\n"
            f"- User: {user_config_path}\n"
            f"- Default: {default_config_path}"
        )

        default_config = _load_single_config(default_config_path)
        user_config = _load_single_config(user_config_path)

        merged = merge_configs(user_config, default_config)
        return Config(**merged)

    except Exception as e:
        error_msg = (
            f"Impossible de charger la configuration:\n"
            f"User: {user_config_path}\n"
            f"Default: {default_config_path}\n"
            f"Erreur: {str(e)}"
        )
        logger.error(error_msg)
        raise ConfigIOError(error_msg) from e


def save_config(
        config: Config,
        output_path: str,
        *,
        minimal_output: bool = True
) -> None:
    """Sauvegarde une configuration dans un fichier YAML.

    Args:
        config: Configuration à sauvegarder
        output_path: Chemin de destination
        minimal_output: Si True, n'inclut que les valeurs non-nulles

    Raises:
        ConfigIOError: Si l'écriture échoue
    """
    try:
        path = Path(output_path).absolute()
        logger.info(f"Sauvegarde configuration vers: {path}")

        config_dict = asdict(config)

        if minimal_output:
            config_dict = {
                k: v for k, v in config_dict.items()
                if _is_valid_config_value(v)
            }

        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                config_dict,
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False
            )

        logger.debug(f"Configuration sauvegardée avec succès. Taille: {path.stat().st_size} octets")

    except Exception as e:
        error_msg = f"Erreur lors de la sauvegarde vers {output_path}: {str(e)}"
        logger.error(error_msg)
        raise ConfigIOError(error_msg) from e


# Alias pour compatibilité ascendante
from_yaml_pair = load_config_pair
merge_config = merge_configs
save_editable_yaml = save_config