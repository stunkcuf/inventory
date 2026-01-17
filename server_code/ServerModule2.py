import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import anvil.tables.query as q
import pandas as pd
import io
import numpy as np
import re
from datetime import datetime

# --- 1. HELPERS ---
def clean_num(val):
  if val is None or val == "" or str(val).strip() == "0": return 0
  if isinstance(val, (int, float)): return val
  clean_val = str(val).replace('$', '').replace(',', '').strip()
  match = re.search(r'(\d+(\.\d+)?)', clean_val)
  if match:
    try: return float(match.group(1))
    except: return 0
  return 0

def get_latest_sheet(sheet_list, keyword):
  pattern = re.compile(r'(\d{2})\.(\d{2})\.(\d{2})')
  dated_sheets = []
  for s in sheet_list:
    if keyword.lower() in s.lower() and "master" not in s.lower() and "order" not in s.lower():
      match = pattern.search(s)
      if match:
        m, d, y = match.groups()
        dt = datetime(2000 + int(y), int(m), int(d))
        dated_sheets.append((dt, s))
  if dated_sheets:
    dated_sheets.sort(key=lambda x: x[0], reverse=True)
    return dated_sheets[0][1]
  return None

# --- 2. SEARCH LOGIC ---
@anvil.server.callable
def get_inventory_fast(category="All", search_query=None):
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")
  return app_tables.inventory.search(tables.order_by("Item", ascending=True), **search_args)

# --- 3. EXCEL IMPORT (De-duplication + Header Hunt) ---
@anvil.server.callable
def process_excel_import(file):
  xl = pd.ExcelFile(io.BytesIO(file.get_bytes()))
  all_sheets = xl.sheet_names
  target_assignments = []

  latest_off = get_latest_sheet(all_sheets, "Office")
  latest_cen = get_latest_sheet(all_sheets, "Center")
  if latest_off: target_assignments.append((latest_off, "inventory"))
  if latest_cen: target_assignments.append((latest_cen, "inventory"))

  for s in all_sheets:
    ls = s.lower()
    if "summary" in ls: target_assignments.append((s, "summary_2025"))
    if "master" in ls or "orderform" in ls:
      table = "office_calcs" if "office" in ls else "center_calcs"
      target_assignments.append((s, table))

  for tbl in ["inventory", "summary_2025", "office_calcs", "center_calcs"]:
    if any(t == tbl for s, t in target_assignments):
      getattr(app_tables, tbl).delete_all_rows()

  for excel_sheet, table_name in target_assignments:
    raw_df = xl.parse(excel_sheet, header=None)
    header_row_index = 0
    for i, row in raw_df.iterrows():
      if "Item" in row.values:
        header_row_index = i
        break

    df = xl.parse(excel_sheet, skiprows=header_row_index).replace({np.nan: None})
    for _, row in df.iterrows():
      raw = dict(row)
      item_name = str(raw.get('Item', '')).strip()
      if not item_name or item_name in ["None", "Item"] or item_name.endswith(':'): continue

      if table_name == "inventory":
        cat = "Office" if "office" in excel_sheet.lower() else "Center"
        existing = app_tables.inventory.get(Item=item_name, Category=cat)
        on_hand = int(clean_num(raw.get('On Hand', 0)))
        min_amt = int(clean_num(raw.get('Minimum Amt', 0)))
        if existing: existing.update(On_Hand=on_hand, Minimum_Amt=min_amt)
        else: app_tables.inventory.add_row(Item=item_name, Category=cat, On_Hand=on_hand, Minimum_Amt=min_amt)

      elif "calcs" in table_name:
        url = next((str(v) for v in raw.values() if v and "http" in str(v)), None)
        price = clean_num(raw.get('$ Amount/each') or raw.get('Amount') or 0)
        table = getattr(app_tables, table_name)
        existing = table.get(Item=item_name)
        if existing: existing.update(Item_Link=url, Price=price)
        else: table.add_row(Item=item_name, Item_Link=url, Price=price, Ordered=False)
  return [s for s, t in target_assignments]

# --- 4. SHOPPING LIST (The Final Join) ---
@anvil.server.callable
def get_shopping_list():
  off_master = {r['Item']: dict(r) for r in app_tables.office_calcs.search() if r['Item']}
  cen_master = {r['Item']: dict(r) for r in app_tables.center_calcs.search() if r['Item']}

  items = []
  for inv_row in app_tables.inventory.search():
    item_name = inv_row['Item']
    cat = inv_row.get('Category', 'Office')
    master_dict = off_master if cat == "Office" else cen_master
    master_info = master_dict.get(item_name, {})

    oh, ma = inv_row.get('On_Hand', 0) or 0, inv_row.get('Minimum_Amt', 0) or 0
    is_ordered = master_info.get('Ordered', False)

    if oh < ma and not is_ordered:
      items.append({
        'Item': item_name, 'On_Hand': oh, 'Minimum_Amt': ma,
        'Category': cat, 'Source': cat,
        'Price': master_info.get('Price', 0),
        'Item_Link': master_info.get('Item_Link'),
        'Ordered': is_ordered
      })
  return sorted(items, key=lambda x: (x['Category'], x['Item']))

@anvil.server.callable
def mark_as_ordered(item_name, category, status):
  table = app_tables.office_calcs if category == "Office" else app_tables.center_calcs
  row = table.get(Item=item_name)
  if row: row['Ordered'] = status