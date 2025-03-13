"""
API configuration module
"""

# Standard library imports
import json
from pathlib import Path
from typing import Any, Dict


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, "rt", encoding="utf-8") as config_file:
        return json.load(config_file)
