"""
Tests du module de qualité des données (src/data_quality.py).
Vérifie les contrôles de qualité formels.
"""

import pytest
import pandas as pd
from src.data_quality import (
    check_null_rate,
    check_uniqueness,
    check_referential_integrity,
    check_value_range,
    run_quality_checks,
)
from src.transform import transform_orders, transform_customers


class TestCheckNullRate:
    """Tests du contrôle de taux de nulls."""

    def test_passes_when_below_threshold(self):
        df = pd.DataFrame({"col": [1, 2, None, 4, 5, 6, 7, 8, 9, 10]})  # 10%
        result = check_null_rate(df, "col", threshold_pct=10.0)
        assert result["passed"] is True
        assert result["null_pct"] == 10.0

    def test_fails_when_above_threshold(self):
        df = pd.DataFrame({"col": [None, None, None, 4, 5]})  # 60%
        result = check_null_rate(df, "col", threshold_pct=10.0)
        assert result["passed"] is False
        assert result["null_pct"] == 60.0

    def test_passes_with_no_nulls(self):
        df = pd.DataFrame({"col": [1, 2, 3, 4, 5]})
        result = check_null_rate(df, "col", threshold_pct=0)
        assert result["passed"] is True
        assert result["null_count"] == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame({"col": pd.Series([], dtype=float)})
        result = check_null_rate(df, "col", threshold_pct=5.0)
        assert result["null_pct"] == 0.0


class TestCheckUniqueness:
    """Tests du contrôle d'unicité."""

    def test_passes_with_unique_keys(self):
        df = pd.DataFrame({"id": ["A", "B", "C"]})
        result = check_uniqueness(df, ["id"])
        assert result["passed"] is True
        assert result["n_duplicates"] == 0

    def test_fails_with_duplicates(self):
        df = pd.DataFrame({"id": ["A", "B", "A"]})
        result = check_uniqueness(df, ["id"])
        assert result["passed"] is False
        assert result["n_duplicates"] == 1

    def test_composite_key_uniqueness(self):
        df = pd.DataFrame({
            "order_id": ["ORD1", "ORD1", "ORD2"],
            "item_id": [1, 2, 1],  # Composite key is unique
        })
        result = check_uniqueness(df, ["order_id", "item_id"])
        assert result["passed"] is True

    def test_composite_key_with_duplicates(self):
        df = pd.DataFrame({
            "order_id": ["ORD1", "ORD1"],
            "item_id": [1, 1],  # Same composite key → duplicate
        })
        result = check_uniqueness(df, ["order_id", "item_id"])
        assert result["passed"] is False


class TestCheckReferentialIntegrity:
    """Tests du contrôle d'intégrité référentielle."""

    def test_passes_when_all_keys_exist(self):
        parent = pd.DataFrame({"id": ["A", "B", "C"]})
        child = pd.DataFrame({"parent_id": ["A", "B", "A"]})
        result = check_referential_integrity(child, parent, "parent_id", "id")
        assert result["passed"] is True
        assert result["n_orphans"] == 0

    def test_fails_with_orphan_records(self):
        parent = pd.DataFrame({"id": ["A", "B"]})
        child = pd.DataFrame({"parent_id": ["A", "B", "C", "D"]})  # C et D sont orphelins
        result = check_referential_integrity(child, parent, "parent_id", "id")
        assert result["passed"] is False
        assert result["n_orphans"] == 2

    def test_orphan_percentage_correct(self):
        parent = pd.DataFrame({"id": ["A"]})
        child = pd.DataFrame({"parent_id": ["A", "B"]})  # 50% orphelins
        result = check_referential_integrity(child, parent, "parent_id", "id")
        assert result["orphan_pct"] == 50.0


class TestCheckValueRange:
    """Tests du contrôle de plage de valeurs."""

    def test_passes_with_valid_range(self):
        df = pd.DataFrame({"price": [0.0, 10.5, 100.0, 500.0]})
        result = check_value_range(df, "price", min_val=0)
        assert result["passed"] is True

    def test_fails_with_negative_values(self):
        df = pd.DataFrame({"price": [10.0, -5.0, 100.0]})
        result = check_value_range(df, "price", min_val=0)
        assert result["passed"] is False
        assert result["n_violations"] == 1

    def test_max_bound_violation(self):
        df = pd.DataFrame({"score": [1, 3, 6, 4]})  # 6 > max=5
        result = check_value_range(df, "score", min_val=1, max_val=5)
        assert result["passed"] is False
        assert result["n_violations"] == 1

    def test_ignores_nan_values(self):
        df = pd.DataFrame({"price": [10.0, None, 20.0]})
        result = check_value_range(df, "price", min_val=0)
        assert result["passed"] is True  # NaN ignorés


class TestRunQualityChecks:
    """Tests du rapport global de qualité."""

    def test_returns_complete_report(self, sample_orders, sample_customers):
        """Le rapport doit contenir les clés attendues."""
        orders_clean, orders_rej = transform_orders(sample_orders)
        customers_clean, customers_rej = transform_customers(sample_customers)

        transformed_data = {
            "orders": (orders_clean, orders_rej),
            "customers": (customers_clean, customers_rej),
        }
        report = run_quality_checks(transformed_data)

        assert "timestamp" in report
        assert "checks" in report
        assert "n_passed" in report
        assert "n_failed" in report
        assert "datasets" in report

    def test_dataset_metrics_present(self, sample_orders, sample_customers):
        """Les métriques par dataset doivent être présentes."""
        orders_clean, orders_rej = transform_orders(sample_orders)
        customers_clean, customers_rej = transform_customers(sample_customers)

        transformed_data = {
            "orders": (orders_clean, orders_rej),
            "customers": (customers_clean, customers_rej),
        }
        report = run_quality_checks(transformed_data)

        assert "orders" in report["datasets"]
        assert "customers" in report["datasets"]
        assert "rows_clean" in report["datasets"]["orders"]
        assert "rows_rejected" in report["datasets"]["orders"]

    def test_rejection_rate_calculation(self, sample_orders):
        """Le taux de rejet doit être calculé correctement."""
        orders_clean, orders_rej = transform_orders(sample_orders)
        transformed_data = {"orders": (orders_clean, orders_rej)}
        report = run_quality_checks(transformed_data)

        total = report["datasets"]["orders"]["rows_clean"] + report["datasets"]["orders"]["rows_rejected"]
        expected_rate = round(report["datasets"]["orders"]["rows_rejected"] / total * 100, 2)
        assert report["datasets"]["orders"]["rejection_rate_pct"] == expected_rate
