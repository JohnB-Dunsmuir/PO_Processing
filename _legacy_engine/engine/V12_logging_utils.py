# engine/V12_logging_utils.py
import logging
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_LOGS = BASE_DIR / "00_Logs"


def setup_logger(name: str = "V12_engine") -> logging.Logger:
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fpath = DIR_LOGS / f"{name}_{ts}.log"

    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    fh = logging.FileHandler(fpath, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)

    log.addHandler(fh)
    log.addHandler(sh)

    log.info("Logging to: %s", fpath)
    return log
