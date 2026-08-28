import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_indian_retail_dataset():
    np.random.seed(42)
    
    stores = [
        "MUMBAI_STORE_001",
        "DELHI_STORE_002",
        "BENGALURU_STORE_003",
        "HYDERABAD_STORE_004",
        "CHENNAI_STORE_005"
    ]
    
    products = [
        {"sku": "SKU_001_Aashirvaad_Atta_5kg", "category": "Staples", "price": 265.0, "base_demand": 14},
        {"sku": "SKU_002_IndiaGate_Basmati_5kg", "category": "Staples", "price": 480.0, "base_demand": 8},
        {"sku": "SKU_003_Fortune_Sunflower_Oil_1L", "category": "Edible Oils", "price": 145.0, "base_demand": 22},
        {"sku": "SKU_004_Amul_Butter_500g", "category": "Dairy", "price": 275.0, "base_demand": 18},
        {"sku": "SKU_005_Tata_Tea_Gold_500g", "category": "Beverages", "price": 320.0, "base_demand": 12},
        {"sku": "SKU_006_Tata_Salt_1kg", "category": "Staples", "price": 28.0, "base_demand": 35},
        {"sku": "SKU_007_Toor_Dal_Premium_1kg", "category": "Pulses", "price": 165.0, "base_demand": 16},
        {"sku": "SKU_008_Maggi_Noodles_12Pack", "category": "Snacks", "price": 168.0, "base_demand": 25},
        {"sku": "SKU_009_Cadbury_Dairy_Milk_Silk", "category": "Chocolates", "price": 95.0, "base_demand": 20},
        {"sku": "SKU_010_Surf_Excel_Matic_2kg", "category": "Home Care", "price": 390.0, "base_demand": 10}
    ]
    
    # 90 Days of history
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    
    records = []
    
    for d in dates:
        dt_str = d.strftime("%Y-%m-%d")
        is_weekend = d.weekday() in [5, 6]
        
        for store in stores:
            for p in products:
                # Weekend demand surge (1.4x)
                base = p["base_demand"]
                if is_weekend:
                    base = int(base * 1.45)
                    
                # Poisson distributed actual sales
                qty = int(np.random.poisson(max(1, base)))
                price = float(p["price"])
                revenue = round(qty * price, 2)
                
                # Synthetic shelf stock level (units)
                shelf_stock = int(np.random.uniform(15, 60))
                # Inject realistic low stock on specific stores
                if store == "MUMBAI_STORE_001" and p["sku"] == "SKU_004_Amul_Butter_500g" and d == dates[-1]:
                    shelf_stock = 0
                elif store == "BENGALURU_STORE_003" and p["sku"] == "SKU_005_Tata_Tea_Gold_500g" and d == dates[-1]:
                    shelf_stock = 2
                elif store == "DELHI_STORE_002" and p["sku"] == "SKU_001_Aashirvaad_Atta_5kg" and d == dates[-1]:
                    shelf_stock = 3
                    
                sentiment = round(float(np.random.uniform(0.20, 0.50)), 2)
                
                records.append({
                    "date": dt_str,
                    "store_id": store,
                    "sku": p["sku"],
                    "qty_sold": qty,
                    "price_inr": price,
                    "revenue_inr": revenue,
                    "shelf_sensor_stock": shelf_stock,
                    "customer_sentiment": sentiment
                })
                
    df = pd.DataFrame(records)
    
    os.makedirs("data", exist_ok=True)
    csv_path = os.path.join("data", "indian_retail_sales_sample.csv")
    xlsx_path = os.path.join("data", "indian_retail_sales_sample.xlsx")
    
    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(f"Generated {len(df):,} records successfully:")
    print(f"- CSV: {csv_path}")
    print(f"- Excel: {xlsx_path}")

if __name__ == "__main__":
    generate_indian_retail_dataset()
