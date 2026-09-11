"""Configuration settings for RedactGov sovereign redaction engine."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class Settings:
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    SYNTHETIC_DIR: Path = DATA_DIR / "synthetic_corpus"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    MODELS_DIR: Path = PROJECT_ROOT / "models"

    # Google Gemma Configuration (Targeting Google Gemma 4 E4B Edge Model)
    GEMMA_MODEL_NAME: str = "google/gemma-4-e4b-it-GGUF"
    GEMMA_DEFAULT_GGUF_FILE: str = "gemma-4-e4b-it-Q4_K_M.gguf"
    GEMMA_CONTEXT_WINDOW: int = 8192
    GEMMA_TEMPERATURE: float = 0.1
    GEMMA_GPU_LAYERS: int = -1 if os.uname().sysname == "Darwin" else 0  # Metal acceleration on macOS

    # Deterministic engine settings
    ENABLE_DETERMINISTIC_FAST_PATH: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 0.75

    # PikePDF stream surgery settings
    ERADICATE_METADATA: bool = True
    REWRITE_GLYPH_STREAMS: bool = True
    BURN_OPAQUE_POLYGONS: bool = True

    def __post_init__(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
