"""Sample data, loaded when the API starts.

Note the flexible schema: products in the same collection have different fields.
"""
from datetime import datetime

from app.db import db

PRODUCTS = [
    {"_id": "p1", "name": "Rain Jacket", "category": "clothing", "price": 49.90,
     "sizes": ["S", "M", "L"], "color": "yellow", "stock": 12},
    {"_id": "p2", "name": "Running Shoes", "category": "shoes", "price": 79.00,
     "sizes": [38, 39, 40, 41, 42], "brand": "Speedy", "stock": 5},
    {"_id": "p3", "name": "Cotton T-Shirt", "category": "clothing", "price": 12.50,
     "sizes": ["XS", "S", "M"], "color": "white", "stock": 40},
    {"_id": "p4", "name": "Frying Pan", "category": "household", "price": 29.99,
     "material": "cast iron", "diameter_cm": 28, "stock": 0},
    {"_id": "p5", "name": "Kids Sneakers", "category": "shoes", "price": 34.90,
     "sizes": [28, 29, 30], "brand": "Speedy", "stock": 8},
    {"_id": "p6", "name": "Bed Linen Set", "category": "household", "price": 39.00,
     "material": "cotton", "dimensions": {"width_cm": 135, "length_cm": 200}, "stock": 15},
]

# Synthetic customers - the address is an *embedded document*
CUSTOMERS = [
    {"_id": "c1", "name": "Alice Example", "country": "DE",
     "address": {"city": "Berlin", "zip": "10115"}},
    {"_id": "c2", "name": "Bob Sample", "country": "PL",
     "address": {"city": "Krakow", "zip": "30-001"}},
    {"_id": "c3", "name": "Carol Test", "country": "NL",
     "address": {"city": "Utrecht", "zip": "3511"}},
]

# Orders embed their line items (always read together), but *reference* the customer
ORDERS = [
    {"customer_id": "c1", "created": datetime(2026, 9, 1), "status": "delivered",
     "items": [{"product_id": "p1", "qty": 1, "price": 49.90},
               {"product_id": "p3", "qty": 3, "price": 12.50}]},
    {"customer_id": "c2", "created": datetime(2026, 9, 3), "status": "shipped",
     "items": [{"product_id": "p2", "qty": 1, "price": 79.00}]},
    {"customer_id": "c1", "created": datetime(2026, 9, 10), "status": "new",
     "items": [{"product_id": "p6", "qty": 2, "price": 39.00}]},
    {"customer_id": "c3", "created": datetime(2026, 9, 12), "status": "delivered",
     "items": [{"product_id": "p5", "qty": 2, "price": 34.90},
               {"product_id": "p4", "qty": 1, "price": 29.99}]},
]


def seed():
    """Drop everything and load the sample data."""
    for name in ("products", "customers", "orders"):
        db[name].drop()
    db.products.insert_many([dict(p) for p in PRODUCTS])  # copies: insert_many mutates input
    db.customers.insert_many([dict(c) for c in CUSTOMERS])
    db.orders.insert_many([dict(o) for o in ORDERS])  # no _id given -> MongoDB generates an ObjectId
    return {name: db[name].count_documents({}) for name in ("products", "customers", "orders")}
