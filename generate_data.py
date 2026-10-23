import pandas as pd
import random

random.seed(42)

# Customers
regions = ["North", "South", "East", "West"]
customers = pd.DataFrame({
    "customer_id": range(1, 51),
    "customer_name": [f"Customer_{i}" for i in range(1, 51)],
    "region": [random.choice(regions) for _ in range(50)]
})

# Products
categories = ["Electronics", "Clothing", "Home", "Sports", "Books"]
products = pd.DataFrame({
    "product_id": range(1, 31),
    "product_name": [f"Product_{i}" for i in range(1, 31)],
    "category": [random.choice(categories) for _ in range(30)],
    "price": [round(random.uniform(200, 5000), 2) for _ in range(30)]
})

# Orders
order_rows = []
for order_id in range(1, 501):
    order_rows.append({
        "order_id": order_id,
        "customer_id": random.randint(1, 50),
        "product_id": random.randint(1, 30),
        "quantity": random.randint(1, 5),
        "order_date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=random.randint(0, 270))
    })
orders = pd.DataFrame(order_rows)

# Save all three as CSVs
customers.to_csv("customers.csv", index=False)
products.to_csv("products.csv", index=False)
orders.to_csv("orders.csv", index=False)

print("Done! Created customers.csv, products.csv, orders.csv")