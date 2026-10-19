# MongoDB demo (NoSQL)

A tiny online-shop dataset (products, customers, orders) served through a FastAPI app, used to show the core ideas of a document database.

## Run

```bash
docker compose up -d --build
```

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI – try every endpoint from the browser |
| http://localhost:8082 | mongo-express – browse the raw collections |
| `localhost:27017` | MongoDB (user `demo` / password `demo`, local use only) |

The API reseeds the data every time it starts. `POST /reset` reloads it without restarting. Code in `app/` is mounted into the container, so edits are picked up live.

Ports clash? Override them: `API_PORT=9000 UI_PORT=9001 docker compose up -d`.

## Endpoints, in teaching order

| Endpoint | Shows |
|---|---|
| `GET /products` | Flexible schema: shoes have `brand`, pans have `material`, same collection. Filters build a Mongo query (`$lte`, `$in`, `$gt`, `$exists`) and the response echoes it as `filter` |
| `GET /products/{id}`, `POST`, `PATCH`, `DELETE` | CRUD. `POST` accepts any extra fields (try `"eco_label": true`); `PATCH` uses `$set` |
| `POST /products/{id}/restock` | Atomic `$inc` |
| `GET /customers?city=Berlin` | Querying an embedded document with dot notation (`address.city`) |
| `GET /orders?product_id=p2` | Matching inside an array of embedded docs + `$lookup` (JOIN) to the customer |
| `GET /stats/categories` | `$group` (GROUP BY) |
| `GET /stats/revenue` | `$unwind` → `$group` → `$lookup` pipeline |
| `GET /indexes/explain` → `POST /indexes/category` → `GET /indexes/explain` | `COLLSCAN` vs `IXSCAN` |

Example filters: `/products?size=M`, `/products?size=40`, `/products?in_stock=false`, `/products?has_field=brand`, `/products?category=clothing&max_price=20`.

## Talking points

- **Documents, not rows** – a document is JSON-like and can hold nested objects and arrays.
- **Schema-on-read** – no `CREATE TABLE`; documents in one collection can differ. Flexible, but the app must handle missing fields (here Pydantic enforces a few required fields and allows the rest).
- **Embed vs reference** – order line items are embedded (always read with the order); the customer is referenced by `customer_id` (shared across orders). Rule of thumb: embed what you read together, reference what is shared or grows unbounded.
- **Trade-off** – joins (`$lookup`) exist but are not the main pattern; you design documents around your queries.

## Project layout

```
app/db.py     connection + ObjectId -> str helper
app/seed.py   sample data, seed() runs on startup
app/main.py   FastAPI endpoints
```

## Explore by hand

```bash
docker exec -it nosql-demo-mongo mongosh -u demo -p demo
use shop
db.products.find({ category: "shoes" })
```

## Run the API without Docker (Mongo still in Docker)

```bash
docker compose up -d mongo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Clean up

```bash
docker compose down -v   # -v also deletes the data volume
```
