import os
import sys
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests
from datetime import datetime, timedelta

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.styles import CUSTOM_CSS

# Configure Streamlit page for clean full-width experience
st.set_page_config(
    page_title="RetailPulse — Demand Intelligence & Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply Black, White & Blue CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 5-Store High-Contrast Palette for Dark Theme
STORE_PALETTE = {
    "MUMBAI_STORE_001": "#3B82F6",    # Electric Blue
    "DELHI_STORE_002": "#38BDF8",     # Sky Blue
    "BENGALURU_STORE_003": "#60A5FA",  # Light Blue
    "HYDERABAD_STORE_004": "#94A3B8",  # Slate
    "CHENNAI_STORE_005": "#CBD5E1",    # Soft White
}

# ----------------- SESSION STATE FOR USER DATA -----------------
try:
    if "user_dataset" not in st.session_state:
        st.session_state.user_dataset = None
    if "dataset_meta" not in st.session_state:
        st.session_state.dataset_meta = None
    if "forecast_dataset" not in st.session_state:
        st.session_state.forecast_dataset = None
    if "anomaly_dataset" not in st.session_state:
        st.session_state.anomaly_dataset = None
except Exception:
    pass

# ----------------- INDIAN CURRENCY FORMATTER -----------------
def format_inr(val):
    """Formats a number into Indian Rupees (INR) with Lakhs/Crores or commas."""
    if val >= 10000000:
        return f"₹{val/10000000:.2f} Cr"
    elif val >= 100000:
        return f"₹{val/100000:.2f} Lakhs"
    else:
        return f"₹{val:,.0f}"

# ----------------- SMART AUTOMATIC FILE SCANNER -----------------
def get_active_stockouts(clean_df):
    """
    Computes active/current stockout incidents based on the latest available record 
    for each Store + SKU combination.
    """
    if clean_df is None or clean_df.empty:
        return pd.DataFrame()
    
    df_sorted = clean_df.copy()
    df_sorted["_dt_sort"] = pd.to_datetime(df_sorted["date"], errors="coerce")
    df_sorted = df_sorted.sort_values(by=["store_id", "sku", "_dt_sort"])
    
    # Extract latest record per store + sku
    latest_df = df_sorted.groupby(["store_id", "sku"]).last().reset_index()
    
    active_rows = []
    for _, row in latest_df.iterrows():
        store = str(row["store_id"])
        sku = str(row["sku"])
        dt = str(row["date"])
        anom_type = str(row.get("anomaly_type", "")).strip().lower()
        stock_lvl = row.get("stock_level", None)
        shelf_qty = row.get("avg_shelf_qty", None)
        
        # Explicitly ignore demand spikes or sensor mismatches
        if anom_type in ["demand_spike", "spike", "sensor_mismatch", "sensor_anomaly"]:
            continue
            
        is_stockout = False
        if anom_type in ["stockout", "stockout_risk"]:
            is_stockout = True
        elif pd.notna(stock_lvl) and float(stock_lvl) <= 0:
            is_stockout = True
        elif (stock_lvl is None or pd.isna(stock_lvl)) and pd.notna(shelf_qty) and float(shelf_qty) <= 0:
            is_stockout = True
            
        if is_stockout:
            cur_shelf = float(shelf_qty) if (pd.notna(shelf_qty) and float(shelf_qty) >= 0) else (float(stock_lvl) if pd.notna(stock_lvl) else 0.0)
            active_rows.append({
                "id": f"STOCKOUT_{store}_{sku}_{dt}",
                "store_id": store,
                "sku": sku,
                "date": dt,
                "shelf_qty": cur_shelf,
                "stock_level": float(stock_lvl) if pd.notna(stock_lvl) else cur_shelf,
                "description": f"Shelf sensor stock ({cur_shelf:.1f} units) is depleted on latest date ({dt})."
            })
            
    return pd.DataFrame(active_rows)

def process_uploaded_file(file):
    try:
        fname = getattr(file, "name", "uploaded_dataset.csv").lower()
        if fname.endswith(".csv"):
            df_raw = pd.read_csv(file)
        elif fname.endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(file)
        else:
            return False, "Unsupported file format. Please upload CSV (.csv) or Excel (.xlsx, .xls)."

        if df_raw.empty:
            return False, "The uploaded file is empty."

        col_names = df_raw.columns.tolist()

        # Automatic intelligent column detection
        def find_col(exact_candidates, fuzzy_candidates, default_col=None):
            for c in col_names:
                if str(c).strip().lower() in [ec.lower() for ec in exact_candidates]:
                    return c
            for c in col_names:
                if any(cand.lower() in str(c).strip().lower() for cand in fuzzy_candidates):
                    return c
            return default_col

        date_c = find_col(["date", "dt", "timestamp", "ts"], ["date", "time", "sold", "day", "created", "order", "timestamp", "ts"], col_names[0])
        sku_c = find_col(["sku", "product_id", "product", "item_id", "item", "code"], ["sku", "item", "product", "desc", "code", "name", "title"], col_names[1] if len(col_names) > 1 else col_names[0])
        qty_c = find_col(["qty_sold", "units_sold", "quantity_sold", "qty", "sales"], ["qty", "quant", "unit", "vol", "sold", "count", "sales"], col_names[2] if len(col_names) > 2 else col_names[0])
        price_c = find_col(["price", "unit_price", "avg_price", "rate", "cost", "price_inr"], ["price", "rate", "cost", "amount", "rev", "total", "val", "inr"], None)
        rev_c = find_col(["revenue", "total_revenue", "revenue_inr", "gross_revenue", "turnover"], ["revenue", "turnover"], None)
        store_c = find_col(["store_id", "store", "location_id", "branch_id"], ["store", "branch", "loc", "outlet", "shop", "city"], None)

        clean_df = pd.DataFrame()
        clean_df["date"] = pd.to_datetime(df_raw[date_c], errors="coerce").dt.strftime("%Y-%m-%d")
        clean_df["ts"] = pd.to_datetime(df_raw[date_c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        clean_df["sku"] = df_raw[sku_c].astype(str)
        clean_df["qty_sold"] = pd.to_numeric(df_raw[qty_c], errors="coerce").fillna(0).astype(int)
        
        if price_c and price_c in df_raw.columns:
            clean_df["price"] = pd.to_numeric(df_raw[price_c], errors="coerce").fillna(150.0).astype(float)
        else:
            clean_df["price"] = 185.0

        if rev_c and rev_c in df_raw.columns:
            clean_df["revenue"] = pd.to_numeric(df_raw[rev_c], errors="coerce").fillna(clean_df["qty_sold"] * clean_df["price"]).astype(float)
        else:
            clean_df["revenue"] = clean_df["qty_sold"] * clean_df["price"]

        if store_c and store_c in df_raw.columns:
            clean_df["store_id"] = df_raw[store_c].astype(str)
        else:
            clean_df["store_id"] = "STORE_001"

        clean_df["channel"] = "in_store"
        clean_df = clean_df.dropna(subset=["date", "sku"]).sort_values("date").reset_index(drop=True)

        # ----------------- EXECUTE REAL PIPELINE (OPTION A) -----------------
        # 1. Save normalized dataset into data/raw_sample/sales_raw.csv
        raw_sales_path = os.path.join(PROJECT_ROOT, "data", "raw_sample", "sales_raw.csv")
        os.makedirs(os.path.dirname(raw_sales_path), exist_ok=True)
        clean_df[["store_id", "sku", "ts", "qty_sold", "price", "channel"]].to_csv(raw_sales_path, index=False)

        # 2. Run clean & join Lakehouse curation
        from transform.spark_jobs.clean_join import clean_and_join_lakehouse
        df_curated = clean_and_join_lakehouse()

        # 3. Train real XGBoost Champion Model with 28-day lags, rolling stats, and MLflow logging
        from modeling.train_xgboost import train_xgboost_model
        _, df_fcst = train_xgboost_model()

        # 4. Run real statistical Anomaly Detection (stockout risks & 3-sigma demand spikes)
        from modeling.anomaly_detection import detect_anomalies
        df_anom = detect_anomalies()
        if df_anom is not None and not df_anom.empty:
            df_anom["acknowledged"] = False

        # 5. Sync to relational warehouse
        try:
            from warehouse.load_warehouse import sync_lakehouse_to_warehouse
            sync_lakehouse_to_warehouse()
        except Exception:
            pass

        # Set session state with genuine pipeline outputs
        st.session_state.user_dataset = df_curated
        st.session_state.forecast_dataset = df_fcst
        st.session_state.anomaly_dataset = df_anom
        st.session_state.dataset_meta = {
            "file_name": getattr(file, "name", "uploaded_dataset.csv"),
            "total_rows": len(df_curated),
            "stores_count": int(df_curated["store_id"].nunique()),
            "skus_count": int(df_curated["sku"].nunique()),
            "date_start": str(df_curated["date"].min()),
            "date_end": str(df_curated["date"].max())
        }

        return True, f"Successfully executed Lakehouse Pipeline & trained XGBoost Champion Model on {len(df_curated):,} curated records."
    except Exception as e:
        return False, f"Pipeline execution failed: {str(e)}"

def load_demo_dataset():
    csv_path = os.path.join(PROJECT_ROOT, "data", "indian_retail_sales_sample.csv")
    if os.path.exists(csv_path):
        with open(csv_path, "rb") as f:
            class MockFile:
                def __init__(self, f_obj, name):
                    self.f_obj = f_obj
                    self.name = name
                def read(self):
                    return self.f_obj.read()
            process_uploaded_file(MockFile(f, "retail_sales_sample.csv"))

# ==================== STATE 1: AWAITING UPLOAD (LANDING PAGE) ====================
_active_user_data = st.session_state.get("user_dataset", None) if hasattr(st, "session_state") else None
if _active_user_data is None:
    st.markdown(
        """
        <div class="top-header-bar">
            <div class="header-brand">
                <div class="header-logo-icon">₹</div>
                <div>
                    <h2 class="header-brand-title">RetailPulse</h2>
                    <div style="font-size:0.75rem; color:#94A3B8; font-weight:600;">FMCG & Grocery Demand Forecasting Platform (INR ₹)</div>
                </div>
            </div>
            <span class="header-status-pill">● Ingestion Engine Ready</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_hero_left, col_hero_right = st.columns([1.6, 1])

    with col_hero_left:
        st.markdown("## 📊 **Upload Retail Sales Data (INR ₹)**")
        st.markdown("<p style='color:#94A3B8; font-size:1.05rem; line-height:1.6;'>Upload any retail transaction export (<b>Excel .xlsx / .xls or CSV .csv</b>). The system will automatically scan columns, calculate Rupee turnover (INR ₹), and unlock the full executive dashboard.</p>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "📁 Drag & Drop or Browse Excel / CSV File",
            type=["csv", "xlsx", "xls"],
            help="Upload your POS sales transactions or inventory log"
        )

        if uploaded_file is not None:
            with st.spinner("Scanning file structure and generating 14-day forecasts in INR (₹)..."):
                ok, msg = process_uploaded_file(uploaded_file)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; color:#64748B; font-weight:600;'>— OR TEST WITH SAMPLE DATASET —</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⚡ Load Sample Dataset (5 Stores • 4,550 Rows)", use_container_width=True):
                load_demo_dataset()
                st.rerun()

        with col_btn2:
            csv_sample_path = os.path.join(PROJECT_ROOT, "data", "indian_retail_sales_sample.csv")
            if os.path.exists(csv_sample_path):
                with open(csv_sample_path, "rb") as f_csv:
                    st.download_button(
                        label="📥 Download Sample CSV Dataset",
                        data=f_csv.read(),
                        file_name="retail_sales_sample.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

    with col_hero_right:
        st.markdown("### 🏬 **Retail Sample Catalog**")
        st.markdown(
            """
            <div class="panel-card-clean">
                <p style="color:#F8FAFC; font-weight:700; margin-bottom:8px;">Supercenter Locations:</p>
                <p style="color:#94A3B8; font-size:0.85rem; line-height:1.5;">
                    • Mumbai (Bandra West)<br>
                    • Delhi (Connaught Place)<br>
                    • Bengaluru (Indiranagar)<br>
                    • Hyderabad (Hitec City)<br>
                    • Chennai (T.Nagar)
                </p>
                
                <p style="color:#F8FAFC; font-weight:700; margin-bottom:8px; margin-top:14px;">Products & INR Pricing:</p>
                <p style="color:#94A3B8; font-size:0.85rem; line-height:1.5;">
                    • Aashirvaad Atta 5kg (₹265)<br>
                    • India Gate Basmati 5kg (₹480)<br>
                    • Amul Butter 500g (₹275)<br>
                    • Tata Tea Gold 500g (₹320)<br>
                    • Maggi Noodles Pack of 12 (₹168)
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==================== STATE 2: ACTIVE DASHBOARD (POST-UPLOAD) ====================
else:
    df_sales = st.session_state.user_dataset
    df_fcst = st.session_state.forecast_dataset
    df_anom = st.session_state.anomaly_dataset
    meta = st.session_state.dataset_meta

    df_active_stockouts = get_active_stockouts(df_sales)
    active_stockout_count = len(df_active_stockouts)
    total_anomalies_count = len(df_anom[df_anom["acknowledged"] == False]) if (df_anom is not None and not df_anom.empty) else 0

    # Top Header Bar with Active File Badge & Reset
    col_head_left, col_head_right = st.columns([3, 1.2])

    with col_head_left:
        badge_style = "color:#EF4444; background:rgba(239, 68, 68, 0.15); border:1px solid rgba(239, 68, 68, 0.35);" if active_stockout_count > 0 else "color:#10B981; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16, 185, 129, 0.35);"
        badge_text = f"{active_stockout_count} Current Stockout Alert{'s' if active_stockout_count != 1 else ''}" if active_stockout_count > 0 else "0 Current Stockout Alerts"
        
        st.markdown(
            f"""
            <div class="top-header-bar" style="margin-bottom:0.5rem;">
                <div class="header-brand">
                    <div class="header-logo-icon">₹</div>
                    <div>
                        <h2 class="header-brand-title">RetailPulse</h2>
                        <div style="font-size:0.75rem; color:#94A3B8; font-weight:600;">Active Dataset: <b>{meta['file_name']}</b> ({meta['total_rows']:,} records • {meta['stores_count']} stores • {meta['skus_count']} SKUs)</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span class="header-status-pill">● Currency: INR (₹)</span>
                    <span style="font-size:0.8rem; font-weight:700; {badge_style} padding:4px 10px; border-radius:9999px;">{badge_text}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_head_right:
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Upload Different Dataset", use_container_width=True):
            st.session_state.user_dataset = None
            st.session_state.dataset_meta = None
            st.session_state.forecast_dataset = None
            st.session_state.anomaly_dataset = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Top Navigation Tabs
    tab_overview, tab_forecast, tab_alerts, tab_data_table, tab_architecture = st.tabs([
        "📊 Executive Overview",
        "📈 14-Day Demand Forecast (INR)",
        f"🚨 Inventory Incident Feed ({total_anomalies_count})",
        "📄 Uploaded Data Table",
        "🏛️ System Architecture"
    ])

    # ---------- TAB 1: EXECUTIVE OVERVIEW ----------
    with tab_overview:
        total_sales_units = int(df_sales["qty_sold"].sum())
        total_rev = float(df_sales["revenue"].sum())
        total_fcst_qty = int(df_fcst["forecast_qty"].sum()) if (df_fcst is not None and not df_fcst.empty) else 0

        # 4 High-Contrast KPI Cards with Semantic Color Top Borders
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.markdown(
                f"""
                <div class="stat-card-clean blue-top">
                    <div class="stat-eyebrow-clean">TOTAL SALES VOLUME <span>🏬 {meta['stores_count']} Stores</span></div>
                    <div class="stat-val-clean">{total_sales_units:,} <span style="font-size:0.95rem; font-weight:600; color:#94A3B8;">units</span></div>
                    <div class="stat-sub-clean"><span style="color:#60A5FA; font-weight:700;">{meta['date_start']}</span> to <span style="color:#60A5FA; font-weight:700;">{meta['date_end']}</span></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k2:
            st.markdown(
                f"""
                <div class="stat-card-clean white-top">
                    <div class="stat-eyebrow-clean">GROSS TURNOVER <span>₹ INR</span></div>
                    <div class="stat-val-clean">{format_inr(total_rev)}</div>
                    <div class="stat-sub-clean"><span style="color:#FFFFFF; font-weight:700;">₹{(total_rev/total_sales_units if total_sales_units>0 else 185.0):.2f}</span> avg price per unit</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k3:
            st.markdown(
                f"""
                <div class="stat-card-clean cyan-top">
                    <div class="stat-eyebrow-clean">14-DAY FORECAST DEMAND <span>🔮 XGBoost</span></div>
                    <div class="stat-val-clean" style="color:#22D3EE;">{total_fcst_qty:,} <span style="font-size:0.95rem; font-weight:600; color:#94A3B8;">units</span></div>
                    <div class="stat-sub-clean"><span style="color:#06B6D4; font-weight:700;">Dynamic Projection</span> across {meta['skus_count']} SKUs</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k4:
            if active_stockout_count > 0:
                st.markdown(
                    f"""
                    <div class="stat-card-clean red-top">
                        <div class="stat-eyebrow-clean">CRITICAL RESTOCK ALERTS <span>🚨 Shelf Sensors</span></div>
                        <div class="stat-val-clean" style="color:#EF4444;">{active_stockout_count} <span style="font-size:0.95rem; font-weight:600; color:#FCA5A5;">items</span></div>
                        <div class="stat-sub-clean"><span style="color:#EF4444; font-weight:700;">Immediate Reorder</span> needed</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="stat-card-clean green-top">
                        <div class="stat-eyebrow-clean">CRITICAL RESTOCK ALERTS <span>🚨 Shelf Sensors</span></div>
                        <div class="stat-val-clean" style="color:#10B981;">0 <span style="font-size:0.95rem; font-weight:600; color:#6EE7B7;">items</span></div>
                        <div class="stat-sub-clean"><span style="color:#10B981; font-weight:700;">All shelves stocked</span> — no reorder needed</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # 2-Column Responsive Body
        col_chart_area, col_side_area = st.columns([1.8, 1])

        with col_chart_area:
            st.markdown(
                """
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div style="font-size:1.15rem; font-weight:700; color:#FFFFFF;">📈 <b>Sales Demand Trajectory & 14-Day ML Forecast</b></div>
                    <div style="display:flex; align-items:center; gap:6px; background:rgba(6, 182, 212, 0.12); padding:3px 10px; border-radius:9999px; border:1px solid rgba(6, 182, 212, 0.3);">
                        <span class="live-pulse-dot live-pulse-cyan"></span>
                        <span style="font-size:0.75rem; font-weight:700; color:#22D3EE; letter-spacing:0.03em;">DYNAMIC INFERENCE ENGINE</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.caption("Historical daily volume overlaid with forward 14-day machine learning predictions:")

            daily = df_sales.groupby("date")["qty_sold"].sum().reset_index()
            daily["dt"] = pd.to_datetime(daily["date"])
            daily = daily.sort_values("dt").reset_index(drop=True)
            recent_daily = daily.tail(60).copy()

            fig_trend = go.Figure()

            # Actual Sales (Electric Blue)
            trace_actual = go.Scatter(
                x=recent_daily["dt"],
                y=recent_daily["qty_sold"],
                mode="lines+markers",
                name="Actual Daily Sales (Units)",
                line=dict(color="#3B82F6", width=2.5),
                marker=dict(size=4, color="#2563EB"),
                hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#3B82F6;'>●</span> Actual Sales: <b>%{y:,} units</b><extra></extra>"
            )
            fig_trend.add_trace(trace_actual)

            # 14-Day Forecast (Cyan)
            if df_fcst is not None and not df_fcst.empty:
                future_agg = df_fcst.groupby("date").agg(
                    fcst=("forecast_qty", "sum"),
                    lower=("lower_ci", "sum"),
                    upper=("upper_ci", "sum")
                ).reset_index()
                future_agg["dt"] = pd.to_datetime(future_agg["date"])

                trace_band = go.Scatter(
                    x=pd.concat([future_agg["dt"], future_agg["dt"][::-1]]),
                    y=pd.concat([future_agg["upper"], future_agg["lower"][::-1]]),
                    fill='toself',
                    fillcolor='rgba(6, 182, 212, 0.12)',
                    line=dict(color='rgba(6, 182, 212, 0.35)'),
                    name='80% Prediction Band',
                    hoverinfo="skip"
                )
                trace_fcst = go.Scatter(
                    x=future_agg["dt"],
                    y=future_agg["fcst"],
                    mode="lines+markers",
                    name="14-Day ML Forecast",
                    line=dict(color="#06B6D4", width=3, dash="dash"),
                    marker=dict(size=5, color="#0891B2"),
                    hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#06B6D4;'>●</span> 14-Day Forecast: <b>%{y:.1f} units</b><extra></extra>"
                )
                fig_trend.add_trace(trace_band)
                fig_trend.add_trace(trace_fcst)

                # Progressive animated frames for dynamic rollout
                frames = []
                for step in range(1, len(future_agg) + 1):
                    sub_f = future_agg.iloc[:step]
                    frames.append(go.Frame(
                        data=[
                            trace_actual,
                            go.Scatter(
                                x=pd.concat([sub_f["dt"], sub_f["dt"][::-1]]),
                                y=pd.concat([sub_f["upper"], sub_f["lower"][::-1]]),
                                fill='toself',
                                fillcolor='rgba(6, 182, 212, 0.14)',
                                line=dict(color='rgba(6, 182, 212, 0.4)'),
                                name='80% Prediction Band',
                                hoverinfo="skip"
                            ),
                            go.Scatter(
                                x=sub_f["dt"],
                                y=sub_f["fcst"],
                                mode="lines+markers",
                                name="14-Day ML Forecast",
                                line=dict(color="#06B6D4", width=3, dash="dash"),
                                marker=dict(size=6, color="#22D3EE"),
                                hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#06B6D4;'>●</span> 14-Day Forecast: <b>%{y:.1f} units</b><extra></extra>"
                            )
                        ],
                        name=f"trend_step_{step}"
                    ))
                fig_trend.frames = frames

                fig_trend.update_layout(
                    updatemenus=[
                        dict(
                            type="buttons",
                            direction="left",
                            x=0.0, y=1.16,
                            xanchor="left", yanchor="top",
                            showactive=False,
                            bgcolor="#1E293B",
                            bordercolor="#334155",
                            borderwidth=1,
                            font=dict(color="#FFFFFF", size=11, family="Plus Jakarta Sans"),
                            buttons=[
                                dict(
                                    label="▶ Play Forecast Rollout",
                                    method="animate",
                                    args=[
                                        None,
                                        dict(
                                            frame=dict(duration=130, redraw=True),
                                            fromcurrent=True,
                                            transition=dict(duration=70, easing="cubic-in-out"),
                                            mode="immediate"
                                        )
                                    ]
                                ),
                                dict(
                                    label="↺ Reset View",
                                    method="animate",
                                    args=[
                                        [f"trend_step_{len(future_agg)}"],
                                        dict(
                                            frame=dict(duration=0, redraw=True),
                                            transition=dict(duration=0),
                                            mode="immediate"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )

            fig_trend.update_layout(
                paper_bgcolor="#0F172A",
                plot_bgcolor="#0F172A",
                height=380,
                margin=dict(l=15, r=15, t=15, b=15),
                font=dict(family="Plus Jakarta Sans", color="#FFFFFF", size=12),
                legend=dict(orientation="h", y=1.05, x=1, xanchor="right", font=dict(color="#FFFFFF")),
                xaxis=dict(showgrid=True, gridcolor="#1E293B", title="Transaction Date", color="#94A3B8"),
                yaxis=dict(showgrid=True, gridcolor="#1E293B", title="Daily Volume (Units)", color="#94A3B8"),
                hovermode="x unified",
                transition=dict(duration=500, easing="cubic-in-out"),
                uirevision="trend_view"
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with col_side_area:
            st.markdown("### 🚨 **Urgent Restock Action Items**")
            st.caption("Depleted inventory requiring replenishment:")

            if active_stockout_count > 0:
                for _, row in df_active_stockouts.head(5).iterrows():
                    st.markdown(
                        f"""
                        <div class="action-row-item danger">
                            <div>
                                <div style="font-weight:700; color:#FFFFFF; font-size:0.92rem;">🏬 {row['store_id']} &nbsp;—&nbsp; 📦 {row['sku']}</div>
                                <div style="font-size:0.78rem; color:#94A3B8; margin-top:2px;">Shelf: <b>{row['shelf_qty']:.1f} units left</b> • Reorder: <b>+35 units</b></div>
                            </div>
                            <span style="background:rgba(239, 68, 68, 0.2); color:#EF4444; font-weight:700; font-size:0.72rem; padding:3px 8px; border-radius:4px; border:1px solid rgba(239, 68, 68, 0.4);">ACTION REQ</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.success("✅ All store shelves currently have sufficient inventory!")
                st.caption("All currently monitored shelves have sufficient inventory.")

            st.markdown("---")
            st.markdown("### 🍩 **Sales Share by Store**")
            store_shares = df_sales.groupby("store_id")["qty_sold"].sum().reset_index()
            donut_fig = px.pie(
                store_shares,
                values="qty_sold",
                names="store_id",
                color="store_id",
                color_discrete_sequence=["#3B82F6", "#06B6D4", "#8B5CF6", "#F59E0B", "#10B981"],
                hole=0.6
            )
            donut_fig.update_traces(
                textposition='inside',
                textinfo='percent',
                hovertemplate="<b>%{label}</b><br>Sales Volume: <b>%{value:,} units</b><br>Store Share: <b>%{percent}</b><extra></extra>"
            )
            donut_fig.update_layout(
                paper_bgcolor="#0F172A",
                plot_bgcolor="#0F172A",
                height=250,
                margin=dict(l=5, r=5, t=5, b=5),
                font=dict(family="Plus Jakarta Sans", color="#FFFFFF"),
                legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", font=dict(color="#94A3B8")),
                transition=dict(duration=500, easing="cubic-in-out")
            )
            st.plotly_chart(donut_fig, use_container_width=True)

    # ---------- TAB 2: 14-DAY DEMAND FORECAST ----------
    with tab_forecast:
        st.markdown(
            """
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <div style="font-size:1.35rem; font-weight:800; color:#FFFFFF;">📈 <b>14-Day Demand Forecast Explorer (INR ₹)</b></div>
                <div style="display:flex; align-items:center; gap:6px; background:rgba(16, 185, 129, 0.12); padding:4px 12px; border-radius:9999px; border:1px solid rgba(16, 185, 129, 0.3);">
                    <span class="live-pulse-dot"></span>
                    <span style="font-size:0.75rem; font-weight:700; color:#34D399; letter-spacing:0.03em;">ACTIVE SENSOR STREAM</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<p style='color:#94A3B8; margin-top:-6px;'>Select any store and SKU to inspect machine learning predictions, animated forecast rollouts, and shelf telemetry.</p>", unsafe_allow_html=True)

        stores = sorted(df_sales["store_id"].unique().tolist())
        skus = sorted(df_sales["sku"].unique().tolist())

        f1, f2, f3 = st.columns([1, 1, 1.2])
        with f1:
            sel_store = st.selectbox("Store Location", stores, index=0)
        with f2:
            sel_sku = st.selectbox("Product SKU", skus, index=0)
        with f3:
            sel_horizon = st.slider("Forecast Horizon (Days)", min_value=7, max_value=28, value=14, step=7)

        hist_data = df_sales[(df_sales["store_id"] == sel_store) & (df_sales["sku"] == sel_sku)].sort_values("date")
        pred_data = df_fcst[(df_fcst["store_id"] == sel_store) & (df_fcst["sku"] == sel_sku)].sort_values("date").head(sel_horizon) if df_fcst is not None else pd.DataFrame()

        if hist_data.empty:
            st.info("No records found for this combination.")
        else:
            st.markdown(f"#### **{sel_store} — {sel_sku} Forecast Trajectory**")
            hist_data["dt"] = pd.to_datetime(hist_data["date"])
            recent_hist = hist_data.tail(45).copy()

            fig_sku = go.Figure()

            # Actual Daily Sales (Solid Blue)
            trace_sku_actual = go.Scatter(
                x=recent_hist["dt"], y=recent_hist["qty_sold"], mode="lines+markers", name="Actual Daily Sales (Units)",
                line=dict(color="#3B82F6", width=2.5),
                marker=dict(size=4, color="#2563EB"),
                hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#3B82F6;'>●</span> Actual: <b>%{y:,} units</b><extra></extra>"
            )
            fig_sku.add_trace(trace_sku_actual)

            # Shelf Sensor Stock Level (Dashed Orange)
            trace_sku_shelf = go.Scatter(
                x=recent_hist["dt"], y=recent_hist["avg_shelf_qty"], mode="lines", name="Shelf Sensor Stock Level",
                line=dict(color="#F59E0B", width=2, dash="dash"),
                hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#F59E0B;'>●</span> Shelf Stock: <b>%{y:.1f} units</b><extra></extra>"
            )
            fig_sku.add_trace(trace_sku_shelf)

            if not pred_data.empty:
                pred_data["dt"] = pd.to_datetime(pred_data["date"])
                trace_sku_band = go.Scatter(
                    x=pd.concat([pred_data["dt"], pred_data["dt"][::-1]]),
                    y=pd.concat([pred_data["upper_ci"], pred_data["lower_ci"][::-1]]),
                    fill='toself', fillcolor='rgba(6, 182, 212, 0.12)',
                    line=dict(color='rgba(6, 182, 212, 0.35)'), name='80% Prediction Band',
                    hoverinfo="skip"
                )
                trace_sku_fcst = go.Scatter(
                    x=pred_data["dt"], y=pred_data["forecast_qty"], mode="lines+markers", name="14-Day ML Forecast",
                    line=dict(color="#06B6D4", width=3, dash="dot"),
                    marker=dict(size=5, color="#0891B2"),
                    hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#06B6D4;'>●</span> ML Forecast: <b>%{y:.1f} units</b><extra></extra>"
                )
                fig_sku.add_trace(trace_sku_band)
                fig_sku.add_trace(trace_sku_fcst)

                # Progressive animated frames for SKU forecast rollout
                frames_sku = []
                for step in range(1, len(pred_data) + 1):
                    sub_p = pred_data.iloc[:step]
                    frames_sku.append(go.Frame(
                        data=[
                            trace_sku_actual,
                            trace_sku_shelf,
                            go.Scatter(
                                x=pd.concat([sub_p["dt"], sub_p["dt"][::-1]]),
                                y=pd.concat([sub_p["upper_ci"], sub_p["lower_ci"][::-1]]),
                                fill='toself', fillcolor='rgba(6, 182, 212, 0.14)',
                                line=dict(color='rgba(6, 182, 212, 0.4)'), name='80% Prediction Band',
                                hoverinfo="skip"
                            ),
                            go.Scatter(
                                x=sub_p["dt"], y=sub_p["forecast_qty"], mode="lines+markers", name="14-Day ML Forecast",
                                line=dict(color="#06B6D4", width=3, dash="dot"),
                                marker=dict(size=6, color="#22D3EE"),
                                hovertemplate="<b>%{x|%b %d, %Y}</b><br><span style='color:#06B6D4;'>●</span> ML Forecast: <b>%{y:.1f} units</b><extra></extra>"
                            )
                        ],
                        name=f"sku_step_{step}"
                    ))
                fig_sku.frames = frames_sku

                fig_sku.update_layout(
                    updatemenus=[
                        dict(
                            type="buttons",
                            direction="left",
                            x=0.0, y=1.16,
                            xanchor="left", yanchor="top",
                            showactive=False,
                            bgcolor="#1E293B",
                            bordercolor="#334155",
                            borderwidth=1,
                            font=dict(color="#FFFFFF", size=11, family="Plus Jakarta Sans"),
                            buttons=[
                                dict(
                                    label="▶ Animate Forecast Rollout",
                                    method="animate",
                                    args=[
                                        None,
                                        dict(
                                            frame=dict(duration=130, redraw=True),
                                            fromcurrent=True,
                                            transition=dict(duration=70, easing="cubic-in-out"),
                                            mode="immediate"
                                        )
                                    ]
                                ),
                                dict(
                                    label="↺ Full Horizon",
                                    method="animate",
                                    args=[
                                        [f"sku_step_{len(pred_data)}"],
                                        dict(
                                            frame=dict(duration=0, redraw=True),
                                            transition=dict(duration=0),
                                            mode="immediate"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )

            fig_sku.update_layout(
                paper_bgcolor="#0F172A", plot_bgcolor="#0F172A", height=380,
                font=dict(family="Plus Jakarta Sans", color="#FFFFFF"),
                xaxis=dict(showgrid=True, gridcolor="#1E293B", title="Date", color="#94A3B8"),
                yaxis=dict(showgrid=True, gridcolor="#1E293B", title="Quantity (Units)", color="#94A3B8"),
                legend=dict(orientation="h", y=1.05, x=1, xanchor="right", font=dict(color="#FFFFFF")),
                hovermode="x unified",
                transition=dict(duration=500, easing="cubic-in-out"),
                uirevision="sku_view"
            )
            st.plotly_chart(fig_sku, use_container_width=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("Avg Daily Demand", f"{hist_data['qty_sold'].mean():.1f} units")
            with sc2:
                st.metric("Current Shelf Reading", f"{hist_data['avg_shelf_qty'].iloc[-1]:.1f} units")
            with sc3:
                st.metric("Total Revenue (INR)", format_inr(hist_data['revenue'].sum()))
            with sc4:
                st.metric(f"Next {sel_horizon}-Day Forecast", f"{pred_data['forecast_qty'].sum():.0f} units" if not pred_data.empty else "N/A")

            # CSV Download
            st.markdown("<br>", unsafe_allow_html=True)
            if not pred_data.empty:
                csv_bytes = pred_data[["date", "store_id", "sku", "forecast_qty", "lower_ci", "upper_ci"]].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download {sel_store} {sel_sku} Forecast CSV",
                    data=csv_bytes,
                    file_name=f"forecast_{sel_store}_{sel_sku}.csv",
                    mime="text/csv"
                )

    # ---------- TAB 3: INVENTORY ANOMALIES FEED ----------
    with tab_alerts:
        st.markdown("## 🚨 **Inventory Anomaly Incident Feed**")
        st.markdown("<p style='color:#94A3B8; margin-top:-10px;'>Live feed of empty shelves, sudden demand spikes, and sensor irregularities with real-time severity scoring.</p>", unsafe_allow_html=True)

        if df_anom is None or df_anom.empty:
            st.success("✅ No inventory anomalies detected in the uploaded dataset.")
        else:
            for idx, row in df_anom.iterrows():
                anom_id = row["id"]
                is_ack = row.get("acknowledged", False)
                anom_type = str(row.get("anomaly_type", "")).strip().lower()
                sev = str(row.get("severity", "medium")).lower()

                if anom_type in ["stockout", "stockout_risk"]:
                    type_label = "STOCKOUT"
                    badge_color = "#EF4444"
                    type_badge_html = '<span style="color:#EF4444; font-weight:700; font-size:0.75rem; background:rgba(239, 68, 68, 0.15); padding:3px 10px; border-radius:6px; border:1px solid rgba(239, 68, 68, 0.35);">STOCKOUT</span>'
                elif anom_type in ["demand_spike", "spike"]:
                    type_label = "DEMAND SPIKE"
                    badge_color = "#06B6D4"
                    type_badge_html = '<span style="color:#06B6D4; font-weight:700; font-size:0.75rem; background:rgba(6, 182, 212, 0.15); padding:3px 10px; border-radius:6px; border:1px solid rgba(6, 182, 212, 0.35);">DEMAND SPIKE</span>'
                elif anom_type in ["sensor_mismatch", "sensor_anomaly", "sensor_error"]:
                    type_label = "SENSOR ANOMALY"
                    badge_color = "#8B5CF6"
                    type_badge_html = '<span style="color:#A78BFA; font-weight:700; font-size:0.75rem; background:rgba(139, 92, 246, 0.15); padding:3px 10px; border-radius:6px; border:1px solid rgba(139, 92, 246, 0.35);">SENSOR ANOMALY</span>'
                else:
                    type_label = anom_type.upper().replace("_", " ")
                    badge_color = "#F59E0B"
                    type_badge_html = f'<span style="color:#F59E0B; font-weight:700; font-size:0.75rem; background:rgba(245, 158, 11, 0.15); padding:3px 10px; border-radius:6px; border:1px solid rgba(245, 158, 11, 0.35);">{type_label}</span>'

                sev_color = "#EF4444" if sev == "high" else ("#F59E0B" if sev == "medium" else "#94A3B8")
                sev_badge_html = f'<span style="color:{sev_color}; font-weight:700; font-size:0.75rem; background:rgba(255, 255, 255, 0.05); padding:3px 10px; border-radius:6px; border:1px solid {sev_color}44;">{sev.upper()} SEVERITY</span>'

                delay_ms = min(idx * 35, 400)
                c_text, c_btn = st.columns([4.2, 1])
                with c_text:
                    st.markdown(
                        f"""
                        <div class="incident-card" style="border-left:4px solid {badge_color}; animation-delay:{delay_ms}ms;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:700; color:#FFFFFF; font-size:0.96rem;">🏬 {row['store_id']} &nbsp;—&nbsp; 📦 {row['sku']}</span>
                                <div style="display:flex; gap:6px;">
                                    {type_badge_html}
                                    {sev_badge_html}
                                </div>
                            </div>
                            <p style="color:#CBD5E1; font-size:0.86rem; margin:8px 0 6px 0; line-height:1.5;">{row['description']}</p>
                            <span style="color:#94A3B8; font-size:0.78rem;">Detected on <b>{row['date']}</b> • Anomaly Score: <b>{row['score']}</b> • Status: {'<span style="color:#10B981; font-weight:700;">✅ Resolved</span>' if is_ack else '<span style="color:#EF4444; font-weight:700;">🔴 Pending Review</span>'}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with c_btn:
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    if not is_ack:
                        if st.button("Acknowledge", key=f"ack_btn_{anom_id}", use_container_width=True):
                            st.session_state.anomaly_dataset.loc[st.session_state.anomaly_dataset["id"] == anom_id, "acknowledged"] = True
                            st.toast(f"Incident {anom_id} marked as acknowledged!", icon="✅")
                            st.rerun()
                    else:
                        st.markdown("<p style='color:#10B981; font-weight:700; font-size:0.88rem; margin-top:14px; text-align:center;'>✓ Resolved</p>", unsafe_allow_html=True)

    # ---------- TAB 4: RAW DATA TABLE & STATS ----------
    with tab_data_table:
        st.markdown("## 📄 **Uploaded Dataset Records & Schema Summary**")
        st.markdown(f"<p style='color:#94A3B8; margin-top:-10px;'>Displaying first 100 rows of <b>{meta['file_name']}</b> ({meta['total_rows']:,} total records):</p>", unsafe_allow_html=True)

        st.dataframe(df_sales.head(100), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        csv_full = df_sales.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Standardized Dataset as CSV",
            data=csv_full,
            file_name="standardized_sales_dataset.csv",
            mime="text/csv"
        )

    # ---------- TAB 5: SYSTEM ARCHITECTURE ----------
    with tab_architecture:
        st.markdown("## 🏛️ **System Architecture & Production ML Pipeline**")
        st.markdown("<p style='color:#94A3B8; margin-top:-10px;'>A transparent, code-accurate view of the unified data engineering, machine learning, and operational serving architecture.</p>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_mode_a, col_mode_b = st.columns(2)

        with col_mode_a:
            st.markdown(
                """
                <div class="panel-card-clean" style="border-left: 4px solid #3B82F6;">
                    <div style="font-size:1.05rem; font-weight:700; color:#FFFFFF; margin-bottom:8px;">
                        ⚙️ <b>1. Data Engineering & Lakehouse Curation</b>
                    </div>
                    <p style="color:#94A3B8; font-size:0.85rem; line-height:1.6; margin-bottom:12px;">
                        End-to-end ingestion and ACID-compliant lakehouse storage:
                    </p>
                    <div style="color:#CBD5E1; font-size:0.85rem; line-height:1.7;">
                        <b>• Raw Ingestion:</b> POS sales transactions & IoT shelf sensor streams loaded into <code>data/raw_sample/sales_raw.csv</code> and MinIO S3.<br>
                        <b>• Lakehouse Transform:</b> Pandas & Spark data cleaning, null handling, IoT shelf telemetry joining, and customer sentiment scoring.<br>
                        <b>• Curated Storage:</b> Persisted to partitioned Delta Lake & Parquet format at <code>data/curated/sales_daily.parquet</code>.<br>
                        <b>• Data Quality Gate:</b> Automated schema validation, range checks, and null constraint enforcement.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_mode_b:
            st.markdown(
                """
                <div class="panel-card-clean" style="border-left: 4px solid #06B6D4;">
                    <div style="font-size:1.05rem; font-weight:700; color:#FFFFFF; margin-bottom:8px;">
                        🔮 <b>2. XGBoost Champion ML & Serving Engine</b>
                    </div>
                    <p style="color:#94A3B8; font-size:0.85rem; line-height:1.6; margin-bottom:12px;">
                        Production-grade gradient boosted forecasting & operational microservices:
                    </p>
                    <div style="color:#CBD5E1; font-size:0.85rem; line-height:1.7;">
                        <b>• Feature Engineering:</b> 28-day autoregressive lags (<code>qty_lag_1..28</code>), rolling statistics (7/14/28-day mean & std), and calendar seasonality.<br>
                        <b>• Model Training:</b> 250-tree XGBoost Champion Model evaluated with holdout backtesting (<b>61.47% MAPE</b>) and logged to MLflow.<br>
                        <b>• Anomaly Triage:</b> Automated 3-sigma demand surge detection and IoT shelf depletion stockout scoring.<br>
                        <b>• Operational Serving:</b> Relational warehouse synchronization (<code>data/warehouse.db</code> / Postgres), FastAPI microservices (<code>:8001-:8003</code>), and interactive dashboard.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background:#111827; border:1px solid #1F2937; border-radius:12px; padding:14px 18px;">
                <span style="font-weight:700; color:#FFFFFF; font-size:0.92rem;">💡 Architectural Flow Summary</span>
                <p style="color:#94A3B8; font-size:0.85rem; margin:6px 0 0 0; line-height:1.6;">
                    <b>Batch Execution:</b> <code>Raw CSV</code> → <code>Batch Loader</code> → <code>MinIO S3</code> → <code>Transform</code> → <code>Delta Lake</code> → <code>XGBoost / Prophet</code> → <code>FastAPI Services (:8001-:8003)</code><br>
                    <b>Interactive Dashboard:</b> <code>User Upload</code> → <code>In-Memory Processing</code> → <code>Feature Engineering</code> → <code>Forecast & Anomaly Engine</code> → <code>Streamlit BI</code>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
