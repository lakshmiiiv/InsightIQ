import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from itertools import cycle

st.set_page_config(page_title="InsightIQ", layout="wide")
st.title("InsightIQ — AI Decision Analytics Platform")
st.caption("Upload any company's transaction CSV → SQL-style aggregation → root-cause driver analysis → churn → AI-explained report.")

PALETTE = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9", "#e66767", "#1baf7a"]
DARK_BG = "#1a1a19"

# ============================================================
# 1. Upload
# ============================================================
uploaded_file = st.file_uploader("Upload a transactions CSV (one row per order/sale)", type=["csv"])

if uploaded_file is None:
    st.info("Upload a CSV to get started. Tip: you can test this with the orders.csv you generated earlier before trying a real dataset.")
    st.stop()

try:
    raw_df = pd.read_csv(uploaded_file)
except UnicodeDecodeError:
    uploaded_file.seek(0)
    raw_df = pd.read_csv(uploaded_file, encoding="latin1")

st.subheader("Preview")
st.dataframe(raw_df.head(10), width='stretch')

# ============================================================
# 2. Column mapping
# ============================================================
st.subheader("Map your columns")
cols = raw_df.columns.tolist()
none_option = "— None —"

c1, c2, c3 = st.columns(3)
with c1:
    date_col = st.selectbox("Date column", cols)
    customer_col = st.selectbox("Customer ID column", cols)
with c2:
    region_col = st.selectbox("Region / area column (optional)", [none_option] + cols)
    product_col = st.selectbox("Product / category column (optional)", [none_option] + cols)
with c3:
    revenue_mode = st.radio("Revenue is...", ["A single amount column", "Quantity × Unit Price"])
    if revenue_mode == "A single amount column":
        revenue_col = st.selectbox("Revenue column", cols)
    else:
        qty_col = st.selectbox("Quantity column", cols)
        price_col = st.selectbox("Unit price column", cols)

if "analysis_run" not in st.session_state:
    st.session_state["analysis_run"] = False

if st.button("Run Analysis", type="primary"):
    st.session_state["analysis_run"] = True

if not st.session_state["analysis_run"]:
    st.stop()

# ============================================================
# 3. Build working dataframe
# ============================================================
df = raw_df.copy()
df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
bad_dates = int(df[date_col].isna().sum())
if bad_dates:
    st.warning(f"{bad_dates} row(s) had unparseable dates and were dropped.")
    df = df.dropna(subset=[date_col])

if revenue_mode == "A single amount column":
    df["revenue"] = pd.to_numeric(df[revenue_col], errors="coerce")
else:
    df["revenue"] = pd.to_numeric(df[qty_col], errors="coerce") * pd.to_numeric(df[price_col], errors="coerce")

bad_revenue = int(df["revenue"].isna().sum())
if bad_revenue:
    st.warning(f"{bad_revenue} row(s) had invalid revenue values and were dropped.")
df = df.dropna(subset=["revenue"])

df["month"] = df[date_col].dt.to_period("M").astype(str)

has_region = region_col != none_option
has_product = product_col != none_option

if df.empty:
    st.error("No valid rows left after cleaning. Check your column mapping.")
    st.stop()

# ============================================================
# 4. Root-cause / driver analysis (pure Python — no LLM involved)
# ============================================================
months_sorted = sorted(df["month"].unique())
seen_customers = set()
driver_records = []

for m in months_sorted:
    month_mask = df["month"] == m
    month_customers = set(df.loc[month_mask, customer_col])
    repeat = month_customers & seen_customers
    new = month_customers - seen_customers
    orders_count = int(month_mask.sum())
    revenue_m = df.loc[month_mask, "revenue"].sum()

    driver_records.append({
        "month": m,
        "revenue": revenue_m,
        "orders_count": orders_count,
        "avg_order_value": revenue_m / orders_count if orders_count else 0,
        "unique_customers": len(month_customers),
        "repeat_customers": len(repeat),
        "new_customers": len(new),
    })
    seen_customers |= month_customers

