"""
Module de logging centralisé.
Utilise Loguru pour produire des logs structurés avec rotation automatique.
"""

import sys
from pathlib import Path
from loguru import logger as _logger
from datetime import datetime


def setup_logger(log_level: str = "INFO", log_dir: Path = None) -> None:
    """
    Configure le logger global Loguru.
    
    - Console : INFO et plus, format coloré.
    - Fichier  : DEBUG et plus, rotation quotidienne, rétention 30 jours.
    
    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR).
        log_dir:   Répertoire de stockage des fichiers de log.
    """
    _logger.remove()  # Supprimer les handlers par défaut

    # ── Handler console ────────────────────────────────────────────────────────
    _logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # ── Handler fichier ────────────────────────────────────────────────────────
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "pipeline_{time:YYYY-MM-DD}.log"

        _logger.add(
            str(log_file),
            level="DEBUG",
            rotation="00:00",     # Rotation à minuit
            retention="30 days",  # Conserver 30 jours
            compression="zip",
            encoding="utf-8",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                "{name}:{function}:{line} | {message}"
            ),
        )


def get_logger(name: str = __name__):
    """
    Retourne une instance du logger avec contexte.
    
    Args:
        name: Nom du module appelant.
        
    Returns:
        Logger Loguru contextualisé.
    """
    return _logger.bind(name=name)


# Logger global pré-configuré
logger = get_logger("retail_platform")
