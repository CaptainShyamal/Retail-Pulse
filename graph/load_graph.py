import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from neo4j import GraphDatabase
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

def get_neo4j_driver(max_retries: int = 15, delay_sec: int = 2):
    """
    Connects to Neo4j instance with retry loop for container warm-up.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "changeme123")

    for attempt in range(1, max_retries + 1):
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                session.run("RETURN 1 AS ping")
            print(f"Connected to Neo4j at {uri}")
            return driver
        except Exception as e:
            if attempt == max_retries:
                raise ConnectionError(f"Failed to connect to Neo4j at {uri} after {max_retries} attempts: {e}")
            print(f"Waiting for Neo4j at {uri} (attempt {attempt}/{max_retries})...")
            time.sleep(delay_sec)

def apply_schema(driver, schema_file: str = None):
    """
    Executes constraints and index definitions from Cypher schema file.
    """
    if schema_file is None:
        schema_file = os.path.join(PROJECT_ROOT, "graph", "schema.cypher")

    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found at {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        statements = [stmt.strip() for stmt in f.read().split(";") if stmt.strip() and not stmt.strip().startswith("//")]

    with driver.session() as session:
        for stmt in statements:
            if stmt.upper().startswith("CREATE"):
                session.run(stmt)
    print("Neo4j Schema constraints and indexes verified.")

def load_knowledge_graph(data_path: str = None):
    """
    Populates Neo4j with Product, Store, and Supplier nodes and relationships
    using idempotent MERGE statements.
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Curated data not found at {data_path}")

    print(f"Reading curated retail data from {data_path}...")
    df = pd.read_parquet(data_path)

    driver = get_neo4j_driver()
    apply_schema(driver)

    # 1. Product metadata extraction
    sku_stats = df.groupby("sku").agg(
        total_qty=("qty_sold", "sum"),
        total_rev=("revenue", "sum"),
        avg_shelf=("avg_shelf_qty", "mean"),
        avg_sentiment=("sentiment_score", "mean")
    ).reset_index()

    sku_stats["avg_price"] = np.where(sku_stats["total_qty"] > 0, sku_stats["total_rev"] / sku_stats["total_qty"], 15.0).round(2)
    # Heuristic category and price band assignment
    categories = ["Beverages", "Snacks", "Dairy", "Bakery", "Household"]
    sku_stats["category"] = [categories[int(str(s).split('_')[-1]) % len(categories)] if '_' in str(s) else "General" for s in sku_stats["sku"]]
    sku_stats["price_band"] = np.where(sku_stats["avg_price"] < 10, "Budget", np.where(sku_stats["avg_price"] < 25, "Mid-Tier", "Premium"))

    # 2. Store metadata extraction
    stores = df["store_id"].unique()
    regions = ["North", "South", "East", "West", "Central"]
    store_metadata = [
        {
            "store_id": str(s),
            "region": regions[int(str(s).split('_')[-1]) % len(regions)] if '_' in str(s) else "Central",
            "format": "Supercenter" if i % 2 == 0 else "Express"
        }
        for i, s in enumerate(sorted(stores))
    ]

    # 3. Suppliers metadata
    suppliers = [
        {"supplier_id": "SUP_GLOBAL_01", "supplier_name": "Global Retail Distributors", "lead_time_days": 3},
        {"supplier_id": "SUP_LOCAL_02", "supplier_name": "FreshSource Logistics", "lead_time_days": 1},
        {"supplier_id": "SUP_PRIME_03", "supplier_name": "Prime Goods Wholesale", "lead_time_days": 2}
    ]

    # 4. Product-Store performance (SOLD_AT)
    ps_stats = df.groupby(["store_id", "sku"]).agg(
        avg_daily_qty=("qty_sold", "mean"),
        total_revenue=("revenue", "sum")
    ).reset_index()

    with driver.session() as session:
        # Load Stores (Idempotent MERGE)
        print("Upserting Store nodes...")
        for st in store_metadata:
            session.run("""
                MERGE (s:Store {store_id: $store_id})
                SET s.region = $region, s.format = $format
            """, st)

        # Load Suppliers (Idempotent MERGE)
        print("Upserting Supplier nodes...")
        for sup in suppliers:
            session.run("""
                MERGE (sup:Supplier {supplier_id: $supplier_id})
                SET sup.supplier_name = $supplier_name, sup.lead_time_days = $lead_time_days
            """, sup)

        # Load Products & Supplier relationships (Idempotent MERGE)
        print("Upserting Product nodes & SUPPLIED_BY relationships...")
        for idx, p in sku_stats.iterrows():
            sup_id = suppliers[idx % len(suppliers)]["supplier_id"]
            session.run("""
                MERGE (p:Product {sku: $sku})
                SET p.category = $category, p.avg_price = $avg_price, p.price_band = $price_band
                WITH p
                MATCH (sup:Supplier {supplier_id: $sup_id})
                MERGE (p)-[:SUPPLIED_BY]->(sup)
            """, {
                "sku": str(p["sku"]),
                "category": str(p["category"]),
                "avg_price": float(p["avg_price"]),
                "price_band": str(p["price_band"]),
                "sup_id": sup_id
            })

        # Load SOLD_AT relationships
        print("Upserting SOLD_AT relationships...")
        for _, row in ps_stats.iterrows():
            session.run("""
                MATCH (p:Product {sku: $sku})
                MATCH (s:Store {store_id: $store_id})
                MERGE (p)-[r:SOLD_AT]->(s)
                SET r.avg_daily_qty = $avg_daily_qty, r.total_revenue = $total_revenue, r.active = true
            """, {
                "sku": str(row["sku"]),
                "store_id": str(row["store_id"]),
                "avg_daily_qty": float(row["avg_daily_qty"]),
                "total_revenue": float(row["total_revenue"])
            })

        # Load SUBSTITUTE_FOR relationships (same category, matching price band within ±35%)
        print("Deriving and upserting SUBSTITUTE_FOR relationships...")
        session.run("""
            MATCH (p1:Product), (p2:Product)
            WHERE p1.sku < p2.sku AND p1.category = p2.category
            AND abs(p1.avg_price - p2.avg_price) <= (0.35 * p1.avg_price)
            MERGE (p1)-[r1:SUBSTITUTE_FOR]-(p2)
            SET r1.category = p1.category,
                r1.similarity_score = 1.0 - (abs(p1.avg_price - p2.avg_price) / p1.avg_price)
        """)

        # Verify summary counts
        node_counts = session.run("""
            RETURN 
                count { (p:Product) } AS products,
                count { (s:Store) } AS stores,
                count { (sup:Supplier) } AS suppliers,
                count { ()-[:SOLD_AT]->() } AS sold_at,
                count { ()-[:SUBSTITUTE_FOR]-() } AS substitutes,
                count { ()-[:SUPPLIED_BY]->() } AS supplied_by
        """).single()

    driver.close()

    print("=" * 60)
    print("Knowledge Graph Successfully Loaded into Neo4j!")
    print(f"  - Products:    {node_counts['products']}")
    print(f"  - Stores:      {node_counts['stores']}")
    print(f"  - Suppliers:   {node_counts['suppliers']}")
    print(f"  - SOLD_AT:     {node_counts['sold_at']}")
    print(f"  - SUBSTITUTES: {node_counts['substitutes']}")
    print(f"  - SUPPLIED_BY: {node_counts['supplied_by']}")
    print("=" * 60)
    return dict(node_counts)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse Neo4j Knowledge Graph Loader")
    parser.add_argument("--data-path", type=str, default=None, help="Path to curated sales parquet")
    args = parser.parse_args()

    load_knowledge_graph(data_path=args.data_path)
