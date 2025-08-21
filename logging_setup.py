# ─────────────────────────────────────────────────────────────────────────────
# hydro_pipeline/logging_setup.py
# ─────────────────────────────────────────────────────────────────────────────
"""Politique générale de journalisation.

Ce module centralise la configuration des logs pour l'ensemble du pipeline.
Il garantit une journalisation structurée, horodatée et adaptée aux besoins
scientifiques (traçabilité, reproductibilité, intégration dans les rapports).

Fonction publique
-----------------
setup_logging(level=logging.INFO)
    Configure et retourne le logger principal du projet.
"""

from __future__ import annotations
import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Initialise et retourne le logger principal du pipeline hydro.

    La configuration applique :
    * Un format standard avec horodatage et niveau de log
    * Une sortie vers stdout (compatible avec les environnements conteneurisés)
    * Un niveau de log paramétrable.

    Notes
    -----
    L'appel à basicConfig est idempotent : une seconde invocation ne modifie pas
    la configuration existante sauf si force=True est spécifié.

    Paramètres
    ----------
    level : int, optionnel
        Niveau minimal de journalisation (par défaut : logging.INFO).

    Retour
    ------
    logging.Logger
        Instance configurée du logger nommé 'hydro_pipeline'.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True  # S'assure de surcharger toute config existante
    )

    logger = logging.getLogger("hydro_pipeline")
    logger.debug("Logger hydro_pipeline configuré avec niveau %s", logging.getLevelName(level))

    return logger