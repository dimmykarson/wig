import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)
CONFIG_FILE = Path("config.json")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception as exc:
        log.warning("Erro ao ler config.json: %s", exc)
        return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        log.warning("Erro ao salvar config.json: %s", exc)
