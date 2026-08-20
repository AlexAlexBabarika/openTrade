from pathlib import Path

import yaml


COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def test_run_snapshots_use_the_persistent_app_data_volume() -> None:
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    service = compose["services"]["openquant"]

    assert service["environment"]["OPENQUANT_DATA_ROOT"] == "/app/data"
    assert "app_data:/app/data" in service["volumes"]
