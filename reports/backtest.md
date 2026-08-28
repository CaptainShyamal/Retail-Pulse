# RetailPulse Demand Forecasting Backtest Report

**Date of Run:** 2026-08-29 01:32:18  
**Evaluation Strategy:** Time-based holdout (28 days)  
**Test Window:** 2025-12-03 to 2025-12-31  
**Total Test Records Evaluated:** 1400

---

## 1. Overall Performance Comparison
 
| Model | Architecture | Holdout MAPE | Holdout RMSE | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Additive Baseline** | Seasonal Holt-Winters / Prophet | **73.63%** | **3.36** | Baseline |
| **XGBoost (Phase 3 Primary)** | GBDT + Lags + Sentiment + IoT | **61.47%** | **3.35** | **Production Champion** |
| **Graph-Enhanced XGBoost (Phase 7)** | GBDT + Lags + Sentiment + IoT + Neo4j Graph Features | **62.01%** | **3.33** | **Experimental** |
 
### Key Takeaways & Honest Assessment of Knowledge Graph Impact:
- **Result Summary:** **Mixed / Inconclusive.** Holdout MAPE degraded slightly by 0.54 percentage points (from **61.47%** to **62.01%**), while Holdout RMSE showed marginal improvement from **3.35** to **3.33** (-0.02 units).
- **Baseline Comparison:** XGBoost reduced Holdout MAPE by **12.16 percentage points** compared to the Holt-Winters baseline (73.63% -> 61.47%, a **16.5% relative error reduction**).
- **Root Cause & Limitations:** With a pilot catalog of only 10 SKUs and 4 substitute relationships, the graph topology is too sparse to provide a strong, unambiguous predictive signal. The graph features add slight noise to percentage error on low-volume items while providing minor variance reduction in RMSE.
- **Production Architecture Decision:** Graph features are categorized as **experimental** and parked behind a feature flag (`--include-graph-features`). The leaner Phase 3 XGBoost model (Lags + IoT Shelf + Sentiment) is retained as the active production champion. Graph features will be re-evaluated once the product catalog expands to 500+ SKUs.

---

## 2. Per-SKU Granular Performance

| SKU     | Baseline MAPE (%)   | XGBoost MAPE (%)   |   Baseline RMSE |   XGBoost RMSE | Winner   |
|:--------|:--------------------|:-------------------|----------------:|---------------:|:---------|
| SKU_001 | 84.92%              | 67.10%             |            2.2  |           2.2  | XGBoost  |
| SKU_002 | 68.37%              | 60.41%             |            4.59 |           4.76 | XGBoost  |
| SKU_003 | 90.85%              | 80.34%             |            3.62 |           3.71 | XGBoost  |
| SKU_004 | 72.17%              | 59.45%             |            1.24 |           1.2  | XGBoost  |
| SKU_005 | 65.10%              | 52.50%             |            2.74 |           2.58 | XGBoost  |
| SKU_006 | 88.39%              | 80.97%             |            2.21 |           2.32 | XGBoost  |
| SKU_007 | 83.17%              | 73.00%             |            6.36 |           6.09 | XGBoost  |
| SKU_008 | 62.64%              | 50.03%             |            1.25 |           1.26 | XGBoost  |
| SKU_009 | 85.00%              | 76.72%             |            1.84 |           1.87 | XGBoost  |
| SKU_010 | 73.18%              | 58.74%             |            3.86 |           3.76 | XGBoost  |

---

## 3. Success Metrics Summary

- **Target Champion RMSE:** < 10.0
- **Achieved Champion RMSE (XGBoost):** **3.35** (Primary) / **3.33** (Graph Exp) [PASSED]
- **Target Champion MAPE:** < 65.0% on discrete sparse retail transactions
- **Achieved Champion MAPE (XGBoost):** **61.47%** (Primary) [PASSED]

---

## 4. Known Limitation & Data Sparsity Diagnostics

- **Root Cause of Elevated MAPE:** The dataset contains low-volume discrete unit counts (e.g. actual daily sales of 1 or 2 items). A 1-unit prediction error on 1 unit actual creates a 100% relative percentage error, elevating the arithmetic MAPE metric despite an absolute error (MAE) of only ~2.08 units and RMSE of ~3.33–3.35 units.
- **Remediation:** Evaluated alongside scale-independent MAE and RMSE metrics for operational inventory reorder decisions.
