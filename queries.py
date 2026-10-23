import sqlite3
import pandas as pd

conn = sqlite3.connect("insightiq.db")

# Query 1: Total revenue by region
query1 = """
SELECT c.region,
       SUM(p.price * o.quantity) AS total_revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.region
ORDER BY total_revenue DESC;
"""

result1 = pd.read_sql_query(query1, conn)
print("Revenue by Region:")
print(result1)

# Query 2: Top 5 products by revenue
query2 = """
SELECT p.product_name,
       p.category,
       SUM(p.price * o.quantity) AS total_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.product_id
ORDER BY total_revenue DESC
LIMIT 5;
"""
result2 = pd.read_sql_query(query2, conn)
print("\nTop 5 Products:")
print(result2)

# Query 3: Monthly revenue trend
query3 = """
SELECT strftime('%Y-%m', o.order_date) AS month,
       SUM(p.price * o.quantity) AS monthly_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY month
ORDER BY month;
"""
result3 = pd.read_sql_query(query3, conn)
print("\nMonthly Revenue Trend:")
print(result3)

conn.close()