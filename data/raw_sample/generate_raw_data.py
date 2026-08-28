import csv
from datetime import datetime, timedelta
import math
import os
import random

def generate_data():
    print("Generating synthetic retail data...")
    
    # Configuration
    stores = [f"STORE_{i:03d}" for i in range(1, 6)]
    skus = [f"SKU_{i:03d}" for i in range(1, 11)]
    channels = ["online", "in-store"]
    
    # Base prices for SKUs
    sku_prices = {
        "SKU_001": 12.99,
        "SKU_002": 24.50,
        "SKU_003": 5.99,
        "SKU_004": 49.99,
        "SKU_005": 8.75,
        "SKU_006": 15.00,
        "SKU_007": 32.20,
        "SKU_008": 9.99,
        "SKU_009": 115.00,
        "SKU_010": 18.50
    }
    
    # 1. Generate Reviews Data
    reviews_data = [
        ("SKU_001", "This product is amazing! Highly recommended and works perfectly."),
        ("SKU_001", "Terrible customer service and the product broke after two days of light usage."),
        ("SKU_001", "Decent value for the price. Not the best, but gets the job done."),
        ("SKU_002", "Absolutely love this SKU! Excellent build quality and design."),
        ("SKU_002", "It is okay. A bit overpriced for what it offers but works fine."),
        ("SKU_003", "Awful. Did not work out of the box. Returning immediately."),
        ("SKU_003", "Cheaply made, but it was very cheap so I cannot complain too much."),
        ("SKU_004", "Premium quality! Highly satisfied with this purchase."),
        ("SKU_005", "Average quality, nothing special. Neutral feelings."),
        ("SKU_006", "Great deal! Works perfectly and shipping was super fast."),
        ("SKU_006", "Horrible. Avoid at all costs."),
        ("SKU_007", "Amazing product, does exactly what it says on the box."),
        ("SKU_008", "Very disappointing. Stopped working after a week."),
        ("SKU_009", "Extremely premium. Best purchase I have made this year! Excellent product."),
        ("SKU_010", "Good, standard item. No issues so far.")
    ]
    
    reviews_file = os.path.join("data", "raw_sample", "reviews_raw.csv")
    with open(reviews_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "review_text"])
        writer.writerows(reviews_data)
    print(f"Saved reviews data to {reviews_file}")
    
    # 2. Generate Sales Data
    # Cover ~2 years: 2024-01-01 to 2025-12-31
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    delta_days = (end_date - start_date).days + 1
    
    sales_file = os.path.join("data", "raw_sample", "sales_raw.csv")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(sales_file), exist_ok=True)
    
    with open(sales_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["store_id", "sku", "ts", "qty_sold", "price", "channel"])
        
        row_count = 0
        
        # We generate transactions day-by-day
        for day_offset in range(delta_days):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Seasonality coefficients
            # Weekly (Saturday/Sunday have more sales)
            weekday = current_date.weekday()
            week_coeff = 1.4 if weekday >= 5 else 0.9
            
            # Yearly (December peak, January dip)
            month = current_date.month
            year_coeff = 1.3 if month == 12 else (0.8 if month == 1 else 1.0)
            
            for store in stores:
                # Add store-specific volume scale
                store_scale = 1.2 if store == "STORE_001" else 0.9
                
                for sku in skus:
                    base_price = sku_prices[sku]
                    
                    # Probability of sale today
                    sku_popularity = (int(sku.split("_")[1]) % 3 + 1) * 0.25 # ranges from 0.25 to 0.75
                    sale_prob = 0.4 * sku_popularity * week_coeff * year_coeff * store_scale
                    
                    if random.random() < sale_prob:
                        # Determine quantity sold
                        base_qty = int(sku.split("_")[1]) % 4 + 1
                        qty = int(base_qty * week_coeff * year_coeff * store_scale * (random.uniform(0.7, 1.3)))
                        qty = max(1, qty)
                        
                        # Generate 1 to 3 transactions per active SKU/store/day combo
                        num_trans = random.randint(1, 3)
                        for t in range(num_trans):
                            # Distribute timestamps randomly throughout the day (8:00 AM to 10:00 PM)
                            hour = random.randint(8, 21)
                            minute = random.randint(0, 59)
                            second = random.randint(0, 59)
                            ts_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"
                            
                            price = base_price
                            qty_sold = qty
                            channel = random.choice(channels)
                            
                            # Inject some data anomalies for Spark clean_join verification
                            # 1. Null qty_sold (0.5% chance)
                            if random.random() < 0.005:
                                qty_sold = ""
                            
                            # 2. Null price (0.5% chance)
                            if random.random() < 0.005:
                                price = ""
                                
                            writer.writerow([store, sku, ts_str, qty_sold, price, channel])
                            row_count += 1
                            
    print(f"Saved {row_count} raw sales events to {sales_file}")

if __name__ == "__main__":
    generate_data()
