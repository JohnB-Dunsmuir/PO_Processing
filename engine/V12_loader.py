import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_PARSERS = BASE_DIR / "Parsers"


@dataclass
class V12ParserModule:
    name: str
    detect: Callable[[str], bool]
    parse: Callable[[str], Any]


def _find_detect_parse(mod, key: str) -> Tuple[Optional[Callable], Optional[Callable]]:
    exact_detect = getattr(mod, f"detect_{key}", None)
    exact_parse = getattr(mod, f"parse_{key}", None)
    if callable(exact_detect) and callable(exact_parse):
        return exact_detect, exact_parse

    detects = [getattr(mod, a) for a in dir(mod) if a.startswith("detect_") and callable(getattr(mod, a))]
    parses = [getattr(mod, a) for a in dir(mod) if a.startswith("parse_") and callable(getattr(mod, a))]

    if len(detects) == 1 and len(parses) == 1:
        return detects[0], parses[0]

    return None, None


def load_parsers(log) -> List[V12ParserModule]:
    modules: List[V12ParserModule] = []

    for f in sorted(DIR_PARSERS.glob("parser_*.py")):
        stem = f.stem
        key = stem.replace("parser_", "", 1)
        mname = f"Parsers.{stem}"

        try:
            mod = importlib.import_module(mname)
        except Exception as e:
            log.error("Failed to load %s: %s", f.name, e)
            continue

        detect, parse = _find_detect_parse(mod, key)

        if callable(detect) and callable(parse):
            modules.append(V12ParserModule(stem, detect, parse))
            log.info("Loaded parser: %s", stem)
        else:
            log.warning(
                "Skipping %s — detect_/parse_ functions not found (expected detect_%s / parse_%s)",
                f.name, key, key
            )

    return modules
