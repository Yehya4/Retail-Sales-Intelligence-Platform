# Dictionnaire des données
## Retail & Sales Intelligence Platform — Dataset Olist

**Version :** 1.0  
**Source :** Brazilian E-Commerce Public Dataset by Olist (Kaggle)  
**Période :** 2016 – 2018  

---

## 1. orders — Commandes

**Grain :** 1 ligne par commande  
**Clé primaire :** `order_id`

| Colonne | Type | Description | Valeurs nulles attendues |
|---|---|---|---|
| `order_id` | string | Identifiant unique de la commande | Non |
| `customer_id` | string | Identifiant du client (lié à customers) | Non |
| `order_status` | string | Statut de la commande | Non |
| `order_purchase_timestamp` | datetime | Date et heure d'achat | Rare |
| `order_approved_at` | datetime | Date d'approbation du paiement | Oui (commandes non approuvées) |
| `order_delivered_carrier_date` | datetime | Date de remise au transporteur | Oui (non livrées) |
| `order_delivered_customer_date` | datetime | Date de livraison effective | Oui (non livrées) |
| `order_estimated_delivery_date` | datetime | Date de livraison estimée à l'achat | Rare |

**Statuts valides :** `delivered`, `shipped`, `canceled`, `invoiced`, `processing`, `approved`, `created`, `unavailable`

**Colonnes calculées (pipeline) :**
- `delivery_days` : différence en jours entre `order_delivered_customer_date` et `order_purchase_timestamp`
- `is_on_time` : 1 si `order_delivered_customer_date <= order_estimated_delivery_date`, 0 sinon
- `delay_days` : différence en jours de retard (si `is_on_time = 0`)

---

## 2. order_items — Lignes de commande

**Grain :** 1 ligne par article dans une commande  
**Clé primaire composite :** (`order_id`, `order_item_id`)

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `order_id` | string | Référence à la commande | Non |
| `order_item_id` | integer | Numéro de séquence de l'article dans la commande | Non |
| `product_id` | string | Référence au produit | Non |
| `seller_id` | string | Référence au vendeur | Non |
| `shipping_limit_date` | datetime | Date limite d'expédition par le vendeur | Rare |
| `price` | float | Prix de vente de l'article (BRL) | Non |
| `freight_value` | float | Frais de livraison facturés au client (BRL) | Non |

> ⚠️ **Attention double comptage** : Ne pas joindre directement cette table à `payments` sans agrégation préalable. La granularité est différente.

---

## 3. customers — Clients

**Grain :** 1 ligne par `customer_id` (identifiant de commande, pas unique per se)  
**Clé primaire :** `customer_id`

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `customer_id` | string | Identifiant client par commande | Non |
| `customer_unique_id` | string | Identifiant unique du client (pour multi-commandes) | Rare |
| `customer_zip_code_prefix` | string | Code postal (5 chiffres) | Oui |
| `customer_city` | string | Ville | Oui |
| `customer_state` | string | État brésilien (2 lettres) | Oui |

> **Note :** Pour analyser les clients récurrents, utiliser `customer_unique_id`.

---

## 4. products — Produits

**Grain :** 1 ligne par produit  
**Clé primaire :** `product_id`

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `product_id` | string | Identifiant unique du produit | Non |
| `product_category_name` | string | Catégorie en portugais | Oui (~1%) |
| `product_category_name_english` | string | Catégorie traduite (via jointure) | Selon traduction |
| `product_name_lenght` | integer | Longueur du nom du produit (caractères) | Oui |
| `product_description_lenght` | integer | Longueur de la description | Oui |
| `product_photos_qty` | integer | Nombre de photos | Oui |
| `product_weight_g` | float | Poids en grammes | Oui |
| `product_length_cm` | float | Longueur en cm | Oui |
| `product_height_cm` | float | Hauteur en cm | Oui |
| `product_width_cm` | float | Largeur en cm | Oui |

---

## 5. sellers — Vendeurs

**Grain :** 1 ligne par vendeur  
**Clé primaire :** `seller_id`

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `seller_id` | string | Identifiant unique du vendeur | Non |
| `seller_zip_code_prefix` | string | Code postal (5 chiffres) | Oui |
| `seller_city` | string | Ville du vendeur | Oui |
| `seller_state` | string | État du vendeur | Oui |

---

## 6. payments — Paiements

**Grain :** 1 ligne par séquence de paiement par commande  
**Clé primaire composite :** (`order_id`, `payment_sequential`)

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `order_id` | string | Référence à la commande | Non |
| `payment_sequential` | integer | Numéro de séquence du paiement | Non |
| `payment_type` | string | Moyen de paiement | Oui |
| `payment_installments` | integer | Nombre de mensualités | Oui |
| `payment_value` | float | Montant du paiement (BRL) | Non |

**Moyens de paiement connus :** `credit_card`, `boleto`, `voucher`, `debit_card`

> ⚠️ Une commande peut avoir plusieurs lignes de paiement (paiements mixtes). Agréger par `order_id` pour le montant total.

---

## 7. reviews — Avis clients

**Grain :** 1 ligne par avis  
**Clé primaire :** `review_id`

| Colonne | Type | Description | Valeurs nulles |
|---|---|---|---|
| `review_id` | string | Identifiant unique de l'avis | Non |
| `order_id` | string | Référence à la commande | Non |
| `review_score` | integer | Note de 1 à 5 | Rare |
| `review_comment_title` | string | Titre du commentaire | Oui (fréquent) |
| `review_comment_message` | string | Corps du commentaire | Oui (fréquent) |
| `review_creation_date` | datetime | Date de création de l'avis | Non |
| `review_answer_timestamp` | datetime | Date de réponse | Oui |

---

## 8. geolocation — Géolocalisation

**Grain :** 1 ligne par code postal (peut avoir plusieurs coordonnées)  
**Usage :** Enrichissement géographique optionnel

| Colonne | Type | Description |
|---|---|---|
| `geolocation_zip_code_prefix` | string | Code postal |
| `geolocation_lat` | float | Latitude |
| `geolocation_lng` | float | Longitude |
| `geolocation_city` | string | Ville |
| `geolocation_state` | string | État |

---

## Relations entre tables

```
customers ──────────────────────────────────────────┐
    (customer_id)                                    │
                                                     ▼
orders ──────────────── order_items ──── products
(order_id)              (order_id)       (product_id)
    │                       │
    ├──── payments           └──── sellers
    │   (order_id)                (seller_id)
    │
    └──── reviews
         (order_id)
```

---

## Règles métier documentées

| Règle | Description |
|---|---|
| R01 | Le CA des articles = SUM(price) sur commandes livrées uniquement |
| R02 | Les frais de livraison (freight_value) ne représentent pas le coût réel de transport pour Olist |
| R03 | payment_value ≠ SUM(price + freight_value) en raison de l'arrondi et des paiements multiples |
| R04 | customer_unique_id doit être utilisé pour l'analyse RFM (pas customer_id) |
| R05 | Les commandes non livrées sont exclues des KPI logistiques (delivery_days, on_time) |
| R06 | delivery_days = order_delivered_customer_date - order_purchase_timestamp (en jours entiers) |
| R07 | delay_days est calculé uniquement si is_on_time = 0 et les deux dates sont valides |
