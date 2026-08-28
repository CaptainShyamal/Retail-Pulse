// ==========================================
// RetailPulse Knowledge Graph Schema Definition
// Graph Model: Neo4j 5.x Cypher
// ==========================================

// 1. Constraints (Unique Identifiers)
CREATE CONSTRAINT product_sku_unique IF NOT EXISTS
FOR (p:Product) REQUIRE p.sku IS UNIQUE;

CREATE CONSTRAINT store_id_unique IF NOT EXISTS
FOR (s:Store) REQUIRE s.store_id IS UNIQUE;

CREATE CONSTRAINT supplier_id_unique IF NOT EXISTS
FOR (sup:Supplier) REQUIRE sup.supplier_id IS UNIQUE;

// 2. Indexes for High-Speed Traversal & Filtering
CREATE INDEX product_category_idx IF NOT EXISTS
FOR (p:Product) ON (p.category);

CREATE INDEX store_region_idx IF NOT EXISTS
FOR (s:Store) ON (s.region);

// 3. Schema Data Contract & Edge Definitions:
// ------------------------------------------
// (:Product {sku: string, category: string, price_band: string, avg_price: float})
// (:Store {store_id: string, region: string, format: string})
// (:Supplier {supplier_id: string, supplier_name: string, lead_time_days: int})
//
// Relationships:
// (p:Product)-[:SOLD_AT {avg_daily_qty: float, total_revenue: float, active: boolean}]->(s:Store)
// (p1:Product)-[:SUBSTITUTE_FOR {category: string, price_ratio: float, similarity_score: float}]->(p2:Product)
// (p:Product)-[:SUPPLIED_BY {lead_time_days: int}]->(sup:Supplier)
