import pandas as pd
import pytest
from fpl_engine.analytics import (
    calculate_z_score, calculate_roi, predict_price_change,
    get_fixture_label, calculate_price_pressure_ci
)


# ── Z-SCORE ──

def test_z_score_normal_case():
    df = pd.DataFrame({'transfers_in': [100, 200, 300]})
    result = calculate_z_score(df)
    assert 'z_score' in result.columns
    # mean=200, std≈100 → middle value should have z_score ≈ 0
    assert result.loc[result['transfers_in'] == 200, 'z_score'].iloc[0] == pytest.approx(0, abs=1e-6)


def test_z_score_zero_variance():
    # All players have identical transfers_in (off-season case)
    df = pd.DataFrame({'transfers_in': [0, 0, 0]})
    result = calculate_z_score(df)
    assert 'z_score' in result.columns
    assert (result['z_score'] == 0.0).all()


# ── ROI ──

def test_roi_calculation():
    df = pd.DataFrame({'total_points': [100, 50], 'now_cost': [10, 5]})
    result = calculate_roi(df)
    assert result['roi'].tolist() == [10.0, 10.0]


# ── PRICE PREDICTION ──

def test_predict_price_rise():
    result = predict_price_change(player_transfers_in=100000, player_transfers_out=0)
    assert result['prediction'] == 'rise'
    assert result['color'] == 'green'


def test_predict_price_fall():
    result = predict_price_change(player_transfers_in=0, player_transfers_out=100000)
    assert result['prediction'] == 'fall'
    assert result['color'] == 'red'


def test_predict_price_stable():
    result = predict_price_change(player_transfers_in=0, player_transfers_out=0)
    assert result['prediction'] == 'stable'
    assert result['pressure'] == 0


def test_pressure_capped_at_100():
    result = predict_price_change(player_transfers_in=10_000_000, player_transfers_out=0)
    assert result['pressure'] == 100


# ── FIXTURE LABELS ──

def test_fixture_label_easy():
    label, color = get_fixture_label(1.5)
    assert color == 'green'


def test_fixture_label_moderate():
    label, color = get_fixture_label(2.5)
    assert color == 'yellow'


def test_fixture_label_tough():
    label, color = get_fixture_label(4.0)
    assert color == 'red'


# ── PRICE PRESSURE CI ──

def test_ci_zero_transfers():
    result = calculate_price_pressure_ci(player_transfers_in=0)
    assert result['ci_low'] == 0.0
    assert result['ci_high'] == 0.0


def test_ci_bounds_valid():
    result = calculate_price_pressure_ci(player_transfers_in=60000)
    assert 0 <= result['ci_low'] <= result['ci_high'] <= 100


def test_ci_high_volume_capped():
    result = calculate_price_pressure_ci(player_transfers_in=10_000_000)
    assert result['ci_high'] == 100.0