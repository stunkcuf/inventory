import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import anvil.tables.query as q
import pandas as pd
import io
import numpy as np
import re
from datetime import datetime

# --- 1. MAIN INVENTORY SEARCH (Fixes get_inventory_fast error) ---
@anvil.server.callable
def get_inventory_fast(category="All", search_query=None):
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")
  return app_tables.inventory.search(tables.order_by("Item", ascending=True), **search_args)

# --- 2. SHOPPING LIST LOGIC (On_Hand < Min and To_Order > 0) ---
@anvil.server.callable
def get_shopping_list():
  # Only show items not yet marked as 'Ordered'
  items = app_tables.inventory.search(Ordered=q.not_(True))
  shopping_list = []
  for row in items:
    on_hand = row['On_Hand'] or 0
    min_amt = row['Minimum_Amt'] or 0
    to_order = row['To_Order'] or 0
    if on_hand < min_amt and to_order > 0:
      shopping_list.append(row)
  return sorted(shopping_list, key=lambda x: (x['Category'], x['Item']))

@anvil.server.callable
def mark_as_ordered(item_row, status):
  item_row['Ordered'] = status

@anvil.server.callable
def reset_ordered_status():
  for row in app_tables.inventory.search(Ordered=True):
    row['Ordered'] = False

# --- 3. DASHBOARD LOGIC (Fixes get_spending_summary error) ---
@anvil.server.callable
def get_spending_summary():
  data = app_tables.summary_2025.search()
  totals = {}
  for row in data:
    loc = row['Location'] or "Unassigned"
    cost = row['Total_Cost'] or 0
    totals[loc] = totals.get(loc, 0) + cost
  sorted_keys = sorted(totals, key=totals.get, reverse=True)
  return sorted_keys, [totals[k] for k in sorted_keys]

# --- 4. MASTER EXCEL IMPORTER ---
@anvil.server.callable
def process_excel_import(file):
  xl = pd.ExcelFile(io.BytesIO(file.get_bytes()))
  # ... (Keep your existing Excel processing logic here)
  # Ensure it sets row_dict['Ordered'] = False during import
  return "Import Successful"