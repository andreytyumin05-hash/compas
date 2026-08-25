"""
Общие настройки проекта.
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
GENERATED_DIR = SCRIPTS_DIR / "generated"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)
