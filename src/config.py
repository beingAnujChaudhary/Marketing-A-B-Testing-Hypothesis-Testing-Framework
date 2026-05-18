"""Configuration management with simple singleton caching.

Design note: Thread-safe locking is intentionally omitted here.
Notebooks and scripts are single-process, so simple caching is sufficient.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

_config_cache: Dict[str, Any] = None


def load_config(config_path: str = "configs/experiment_config.yaml") -> Dict[str, Any]:
    """Load YAML config file with caching to avoid re-reading.

    Args:
        config_path: Relative or absolute path to the YAML config file.

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    logger.info("✅ Configuration loaded from %s", config_path)
    return _config_cache


def get_config() -> Dict[str, Any]:
    """Convenience function to get config from anywhere in the codebase."""
    return load_config()


def reset_config() -> None:
    """Reset the cache — required between tests to ensure a fresh config load."""
    global _config_cache
    _config_cache = None