driver_df = pd.DataFrame(driver_records)
for col in ["revenue", "orders_count", "avg_order_value", "unique_customers", "repeat_customers", "new_customers"]:
    driver_df[f"{col}_pct_change"] = driver_df[col].pct_change() * 100
driver_df["flagged"] = driver_df["revenue_pct_change"] < -10

root_cause = None
prev_row = None
valid_drivers = driver_df.dropna(subset=["revenue_pct_change"])
if not valid_drivers.empty:
    worst_idx = valid_drivers["revenue_pct_change"].idxmin()
    worst_row = driver_df.loc[worst_idx]
    if worst_idx > 0:
        prev_row = driver_df.loc[worst_idx - 1]

    candidates = {
        "order volume": worst_row["orders_count_pct_change"],
        "average order value": worst_row["avg_order_value_pct_change"],
        "repeat customers": worst_row["repeat_customers_pct_change"],
        "new customers": worst_row["new_customers_pct_change"],
    }
    valid_candidates = {k: v for k, v in candidates.items() if pd.notna(v)}
    primary_driver = min(valid_candidates, key=valid_candidates.get) if valid_candidates else None

    root_cause = {
        "worst_month": worst_row["month"],
        "revenue_change_pct": worst_row["revenue_pct_change"],
        "orders_change_pct": worst_row["orders_count_pct_change"],
        "aov_change_pct": worst_row["avg_order_value_pct_change"],
        "customers_change_pct": worst_row["unique_customers_pct_change"],
        "repeat_customers_change_pct": worst_row["repeat_customers_pct_change"],
        "primary_driver": primary_driver,
        "primary_driver_change_pct": valid_candidates.get(primary_driver),
    }

# ============================================================
# 5. Tabs
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📊 Overview", "🌍 Regions", "📈 Trend", "🔍 Root Cause", "🔁 Churn", "🤖 AI Report"]
)

