"""
Tests du module de transformation (src/transform.py).
Vérifie les règles métier de nettoyage des données.
"""

import pytest
import pandas as pd
from src.transform import (
    transform_orders,
    transform_order_items,
    transform_customers,
    transform_products,
    transform_payments,
    transform_reviews,
)


class TestTransformOrders:
    """Tests des transformations sur le dataset orders."""

    def test_removes_duplicates(self, sample_orders):
        """Les doublons sur order_id doivent être éliminés."""
        df_clean, df_rejected = transform_orders(sample_orders)
        assert df_clean["order_id"].duplicated().sum() == 0

    def test_rejects_null_customer_id(self, sample_orders):
        """Les lignes sans customer_id doivent être rejetées."""
        df_clean, df_rejected = transform_orders(sample_orders)
        assert df_clean["customer_id"].isnull().sum() == 0

    def test_rejects_go_to_rejected_df(self, sample_orders):
        """Les lignes rejetées doivent apparaître dans df_rejected."""
        _, df_rejected = transform_orders(sample_orders)
        assert len(df_rejected) > 0

    def test_dates_converted_to_datetime(self, sample_orders):
        """Les colonnes de dates doivent être au format datetime."""
        df_clean, _ = transform_orders(sample_orders)
        assert pd.api.types.is_datetime64_any_dtype(df_clean["order_purchase_timestamp"])

    def test_delivery_days_calculated(self, sample_orders):
        """Le délai de livraison doit être calculé pour les commandes livrées."""
        df_clean, _ = transform_orders(sample_orders)
        delivered = df_clean[
            df_clean["order_delivered_customer_date"].notna()
            & df_clean["order_purchase_timestamp"].notna()
        ]
        assert "delivery_days" in df_clean.columns
        assert delivered["delivery_days"].notna().all()

    def test_delivery_days_positive(self, sample_orders):
        """Le délai de livraison doit être >= 0."""
        df_clean, _ = transform_orders(sample_orders)
        valid = df_clean["delivery_days"].dropna()
        assert (valid >= 0).all()

    def test_is_on_time_binary(self, sample_orders):
        """is_on_time doit être 0 ou 1 uniquement."""
        df_clean, _ = transform_orders(sample_orders)
        valid_values = df_clean["is_on_time"].dropna().unique()
        assert all(v in [0, 1] for v in valid_values)

    def test_on_time_order(self, sample_orders):
        """ORD001 livré le 25/01, estimé le 30/01 → doit être on_time=1."""
        df_clean, _ = transform_orders(sample_orders)
        ord001 = df_clean[df_clean["order_id"] == "ORD001"]
        assert ord001.iloc[0]["is_on_time"] == 1

    def test_late_order(self, sample_orders):
        """ORD002 livré le 05/03, estimé le 28/02 → doit être on_time=0 et delay_days > 0."""
        df_clean, _ = transform_orders(sample_orders)
        ord002 = df_clean[df_clean["order_id"] == "ORD002"]
        if not ord002.empty:
            assert ord002.iloc[0]["is_on_time"] == 0
            assert ord002.iloc[0]["delay_days"] > 0


class TestTransformOrderItems:
    """Tests des transformations sur le dataset order_items."""

    def test_rejects_negative_price(self, sample_order_items):
        """Les lignes avec price négatif doivent être rejetées."""
        df_clean, df_rejected = transform_order_items(sample_order_items)
        assert (df_clean["price"] >= 0).all()
        assert len(df_rejected) > 0

    def test_rejects_null_order_id(self):
        """Les lignes sans order_id doivent être rejetées."""
        df = pd.DataFrame({
            "order_id": [None, "ORD1"],
            "order_item_id": [1, 1],
            "product_id": ["P1", "P2"],
            "seller_id": ["S1", "S2"],
            "shipping_limit_date": ["2017-01-01", "2017-01-01"],
            "price": [10.0, 20.0],
            "freight_value": [2.0, 3.0],
        })
        df_clean, df_rejected = transform_order_items(df)
        assert df_clean["order_id"].isnull().sum() == 0
        assert len(df_rejected) == 1

    def test_clean_data_untouched(self, sample_order_items):
        """Les données valides ne doivent pas être altérées."""
        valid_rows = sample_order_items[sample_order_items["price"] >= 0].copy()
        df_clean, _ = transform_order_items(sample_order_items)
        assert len(df_clean) == len(valid_rows)


class TestTransformCustomers:
    """Tests des transformations sur le dataset customers."""

    def test_removes_duplicate_customers(self, sample_customers):
        """Les doublons sur customer_id doivent être supprimés."""
        df_clean, _ = transform_customers(sample_customers)
        assert df_clean["customer_id"].duplicated().sum() == 0

    def test_city_normalized_lowercase(self, sample_customers):
        """Les noms de villes doivent être en minuscules."""
        df_clean, _ = transform_customers(sample_customers)
        assert df_clean["customer_city"].str.islower().all()

    def test_state_normalized_lowercase(self, sample_customers):
        """Les états doivent être en minuscules."""
        df_clean, _ = transform_customers(sample_customers)
        assert df_clean["customer_state"].str.islower().all()


class TestTransformPayments:
    """Tests des transformations sur le dataset payments."""

    def test_rejects_negative_payment(self, sample_payments):
        """Les paiements négatifs doivent être rejetés."""
        df_clean, df_rejected = transform_payments(sample_payments)
        assert (df_clean["payment_value"] >= 0).all()
        assert len(df_rejected) > 0

    def test_valid_payments_retained(self, sample_payments):
        """Les paiements valides doivent être conservés."""
        df_clean, _ = transform_payments(sample_payments)
        valid_original = sample_payments[sample_payments["payment_value"] >= 0]
        assert len(df_clean) == len(valid_original)


class TestTransformProducts:
    """Tests des transformations sur le dataset products."""

    def test_removes_duplicate_products(self, sample_products):
        """Les doublons sur product_id doivent être supprimés."""
        df_dup = pd.concat([sample_products, sample_products.iloc[[0]]], ignore_index=True)
        df_clean, _ = transform_products(df_dup)
        assert df_clean["product_id"].duplicated().sum() == 0

    def test_category_translation_joined(self, sample_products):
        """Les traductions doivent être jointes si df_translations est fourni."""
        translations = pd.DataFrame({
            "product_category_name": ["cama_mesa_banho", "beleza_saude"],
            "product_category_name_english": ["bed_bath_table", "health_beauty"],
        })
        df_clean, _ = transform_products(sample_products, translations)
        assert "product_category_name_english" in df_clean.columns
        assert df_clean.loc[
            df_clean["product_category_name"] == "cama_mesa_banho",
            "product_category_name_english",
        ].iloc[0] == "bed_bath_table"

    def test_numeric_columns_coerced(self, sample_products):
        """Les colonnes numériques invalides doivent être converties en NaN."""
        df = sample_products.copy()
        df["product_weight_g"] = df["product_weight_g"].astype(object)
        df.loc[0, "product_weight_g"] = "invalid"
        df_clean, _ = transform_products(df)
        assert pd.api.types.is_float_dtype(df_clean["product_weight_g"])
