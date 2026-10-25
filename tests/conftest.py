"""
Configuration pytest & fixtures partagées.
"""

import pytest
import pandas as pd
from datetime import datetime


# ── Fixtures : données de test ─────────────────────────────────────────────────

@pytest.fixture
def sample_orders():
    """Jeu de données orders minimal pour les tests."""
    return pd.DataFrame({
        "order_id": ["ORD001", "ORD002", "ORD003", "ORD001"],  # ORD001 dupliqué
        "customer_id": ["CUST1", "CUST2", "CUST3", None],      # None → rejet
        "order_status": ["delivered", "shipped", "canceled", "delivered"],
        "order_purchase_timestamp": [
            "2017-01-15 10:00:00",
            "2017-02-20 14:30:00",
            "2017-03-05 09:00:00",
            "2017-01-15 10:00:00",
        ],
        "order_approved_at": [
            "2017-01-15 11:00:00",
            "2017-02-20 15:00:00",
            None,
            "2017-01-15 11:00:00",
        ],
        "order_delivered_carrier_date": [
            "2017-01-18 08:00:00",
            "2017-02-25 10:00:00",
            None,
            "2017-01-18 08:00:00",
        ],
        "order_delivered_customer_date": [
            "2017-01-25 16:00:00",
            "2017-03-05 12:00:00",
            None,
            "2017-01-25 16:00:00",
        ],
        "order_estimated_delivery_date": [
            "2017-01-30 00:00:00",
            "2017-02-28 00:00:00",
            "2017-03-20 00:00:00",
            "2017-01-30 00:00:00",
        ],
    })


@pytest.fixture
def sample_order_items():
    """Jeu de données order_items minimal."""
    return pd.DataFrame({
        "order_id": ["ORD001", "ORD001", "ORD002", "ORD003"],
        "order_item_id": [1, 2, 1, 1],
        "product_id": ["PROD1", "PROD2", "PROD1", "PROD3"],
        "seller_id": ["SELL1", "SELL1", "SELL2", "SELL1"],
        "shipping_limit_date": [
            "2017-01-20 00:00:00",
            "2017-01-20 00:00:00",
            "2017-02-27 00:00:00",
            "2017-03-10 00:00:00",
        ],
        "price": [150.00, 75.50, -10.00, 200.00],  # -10 → rejet
        "freight_value": [15.00, 10.00, 5.00, 20.00],
    })


@pytest.fixture
def sample_customers():
    """Jeu de données customers minimal."""
    return pd.DataFrame({
        "customer_id": ["CUST1", "CUST2", "CUST3", "CUST1"],  # CUST1 dupliqué
        "customer_unique_id": ["UNIQ1", "UNIQ2", "UNIQ3", "UNIQ1"],
        "customer_zip_code_prefix": ["01310", "20040", "30140", "01310"],
        "customer_city": ["SAO PAULO", "RIO DE JANEIRO", "BELO HORIZONTE", "SAO PAULO"],
        "customer_state": ["SP", "RJ", "MG", "SP"],
    })


@pytest.fixture
def sample_products():
    """Jeu de données products minimal."""
    return pd.DataFrame({
        "product_id": ["PROD1", "PROD2", "PROD3"],
        "product_category_name": ["cama_mesa_banho", "beleza_saude", None],
        "product_name_lenght": [40, 60, 30],
        "product_description_lenght": [200, 450, 100],
        "product_photos_qty": [3, 1, 2],
        "product_weight_g": [800.0, 200.0, 1500.0],
        "product_length_cm": [30.0, 15.0, 50.0],
        "product_height_cm": [10.0, 5.0, 20.0],
        "product_width_cm": [25.0, 12.0, 40.0],
    })


@pytest.fixture
def sample_payments():
    """Jeu de données payments minimal."""
    return pd.DataFrame({
        "order_id": ["ORD001", "ORD001", "ORD002", "ORD003"],
        "payment_sequential": [1, 2, 1, 1],
        "payment_type": ["credit_card", "voucher", "boleto", "credit_card"],
        "payment_installments": [3, 1, 1, 6],
        "payment_value": [225.00, 15.50, -5.00, 220.00],  # -5 → rejet
    })
