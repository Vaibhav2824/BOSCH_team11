import json
from pathlib import Path

import yaml

from oncall.schema import Diagnosis

ROOT = Path(__file__).parents[1]


def test_sample_bundle_and_diagnosis_are_readable():
    bundle = ROOT / "bundles" / "sample"
    telemetry = json.loads((bundle / "telemetry.json").read_text())
    diagnosis = Diagnosis.model_validate(json.loads((bundle / "diagnosis.json").read_text()))

    assert telemetry["schema"] == "telemetry-bundle-v0"
    assert telemetry["incident_id"] == "sample"
    assert diagnosis.decision == "diagnosed"


def test_every_practice_bundle_has_telemetry():
    practice = yaml.safe_load((ROOT / "eval" / "practice.yaml").read_text())
    assert len(practice["incidents"]) == 10
    for incident in practice["incidents"]:
        telemetry = json.loads((ROOT / incident["bundle"] / "telemetry.json").read_text())
        assert telemetry["incident_id"] == incident["id"]
        for key in ("traces", "logs", "containers"):
            assert telemetry[key], f"{incident['id']}: empty {key}"
        services = {s["service"] for s in telemetry["metrics"]["services"]}
        container_names = {c["service"] for c in telemetry["containers"]}
        assert incident["expected_component"] in services | container_names
