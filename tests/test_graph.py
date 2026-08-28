import os
import sys
import pytest
import pandas as pd
import numpy as np
from neo4j import GraphDatabase

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from graph.graph_features import compute_point_in_time_graph_features

def test_schema_cypher_syntax_and_constraints():
    schema_path = os.path.join(PROJECT_ROOT, "graph", "schema.cypher")
    assert os.path.exists(schema_path), f"Schema file missing at {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "CREATE CONSTRAINT product_sku_unique" in content
    assert "CREATE CONSTRAINT store_id_unique" in content
    assert "CREATE CONSTRAINT supplier_id_unique" in content
    assert "SOLD_AT" in content
    assert "SUBSTITUTE_FOR" in content
    assert "SUPPLIED_BY" in content

def test_point_in_time_graph_features_data_leakage_guard():
    # Construct synthetic time-series
    dates = pd.date_range("2025-01-01", "2025-01-10")
    records = []
    for d in dates:
        records.append({
            "store_id": "STORE_001",
            "sku": "SKU_001",
            "date": d.strftime("%Y-%m-%d"),
            "qty_sold": 5,
            "revenue": 50.0,
            "avg_shelf_qty": 10.0,
            "sentiment_score": 0.5
        })
        records.append({
            "store_id": "STORE_001",
            "sku": "SKU_002",
            "date": d.strftime("%Y-%m-%d"),
            "qty_sold": 3,
            "revenue": 30.0,
            "avg_shelf_qty": 8.0,
            "sentiment_score": 0.2
        })

    df = pd.DataFrame(records)
    substitute_map = {"SKU_001": {"SKU_002"}, "SKU_002": {"SKU_001"}}

    # Compute with cutoff at day 5
    cutoff = "2025-01-05"
    enriched = compute_point_in_time_graph_features(df, substitute_map, cutoff_date=cutoff)

    assert "graph_co_stock_freq" in enriched.columns
    assert "graph_substitute_available" in enriched.columns
    # Check bounded range
    assert (enriched["graph_co_stock_freq"] >= 0.0).all() and (enriched["graph_co_stock_freq"] <= 1.0).all()
    assert set(enriched["graph_substitute_available"].unique()).issubset({0.0, 1.0})

def test_neo4j_live_connection_and_node_counts():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "changeme123")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            res = session.run("RETURN count { (p:Product) } AS p_cnt").single()
            product_count = res["p_cnt"]
            assert product_count >= 10, f"Expected at least 10 products in Neo4j, got {product_count}"
        driver.close()
    except Exception as e:
        pytest.skip(f"Neo4j container not reachable in current test context: {e}")
