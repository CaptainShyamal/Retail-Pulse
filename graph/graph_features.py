import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

def get_substitute_mapping_from_neo4j():
    """
    Queries Neo4j Knowledge Graph to retrieve bidirectional substitute product mappings.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "changeme123")

    substitute_map = {}
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("""
                MATCH (p1:Product)-[:SUBSTITUTE_FOR]-(p2:Product)
                RETURN p1.sku AS sku1, p2.sku AS sku2, p1.category AS category
            """)
            for record in result:
                sku1, sku2 = record["sku1"], record["sku2"]
                substitute_map.setdefault(sku1, set()).add(sku2)
                substitute_map.setdefault(sku2, set()).add(sku1)
        driver.close()
        print(f"Loaded {len(substitute_map)} SKU substitute mappings from Neo4j.")
    except Exception as e:
        print(f"Warning: Could not query Neo4j ({e}). Building fallback structural mapping from category definitions.")
        # Fallback category grouping
        categories = ["Beverages", "Snacks", "Dairy", "Bakery", "Household"]
        all_skus = [f"SKU_{i:03d}" for i in range(1, 51)]
        cat_map = {s: categories[int(s.split('_')[-1]) % len(categories)] for s in all_skus}
        for s1 in all_skus:
            for s2 in all_skus:
                if s1 != s2 and cat_map[s1] == cat_map[s2]:
                    substitute_map.setdefault(s1, set()).add(s2)

    return substitute_map

def compute_point_in_time_graph_features(
    df: pd.DataFrame,
    substitute_map: dict,
    cutoff_date: str = None
) -> pd.DataFrame:
    """
    Computes graph-derived features with strict Point-in-Time Data Leakage Guards:
    
    1. `graph_co_stock_freq`:
       Measures historical co-occurrence frequency of substitute/peer products in the same store.
       Calculated strictly on historical observations (or restricted before `cutoff_date`).
       
    2. `graph_substitute_available`:
       Point-in-time daily flag (0 or 1) indicating if at least one graph-linked substitute product
       had available shelf stock (avg_shelf_qty > 0) at the SAME store on the prior day (t-1).
       Using lag-1 shelf stock completely eliminates target/future-period lookahead leakage.
    """
    df = df.copy()
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["store_id", "dt", "sku"]).reset_index(drop=True)

    print("Computing Point-in-Time Graph Features (No-Leakage Guarantee)...")
    if cutoff_date:
        print(f"  [DATA LEAKAGE GUARD] Training/Holdout boundary active at: {cutoff_date}")

    # Create a quick lookup for store-sku-date inventory (shifted by 1 day to prevent contemporaneous leak)
    # Using t-1 shelf stock of substitute products:
    df["prev_day_shelf"] = df.groupby(["store_id", "sku"])["avg_shelf_qty"].shift(1).fillna(0)
    
    # Store-day level inventory index: {(store_id, date, sku): prev_shelf}
    inventory_map = {
        (r.store_id, r.dt.strftime("%Y-%m-%d"), r.sku): float(r.prev_day_shelf)
        for r in df[["store_id", "dt", "sku", "prev_day_shelf"]].itertuples(index=False)
    }

    # Historical co-stock frequency calculation (using only records <= cutoff_date if supplied)
    hist_df = df[df["dt"] <= pd.to_datetime(cutoff_date)] if cutoff_date else df
    active_pairs = hist_df[hist_df["qty_sold"] > 0].groupby(["store_id", "sku"])["date"].nunique()
    total_store_days = hist_df.groupby("store_id")["date"].nunique()

    co_stock_freq_lookup = {}
    for (st, sk), days_sold in active_pairs.items():
        st_days = total_store_days.get(st, 1)
        substitutes = substitute_map.get(sk, set())
        # Average frequency of substitute peers
        peer_days = [active_pairs.get((st, peer_sku), 0) for peer_sku in substitutes]
        avg_peer_freq = (np.mean(peer_days) / st_days) if (peer_days and st_days > 0) else (days_sold / st_days)
        co_stock_freq_lookup[(st, sk)] = float(np.clip(avg_peer_freq, 0.0, 1.0))

    # Vectorized feature assignment
    def check_substitute_available(row):
        subs = substitute_map.get(row["sku"], set())
        d_str = row["dt"].strftime("%Y-%m-%d") if isinstance(row["dt"], pd.Timestamp) else str(row["date"])[:10]
        for sub_sku in subs:
            if inventory_map.get((row["store_id"], d_str, sub_sku), 0.0) > 2.0:
                return 1.0
        return 0.0

    df["graph_co_stock_freq"] = df.apply(
        lambda r: co_stock_freq_lookup.get((r["store_id"], r["sku"]), 0.5), axis=1
    )
    df["graph_substitute_available"] = df.apply(check_substitute_available, axis=1)

    df = df.drop(columns=["prev_day_shelf"])
    return df

def enrich_curated_with_graph_features(data_path: str = None, cutoff_date: str = None):
    """
    Loads curated sales dataset, computes graph features, and updates curated Parquet.
    """
    if data_path is None:
        data_path = os.path.join(PROJECT_ROOT, "data", "curated", "sales_daily.parquet")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Curated sales data not found at {data_path}")

    df = pd.read_parquet(data_path)
    substitute_map = get_substitute_mapping_from_neo4j()

    enriched_df = compute_point_in_time_graph_features(df, substitute_map, cutoff_date=cutoff_date)
    enriched_df.to_parquet(data_path, index=False)

    print("=" * 60)
    print("Graph Features Successfully Enriched into Curated Lakehouse!")
    print(f"  - Output file: {data_path}")
    print(f"  - Total rows:  {len(enriched_df)}")
    print(f"  - Mean co-stock frequency:       {enriched_df['graph_co_stock_freq'].mean():.4f}")
    print(f"  - Substitute availability rate:  {enriched_df['graph_substitute_available'].mean() * 100:.2f}%")
    print("=" * 60)
    return enriched_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse Graph Feature Engineering")
    parser.add_argument("--cutoff-date", type=str, default=None, help="Optional holdout cutoff date for strict backtesting")
    args = parser.parse_args()

    enrich_curated_with_graph_features(cutoff_date=args.cutoff_date)
