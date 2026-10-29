"""
OpenFX Research Lab entry point.
"""
import json
import logging
import platform
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

for directory in (DATA_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "research.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("openfx")


def get_system_status():
    """Return basic runtime and project information."""
    return {
        "project": "OpenFX Research Lab",
        "short_name": "OpenFX",
        "status": "research_scaffold",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "data_directory": str(DATA_DIR),
        "log_directory": str(LOG_DIR),
        "mt5_available": False,
        "trading_enabled": False,
    }


def main():
    status = get_system_status()
    logger.info("OpenFX startup")
    logger.info("Project status: %s", status["status"])
    print(json.dumps(status, indent=2, ensure_ascii=False))
    logger.info(
        "Research scaffold loaded. No MT5 terminal, broker connection, "
        "market-data pipeline, or backtest has been started."
    )


if __name__ == "__main__":
    main()
