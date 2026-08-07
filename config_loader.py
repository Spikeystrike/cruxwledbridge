import importlib
import sys


def load_config():
    try:
        return importlib.import_module("config.config")
    except ModuleNotFoundError as exc:
        if exc.name not in {"config", "config.config"}:
            raise

        print(
            "ERROR: config/config.py is missing. "
            "Copy config/config.example.py to config/config.py, configure it, "
            "and then start the bridge again.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


config = load_config()
