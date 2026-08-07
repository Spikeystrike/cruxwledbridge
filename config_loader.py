import importlib
import shutil
import sys
from pathlib import Path


APP_CONFIG_DIR = Path(__file__).resolve().parent / "config"
BUNDLED_CONFIG_DIR = Path("/code/config")


def initialize_config(config_dir=APP_CONFIG_DIR, bundled_config_dir=BUNDLED_CONFIG_DIR):
    target = config_dir / "config.py"
    if target.is_file():
        return target

    for filename in ("config.py", "config.example.py"):
        source = bundled_config_dir / filename
        if not source.is_file():
            continue

        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as exc:
            print(
                f"ERROR: could not copy {source} to {target}: {exc}",
                file=sys.stderr,
            )
            raise SystemExit(1) from None

        print(f"Initialized {target} from {source}.", file=sys.stderr)
        return target

    return None


def load_config():
    try:
        return importlib.import_module("config.config")
    except ModuleNotFoundError as exc:
        if exc.name not in {"config", "config.config"}:
            raise

        if initialize_config() is not None:
            importlib.invalidate_caches()
            try:
                return importlib.import_module("config.config")
            except ModuleNotFoundError as retry_exc:
                if retry_exc.name not in {"config", "config.config"}:
                    raise

        print(
            "ERROR: config/config.py is missing. "
            "No config.py or config.example.py is available to initialize it.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


config = load_config()
