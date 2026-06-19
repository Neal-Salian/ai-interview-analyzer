"""
Unit tests for scoring_utils.py

Tests all the shared utility functions used by the metric plugins.
"""

import pytest
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    keyword_density_confidence,
    remove_outliers_iqr,
    ema_smooth,
    SignalComponent,
)


# ── confidence_weighted_average ──────────────────────────────────────────────

class TestConfidenceWeightedAverage:
    def test_empty_components(self):
        result = confidence_weighted_average([])
        assert result["final_score"] == 0
        assert result["raw_score"] == 0
        assert result["overall_confidence"] == 0.0
        assert result["confidence_details"] == []

    def test_single_component(self):
        components = [
            SignalComponent(score=80, confidence=0.9, signal_name="test"),
        ]
        result = confidence_weighted_average(components)
        assert result["final_score"] == 80
        assert result["raw_score"] == 80
        assert result["overall_confidence"] == 0.9
        assert len(result["confidence_details"]) == 1
        assert result["confidence_details"][0]["weight_applied"] == 1.0

    def test_equal_confidence_equals_simple_average(self):
        components = [
            SignalComponent(score=60, confidence=0.8, signal_name="a"),
            SignalComponent(score=80, confidence=0.8, signal_name="b"),
        ]
        result = confidence_weighted_average(components)
        assert result["final_score"] == 70  # (60+80)/2
        assert result["raw_score"] == 70

    def test_high_confidence_dominates(self):
        components = [
            SignalComponent(score=90, confidence=0.9, signal_name="reliable"),
            SignalComponent(score=30, confidence=0.1, signal_name="noisy"),
        ]
        result = confidence_weighted_average(components)
        # Weighted: (90*0.9 + 30*0.1) / (0.9+0.1) = (81+3)/1.0 = 84
        assert result["final_score"] == 84
        # Raw: (90+30)/2 = 60
        assert result["raw_score"] == 60

    def test_low_confidence_dropped(self):
        """Components with confidence < min_confidence are dropped entirely."""
        components = [
            SignalComponent(score=80, confidence=0.8, signal_name="good"),
            SignalComponent(score=10, confidence=0.05, signal_name="junk"),
        ]
        result = confidence_weighted_average(components, min_confidence=0.1)
        assert result["final_score"] == 80  # junk dropped
        assert len(result["confidence_details"]) == 1

    def test_all_below_min_confidence(self):
        components = [
            SignalComponent(score=50, confidence=0.05, signal_name="a"),
            SignalComponent(score=60, confidence=0.03, signal_name="b"),
        ]
        result = confidence_weighted_average(components, min_confidence=0.1)
        assert result["final_score"] == 0
        assert result["overall_confidence"] == 0.0

    def test_all_zero_confidence(self):
        components = [
            SignalComponent(score=80, confidence=0.0, signal_name="a"),
        ]
        result = confidence_weighted_average(components)
        assert result["final_score"] == 0

    def test_score_clamping(self):
        components = [
            SignalComponent(score=150, confidence=1.0, signal_name="over"),
        ]
        result = confidence_weighted_average(components)
        assert result["final_score"] == 100

    def test_weight_distribution(self):
        components = [
            SignalComponent(score=100, confidence=0.6, signal_name="a"),
            SignalComponent(score=0, confidence=0.4, signal_name="b"),
        ]
        result = confidence_weighted_average(components)
        details = result["confidence_details"]
        assert len(details) == 2
        assert details[0]["weight_applied"] == 0.6
        assert details[1]["weight_applied"] == 0.4


# ── sample_size_confidence ───────────────────────────────────────────────────

class TestSampleSizeConfidence:
    def test_below_minimum(self):
        assert sample_size_confidence(3, 10, 50) == 0.0

    def test_at_minimum(self):
        assert sample_size_confidence(10, 10, 50) == 0.0

    def test_at_ideal(self):
        assert sample_size_confidence(50, 10, 50) == 1.0

    def test_above_ideal(self):
        assert sample_size_confidence(100, 10, 50) == 1.0

    def test_midpoint(self):
        result = sample_size_confidence(30, 10, 50)
        assert result == 0.5

    def test_quarter(self):
        result = sample_size_confidence(20, 10, 50)
        assert result == 0.25


# ── keyword_density_confidence ───────────────────────────────────────────────

class TestKeywordDensityConfidence:
    def test_below_min_words(self):
        assert keyword_density_confidence(5, 30, min_words=50) == 0.0

    def test_at_ideal_words_with_hits(self):
        result = keyword_density_confidence(5, 200, min_words=50, ideal_words=200)
        assert result == 1.0  # length_conf=1.0, hit_boost capped

    def test_no_hits_but_long_text(self):
        result = keyword_density_confidence(0, 200, min_words=50, ideal_words=200)
        assert result == 1.0  # pure length confidence

    def test_some_hits_short_text(self):
        result = keyword_density_confidence(3, 100, min_words=50, ideal_words=200)
        # length_conf = (100-50)/(200-50) = 50/150 ≈ 0.333
        # hit_boost = min(3/3, 1.0) * 0.2 = 0.2
        # total = 0.333 + 0.2 = 0.533
        assert 0.5 <= result <= 0.6


# ── remove_outliers_iqr ──────────────────────────────────────────────────────

class TestRemoveOutliersIQR:
    def test_too_few_values(self):
        values = [1.0, 2.0, 100.0]
        result = remove_outliers_iqr(values)
        assert result == values  # unchanged

    def test_removes_extreme_outlier(self):
        values = [10.0, 12.0, 11.0, 13.0, 10.5, 12.5, 11.5, 100.0]
        result = remove_outliers_iqr(values)
        assert 100.0 not in result
        assert len(result) < len(values)

    def test_no_outliers(self):
        values = [5.0, 6.0, 5.5, 6.5, 5.2, 6.3, 5.8, 6.1]
        result = remove_outliers_iqr(values)
        assert len(result) == len(values)

    def test_empty_list(self):
        assert remove_outliers_iqr([]) == []

    def test_preserves_order(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = remove_outliers_iqr(values)
        assert result == values


# ── ema_smooth ───────────────────────────────────────────────────────────────

class TestEmaSmooth:
    def test_empty(self):
        assert ema_smooth([]) == []

    def test_single_value(self):
        assert ema_smooth([42.0]) == [42.0]

    def test_smoothing_reduces_spikes(self):
        # A spike at position 2 should be dampened
        values = [10.0, 10.0, 100.0, 10.0, 10.0]
        result = ema_smooth(values, alpha=0.3)
        # The spike should be significantly dampened
        assert result[2] < 100.0
        assert result[2] > 10.0

    def test_constant_series_unchanged(self):
        values = [5.0, 5.0, 5.0, 5.0]
        result = ema_smooth(values, alpha=0.3)
        for v in result:
            assert abs(v - 5.0) < 0.001

    def test_alpha_one_is_raw(self):
        values = [1.0, 2.0, 3.0, 4.0]
        result = ema_smooth(values, alpha=1.0)
        assert result == values

    def test_first_value_preserved(self):
        values = [42.0, 10.0, 20.0]
        result = ema_smooth(values, alpha=0.5)
        assert result[0] == 42.0
