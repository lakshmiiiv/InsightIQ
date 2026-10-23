import sqlite3
import pandas as pd

conn = sqlite3.connect("insightiq.db")

query = """
SELECT strftime('%Y-%m', o.order_date) AS month,
       SUM(p.price * o.quantity) AS monthly_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY month
ORDER BY month;
"""

df = pd.read_sql_query(query, conn)
conn.close()

# Calculate % change month-over-month
df["pct_change"] = df["monthly_revenue"].pct_change() * 100
df["pct_change"] = df["pct_change"].round(2)

print(df)

# Flag months where revenue dropped more than 10%
flagged = df[df["pct_change"] < -10]
print("\nFlagged months (revenue dropped >10%):")
print(flagged)