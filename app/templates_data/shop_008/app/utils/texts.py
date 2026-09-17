from functools import lru_cache
from pathlib import Path
import yaml


@lru_cache(maxsize=1)
def load_texts() -> dict:
    file_path = Path(__file__).resolve().parent.parent / "texts.yml"
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
