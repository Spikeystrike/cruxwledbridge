import importlib
import shutil
import sys
from pathlib import Path


APP_CONFIG_DIR = Path(__file__).resolve().parent / "config"
BUNDLED_CONFIG_DIR = Path("/code/config")
EXAMPLE_WLED_CONTROLLER = {"ip": "192.0.2.10", "start": 0, "end": 399}


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


def validate_config(config_module):
    errors = []

    token = getattr(config_module, "token", None)
    if not isinstance(token, str) or not token.strip():
        errors.append("token is empty")

    wled_controllers = getattr(config_module, "wled_controllers", None)
    if wled_controllers == [EXAMPLE_WLED_CONTROLLER]:
        errors.append("wled_controllers still contains the example controller 192.0.2.10")

    if errors:
        print(
            "ERROR: config/config.py still contains unconfigured example values: "
            + "; ".join(errors)
            + ". Edit config/config.py and restart the bridge.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return config_module


def load_config():
    try:
        loaded_config = importlib.import_module("config.config")
    except ModuleNotFoundError as exc:
        if exc.name not in {"config", "config.config"}:
            raise

        if initialize_config() is not None:
            importlib.invalidate_caches()
            try:
                loaded_config = importlib.import_module("config.config")
            except ModuleNotFoundError as retry_exc:
                if retry_exc.name not in {"config", "config.config"}:
                    raise
            else:
                return validate_config(loaded_config)

        print(
            "ERROR: config/config.py is missing. "
            "No config.py or config.example.py is available to initialize it.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    return validate_config(loaded_config)


config = load_config()
