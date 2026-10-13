import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "examples" / "sample_output.json"


def load_sample_output():
    with OUTPUT_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_sample_output_has_required_sections():
    output = load_sample_output()

    assert output["feature_name"]
    assert isinstance(output["scenarios"], list)
    assert isinstance(output["test_cases"], list)
    assert output["scenarios"]
    assert output["test_cases"]


def test_scenario_ids_are_unique():
    output = load_sample_output()

    scenario_ids = [
        scenario["scenario_id"]
        for scenario in output["scenarios"]
    ]

    assert len(scenario_ids) == len(set(scenario_ids))


def test_test_case_ids_are_unique():
    output = load_sample_output()

    test_case_ids = [
        case["test_case_id"]
        for case in output["test_cases"]
    ]

    assert len(test_case_ids) == len(set(test_case_ids))


def test_each_test_case_references_an_existing_scenario():
    output = load_sample_output()

    scenario_ids = {
        scenario["scenario_id"]
        for scenario in output["scenarios"]
    }

    for case in output["test_cases"]:
        assert case["scenario_id"] in scenario_ids