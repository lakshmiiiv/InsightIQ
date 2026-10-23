import sqlite3
import pandas as pd

# Connect to (or create) the database file
conn = sqlite3.connect("insightiq.db")

# Load each CSV and write it into the database as a table
customers = pd.read_csv("customers.csv")
products = pd.read_csv("products.csv")
orders = pd.read_csv("orders.csv")

customers.to_sql("customers", conn, if_exists="replace", index=False)
products.to_sql("products", conn, if_exists="replace", index=False)
orders.to_sql("orders", conn, if_exists="replace", index=False)

print("Done! Loaded customers, products, and orders into insightiq.db")

conn.close()