# ---- Overview ----
with tab1:
    total_revenue = df["revenue"].sum()
    total_orders = len(df)
    unique_customers = df[customer_col].nunique()
    date_min, date_max = df[date_col].min(), df[date_col].max()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"₹{total_revenue:,.0f}")
    k2.metric("Total Orders", f"{total_orders:,}")
    k3.metric("Unique Customers", f"{unique_customers:,}")
    k4.metric("Date Range", f"{date_min.date()} → {date_max.date()}")

    if has_product:
        st.subheader("Top Products / Categories")
        top_products = df.groupby(product_col)["revenue"].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(top_products, x=product_col, y="revenue", text_auto=".2s")
        fig.update_traces(marker_color=PALETTE[0], hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
        fig.update_layout(plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG, showlegend=False)
        st.plotly_chart(fig, width='stretch')

# ---- Regions ----
with tab2:
    if has_region:
        region_df = df.groupby(region_col)["revenue"].sum().sort_values(ascending=False).reset_index()
        region_colors = {r: c for r, c in zip(region_df[region_col], cycle(PALETTE))}

        st.subheader(f"Revenue by {region_col}")
        fig = px.bar(region_df, x=region_col, y="revenue", color=region_col,
                     color_discrete_map=region_colors, text_auto=".2s")
        fig.update_layout(showlegend=False, plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG)
        fig.update_traces(hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
        st.plotly_chart(fig, width='stretch')

        top_region_row = region_df.iloc[0]
        bottom_region_row = region_df.iloc[-1]
        st.caption(f"Strongest: **{top_region_row[region_col]}** (₹{top_region_row['revenue']:,.0f}) · "
                   f"Weakest: **{bottom_region_row[region_col]}** (₹{bottom_region_row['revenue']:,.0f})")
    else:
        st.info("No region/area column was mapped, so this tab has nothing to show.")

# ---- Trend ----
with tab3:
    st.subheader("Monthly Revenue Trend")
    fig = px.line(driver_df, x="month", y="revenue", markers=True)
    fig.update_traces(line_color=PALETTE[0], hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
    flagged_points = driver_df[driver_df["flagged"]]
    fig.add_scatter(x=flagged_points["month"], y=flagged_points["revenue"], mode="markers",
                     marker=dict(color="#e66767", size=12), name="Flagged drop (>10%)",
                     hovertemplate="%{x}<br>₹%{y:,.0f}<extra>Flagged</extra>")
    fig.update_layout(plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG)
    st.plotly_chart(fig, width='stretch')
    st.caption("🔴 Red markers = months where revenue dropped more than 10% vs. the previous month")

# ---- Root Cause ----
with tab4:
    st.subheader("Root Cause: What drove the worst month?")
    if root_cause is None:
        st.info("Not enough months of data to compute a root cause yet.")
    else:
        st.metric(f"Revenue change in {root_cause['worst_month']}", f"{root_cause['revenue_change_pct']:.1f}%")

        driver_compare = pd.DataFrame({
            "Driver": ["Order Volume", "Avg Order Value", "Repeat Customers", "Total Customers"],
            "% Change": [
                root_cause["orders_change_pct"],
                root_cause["aov_change_pct"],
                root_cause["repeat_customers_change_pct"],
                root_cause["customers_change_pct"],
            ]
        })
        fig = px.bar(driver_compare, x="Driver", y="% Change", text_auto=".1f")
        fig.update_traces(marker_color=["#e66767" if v < 0 else "#199e70" for v in driver_compare["% Change"]])
        fig.update_layout(plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG, showlegend=False)
        st.plotly_chart(fig, width='stretch')

        st.success(
            f"**Primary driver:** {root_cause['primary_driver']} "
            f"({root_cause['primary_driver_change_pct']:.1f}% change) — this metric declined the most "
            f"and is the biggest contributor to the revenue drop. Calculated directly from your data, not AI-guessed."
        )

        if prev_row is not None:
            compare_table = pd.DataFrame({
                "Metric": ["Revenue", "Orders", "Avg Order Value", "Unique Customers", "Repeat Customers", "New Customers"],
                "Previous Month": [
                    f"₹{prev_row['revenue']:,.0f}", f"{int(prev_row['orders_count']):,}",
                    f"₹{prev_row['avg_order_value']:,.0f}", f"{int(prev_row['unique_customers']):,}",
                    f"{int(prev_row['repeat_customers']):,}", f"{int(prev_row['new_customers']):,}"
                ],
                "Worst Month": [
                    f"₹{worst_row['revenue']:,.0f}", f"{int(worst_row['orders_count']):,}",
                    f"₹{worst_row['avg_order_value']:,.0f}", f"{int(worst_row['unique_customers']):,}",
                    f"{int(worst_row['repeat_customers']):,}", f"{int(worst_row['new_customers']):,}"
                ],
            })
            st.table(compare_table)

# ---- Churn ----
with tab5:
    st.subheader("Customer Churn")
    churn_window = st.slider("Churn window (days since last order)", min_value=7, max_value=365, value=90, step=1)

    last_purchase = df.groupby(customer_col)[date_col].max().reset_index()
    last_purchase.columns = [customer_col, "last_order_date"]
    snapshot_date = df[date_col].max()
    last_purchase["days_since_last_order"] = (snapshot_date - last_purchase["last_order_date"]).dt.days
    last_purchase["status"] = last_purchase["days_since_last_order"].apply(
        lambda d: "Churned" if d > churn_window else "Active"
    )

    churned_count = int((last_purchase["status"] == "Churned").sum())
    active_count = int((last_purchase["status"] == "Active").sum())
    churn_rate = churned_count / len(last_purchase) * 100 if len(last_purchase) else 0

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Active Customers", active_count)
    cc2.metric("Churned Customers", churned_count)
    cc3.metric("Churn Rate", f"{churn_rate:.1f}%")

    status_counts = last_purchase["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig = px.bar(status_counts, x="status", y="count",
                 color="status", color_discrete_map={"Active": "#199e70", "Churned": "#e66767"},
                 text_auto=True)
    fig.update_layout(showlegend=False, plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG)
    st.plotly_chart(fig, width='stretch')

    if has_region:
        st.subheader(f"Churn Rate by {region_col}")
        region_lookup = df[[customer_col, region_col]].drop_duplicates(subset=[customer_col])
        merged = last_purchase.merge(region_lookup, on=customer_col, how="left")
        churn_by_region = merged.groupby(region_col)["status"].apply(
            lambda s: (s == "Churned").mean() * 100
        ).reset_index(name="churn_rate")
        fig2 = px.bar(churn_by_region, x=region_col, y="churn_rate", text_auto=".1f")
        fig2.update_traces(marker_color="#e66767", hovertemplate="%{x}<br>%{y:.1f}% churned<extra></extra>")
        fig2.update_layout(plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG, showlegend=False)
        st.plotly_chart(fig2, width='stretch')

    st.caption(f"A customer is marked **Churned** if their last order was more than **{churn_window} days** before "
               f"the most recent date in the dataset ({snapshot_date.date()}).")

# ---- AI Report ----
with tab6:
    st.subheader("🤖 AI-Generated Report")

    def build_facts():
        facts = {
            "total_revenue": f"₹{total_revenue:,.0f}",
            "total_orders": f"{total_orders:,}",
            "unique_customers": f"{unique_customers:,}",
            "churn_rate": f"{churn_rate:.1f}%",
            "churned_count": f"{churned_count:,}",
            "active_count": f"{active_count:,}",
        }
        if root_cause is not None:
            facts["worst_month"] = root_cause["worst_month"]
            facts["worst_month_revenue_change"] = f"{root_cause['revenue_change_pct']:.1f}%"
            facts["primary_driver_of_decline"] = root_cause["primary_driver"]
            facts["primary_driver_change"] = f"{root_cause['primary_driver_change_pct']:.1f}%"
        if has_region:
            facts["top_region"] = f"{top_region_row[region_col]} (₹{top_region_row['revenue']:,.0f})"
            facts["bottom_region"] = f"{bottom_region_row[region_col]} (₹{bottom_region_row['revenue']:,.0f})"
        return facts

    def generate_report(facts):
        summary = (
            f"Total revenue was {facts['total_revenue']} across {facts['total_orders']} orders "
            f"from {facts['unique_customers']} unique customers."
        )

        revenue_finding = "No significant monthly decline was detected."
        if "worst_month" in facts:
            revenue_finding = (
                f"The worst month was {facts['worst_month']}, with revenue down "
                f"{facts['worst_month_revenue_change']} versus the prior month. "
                f"The primary driver was {facts['primary_driver_of_decline']} "
                f"(changed {facts['primary_driver_change']})."
            )

        churn_finding = (
            f"Churn rate is {facts['churn_rate']}, with {facts['churned_count']} churned customers "
            f"out of {int(facts['churned_count'].replace(',', '')) + int(facts['active_count'].replace(',', ''))} total."
        )

        driver = facts.get("primary_driver_of_decline", "overall demand")
        prompt = f"""You are a senior business analyst. In exactly 1-2 sentences, write ONE concrete, specific recommendation for leadership, given that the primary driver of a recent revenue decline was: {driver}. Do not include any numbers or statistics. Just the recommended action and brief reasoning."""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:1b", "prompt": prompt, "stream": False},
            timeout=60
        )
        response.raise_for_status()
        recommendation = response.json()["response"].strip()

        return (
            f"**Executive Summary**\n\n{summary}\n\n"
            f"**Key Finding: Revenue Trend**\n\n{revenue_finding}\n\n"
            f"**Key Finding: Customer Churn**\n\n{churn_finding}\n\n"
            f"**Recommendation**\n\n{recommendation}"
        )

    if st.button("Generate Report"):
        with st.spinner("Analyzing..."):
            try:
                facts = build_facts()
                report_text = generate_report(facts)
                st.session_state["report_text"] = report_text
            except requests.exceptions.ConnectionError:
                st.error("Couldn't reach Ollama. Run `ollama run llama3.2:1b` once to wake it up, then try again.")

    if "report_text" in st.session_state:
        st.markdown(st.session_state["report_text"])
        st.download_button("Download Report", st.session_state["report_text"], file_name="insight_report.txt")