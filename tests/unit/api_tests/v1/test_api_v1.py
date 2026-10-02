import os

import pytest
from fastapi.testclient import TestClient

import api.v1.api as api

expected_prediction_key = "power_kw"
expected_dict_keys = ["timestamp", "predictions"]
prediction_key = expected_dict_keys[1]
expected_number_of_values = 192
expected_response_on_wrong_types = {
    "detail": [
        {
            "loc": ["body", "site", "latitude"],
            "msg": "Input should be less than or equal to 90",
            "type": "less_than_equal",
            "input": 91,
            "ctx": {"le": 90.0},
        },
        {
            "loc": ["body", "site", "longitude"],
            "msg": "Input should be greater than or equal to -180",
            "type": "greater_than_equal",
            "input": -181,
            "ctx": {"ge": -180.0},
        },
        {
            "loc": ["body", "site", "capacity_kwp"],
            "msg": "Input should be greater than or equal to 0",
            "type": "greater_than_equal",
            "input": -1,
            "ctx": {"ge": 0.0},
        },
        {
            "loc": ["body", "site", "tilt"],
            "msg": "Input should be less than or equal to 90",
            "type": "less_than_equal",
            "input": 91,
            "ctx": {"le": 90.0},
        },
        {
            "loc": ["body", "site", "orientation"],
            "msg": "Input should be less than or equal to 360",
            "type": "less_than_equal",
            "input": 361,
            "ctx": {"le": 360.0},
        },
    ]
}


@pytest.fixture
def client():
    return TestClient(api.app)


@pytest.fixture
def body():
    return {
        "site": {
            "latitude": -90,
            "longitude": -180,
            "capacity_kwp": 0,
            "tilt": 35,
            "orientation": 180,
            "inverter_type": "string",
        },
        "timestamp": "2021-01-26 01:15:00",
        "live_generation": [
            {
                "timestamp": "2021-01-26 01:10:00",
                "generation": 0.0
            }
        ]
    }


@pytest.fixture
def body_short():
    return {
        "site": {
            "latitude": -90,
            "longitude": -180,
            "capacity_kwp": 0,
        },
        "timestamp": "2021-01-26 01:15:00",
    }


@pytest.fixture
def body_wrong():
    return {
        "site": {
            "latitude": 91,
            "longitude": -181,
            "capacity_kwp": -1,
            "tilt": 91,
            "orientation": 361,
            "inverter_type": "string",
        },
        "timestamp": "2021-01-26 01:15:00",
    }


@pytest.fixture
def bad_redirect_url(client):
    return "url"


@pytest.fixture
def bad_redirect_url_correct_param(client):
    return "url?code=code"


def test_api_ok(client, body, monkeypatch, mock_run_forecast):
    monkeypatch.setattr(api, "run_forecast", mock_run_forecast)

    response = client.post("/forecast/", json=body)
    response_body = response.json()
    assert response.status_code == 200
    assert isinstance(response_body[prediction_key][expected_prediction_key], dict)
    assert all(
        [key in response_body.keys() for key in expected_dict_keys]
    ), "Expected dictonary key is missing"
    assert (
        len(response_body[prediction_key][expected_prediction_key]) == expected_number_of_values
    ), "Expected number of values is wrong"


def test_api_ok_short(client, body_short, monkeypatch, mock_run_forecast):
    monkeypatch.setattr(api, "run_forecast", mock_run_forecast)

    response = client.post("/forecast/", json=body_short)
    response_body = response.json()

    assert response.status_code == 200
    assert isinstance(response_body[prediction_key][expected_prediction_key], dict)
    assert all(
        [key in response_body.keys() for key in expected_dict_keys]
    ), "Expected dictonary key is missing"
    assert len(response_body[prediction_key][expected_prediction_key]) == expected_number_of_values


def test_api_wrong_body(client, body_wrong):
    # Tests all wrong data types responses
    response = client.post("/forecast/", json=body_wrong)
    response_body = response.json()

    assert response.status_code == 422
    assert response_body == expected_response_on_wrong_types

