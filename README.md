# InsightIQ - AI Decision Analytics Dashboard

Upload any company's transaction CSV, map your columns, and InsightIQ explains what happened to the business: why revenue dropped, which customers stopped buying, and what to do about it.

## What it does

- **Works on any transaction CSV.** You map your own columns (date, customer, region, product, revenue or quantity x price).
- **Cleans real-world data.** Handles non-UTF-8 encodings, day-first dates and invalid rows.
- **Overview, Regions and Trend tabs.** Revenue, orders and customers over time and by region.
- **Root-cause analysis.** Flags months where revenue fell more than 10% and breaks the drop into orders, average order value, and new vs. repeat customers.
- **Churn analysis.** Customers who have not ordered within an adjustable window (7-365 days), with region-wise churn rates.
- **AI report.** A written summary and recommendation, downloadable as text.

## How the AI report works

Early versions let the LLM write the whole report, and it mixed up months and numbers. So the design was changed:

- Python computes every figure and writes every sentence that contains a number.
- A local LLM (Llama 3.2 via Ollama) writes only a short recommendation, with no numbers.
- Everything runs locally, so business data never leaves the machine.

## Tech stack

Python, Pandas, Streamlit, Plotly, Ollama (Llama 3.2 1B). An early version used SQL with SQLite (see `queries.py`, `load_db.py`).

## Run it

1. Install the requirements:
   `pip install -r requirements.txt`
2. Install Ollama from https://ollama.com and pull the model:
   `ollama pull llama3.2:1b`
3. Download the sample dataset (UCI Online Retail) from
   https://archive.ics.uci.edu/dataset/352/online+retail
   and save it as a CSV.
4. Start the app:
   `python -m streamlit run app.py`
5. Upload the CSV, map the columns (for the sample: Date = InvoiceDate, Customer = CustomerID, Region = Country, Product = Description, Revenue = Quantity x UnitPrice), and click Run Analysis.

## Tested on

The UCI Online Retail dataset (about 540,000 rows).

## Limitations

- A student project, tested on one public dataset and not deployed with a real business.
- Uses a small local model, so the written recommendation is general.
- Churn is defined by inactivity days and is not a predictive model.

## Files

- `app.py` - the Streamlit dashboard
- `analysis.py`, `queries.py`, `load_db.py`, `generate_data.py` - the earlier SQL/SQLite version and its sample data
