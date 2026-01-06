"""
V12_main.py
Entry point for the V12 PO PDF processing pipeline.
"""

import logging
from engine.V12_parser_engine import process_all_pdfs


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("V12_MAIN")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def main() -> None:
    log = _build_logger()
    process_all_pdfs(log=log)


if __name__ == "__main__":
    main()
