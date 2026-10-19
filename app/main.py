"""FastAPI app exposing the MongoDB demo as endpoints. Open /docs to try them."""
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db import clean, db
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Seeded:", seed())  # fresh data on every start
    yield


app = FastAPI(title="MongoDB demo shop", lifespan=lifespan)


@app.post("/reset", tags=["setup"])
def reset():
    """Drop all collections and reload the sample data."""
    return seed()


# ---------- CRUD ----------

class Product(BaseModel):
    # A few required fields, but any extra field is accepted and stored as-is
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    category: str
    price: float
    stock: int = 0


@app.get("/products", tags=["products"])
def list_products(category: str | None = None, max_price: float | None = None,
                  size: str | None = None, in_stock: bool | None = None,
                  has_field: str | None = None):
    """Build a MongoDB filter from the query parameters."""
    query = {}
    if category:
        query["category"] = category
    if max_price is not None:
        query["price"] = {"$lte": max_price}
    if size:
        # Array match: sizes are strings ("M") for clothes and numbers (40) for shoes
        query["sizes"] = {"$in": [size, int(size)] if size.isdigit() else [size]}
    if in_stock is not None:
        query["stock"] = {"$gt": 0} if in_stock else 0
    if has_field:
        query[has_field] = {"$exists": True}
    return {"filter": query, "results": list(db.products.find(query).sort("price"))}


@app.get("/products/{product_id}", tags=["products"])
def get_product(product_id: str):
    product = db.products.find_one({"_id": product_id})
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.post("/products", status_code=201, tags=["products"],
          openapi_extra={"requestBody": {"content": {"application/json": {"example": {
              "id": "p7", "name": "Wool Socks", "category": "clothing",
              "price": 9.9, "stock": 100, "eco_label": True}}}}})
def create_product(product: Product):
    doc = product.model_dump()
    doc["_id"] = doc.pop("id")
    if db.products.find_one({"_id": doc["_id"]}):
        raise HTTPException(409, "Product id already exists")
    db.products.insert_one(doc)
    return doc


@app.patch("/products/{product_id}", tags=["products"])
def update_product(product_id: str, changes: dict = Body(examples=[{"price": 7.9, "tags": ["sale"]}])):
    """Partial update with $set - only the given fields change."""
    changes.pop("_id", None)
    result = db.products.update_one({"_id": product_id}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return db.products.find_one({"_id": product_id})


@app.post("/products/{product_id}/restock", tags=["products"])
def restock(product_id: str, amount: int = 10):
    """Atomic increment with $inc - no read-modify-write race."""
    result = db.products.update_one({"_id": product_id}, {"$inc": {"stock": amount}})
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return db.products.find_one({"_id": product_id}, {"name": 1, "stock": 1})


@app.delete("/products/{product_id}", tags=["products"])
def delete_product(product_id: str):
    result = db.products.delete_one({"_id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")
    return {"deleted": product_id}


# ---------- Nested documents & references ----------

@app.get("/customers", tags=["customers & orders"])
def list_customers(city: str | None = None):
    """Filter on an embedded document with dot notation: address.city"""
    query = {"address.city": city} if city else {}
    return list(db.customers.find(query))


@app.get("/orders", tags=["customers & orders"])
def list_orders(product_id: str | None = None):
    """Orders with customer details joined in via $lookup."""
    pipeline = []
    if product_id:
        # Match inside an array of embedded documents
        pipeline.append({"$match": {"items.product_id": product_id}})
    pipeline += [
        {"$lookup": {"from": "customers", "localField": "customer_id",
                     "foreignField": "_id", "as": "customer"}},
        {"$unwind": "$customer"},
        {"$project": {"customer_id": 0, "customer.address": 0}},
    ]
    return clean(list(db.orders.aggregate(pipeline)))


# ---------- Aggregation ----------

@app.get("/stats/categories", tags=["aggregation"])
def category_stats():
    """$group ~ SQL GROUP BY"""
    return list(db.products.aggregate([
        {"$group": {"_id": "$category",
                    "products": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "total_stock": {"$sum": "$stock"}}},
        {"$set": {"avg_price": {"$round": ["$avg_price", 2]}}},
        {"$sort": {"_id": 1}},
    ]))


@app.get("/stats/revenue", tags=["aggregation"])
def revenue_per_customer():
    """$unwind line items, multiply qty * price, sum per customer, join the name."""
    return list(db.orders.aggregate([
        {"$unwind": "$items"},  # one document per line item
        {"$group": {"_id": "$customer_id",
                    "revenue": {"$sum": {"$multiply": ["$items.qty", "$items.price"]}}}},
        {"$set": {"revenue": {"$round": ["$revenue", 2]}}},
        {"$lookup": {"from": "customers", "localField": "_id",
                     "foreignField": "_id", "as": "customer"}},
        {"$project": {"revenue": 1, "name": {"$first": "$customer.name"}}},
        {"$sort": {"revenue": -1}},
    ]))


# ---------- Indexes ----------

@app.get("/indexes/explain", tags=["indexes"])
def explain(category: str = "shoes"):
    """Show whether a query scans the whole collection (COLLSCAN) or uses an index (IXSCAN)."""
    stage = db.products.find({"category": category}).explain()["queryPlanner"]["winningPlan"]
    while "inputStage" in stage:  # walk down to the innermost stage
        stage = stage["inputStage"]
    return {"plan": stage["stage"], "indexes": list(db.products.index_information())}


@app.post("/indexes/category", tags=["indexes"])
def create_category_index():
    return {"created": db.products.create_index("category")}


@app.delete("/indexes/category", tags=["indexes"])
def drop_category_index():
    db.products.drop_index("category_1")
    return {"dropped": "category_1"}
