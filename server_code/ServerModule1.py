import anvil.server
import anvil.media
import pandas as pd
import numpy as np
import io
from datetime import datetime
from anvil.tables import app_tables
import anvil.tables.query as q

def clean_val(val, target_type):
  if pd.isna(val): return None
  val_str = str(val).strip()
  if val_str.lower() in ["nan", "none", "", "nat", "$-"]: return None

  try:
    if target_type == 'number':
      clean_num = val_str.replace('$', '').replace(',', '').replace(' ', '')
      return float(clean_num) if clean_num not in ["-", ""] else None
    elif target_type == 'date':
      if isinstance(val, datetime): return val.date()
      parsed = pd.to_datetime(val_str, errors='coerce')
      return parsed.date() if not pd.isna(parsed) else None
    return val_str
  except:
    return None

@anvil.server.callable
def import_master_inventory(file):
  content = file.get_bytes()
  all_sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)

  SHEET_CONFIG = {
    "2025-Summary-Internal": {"table": app_tables.inventory_summary_internal, "header": 0, "cols": {"Date Requested":("date_requested","date"), "Location Name":("location_name","string"), "Employee":("employee","string"), "Total Amt":("total_amt","number"), "Date Filled":("date_filled","date")}},
    "2025-Summary-Office": {"table": app_tables.inventory_summary_office, "header": 0, "cols": {"Date Requested":("date_requested","date"), "Location Name":("location_name","string"), "Employee":("employee","string"), "Total Amt":("total_amt","number"), "Date Filled":("date_filled","date")}},
    "2025-Summary-Center": {"table": app_tables.inventory_summary_center, "header": 0, "cols": {"Date Requested":("date_requested","date"), "Location Name":("location_name","string"), "Employee":("employee","string"), "Total Amt":("total_amt","number"), "Date Filled":("date_filled","date")}},
    "2025-Summary": {"table": app_tables.inventory_summary_total, "header": 0, "cols": {"Date Requested":("date_requested","date"), "Location Name":("location_name","string"), "Employee":("employee","string"), "Total Amt":("total_amt","number"), "Date Filled":("date_filled","date")}},
    "OfficeSuppliesInventory": {"table": app_tables.office_supplies, "header": 0, "cols": {"Item":("item","string"), "On Hand":("on_hand","number"), "Minimum Amt":("minimum_amt","number"), "To Order":("to_order","number")}},
    "CenterSuppliesInventory": {"table": app_tables.center_supplies, "header": 0, "cols": {"Item":("item","string"), "On Hand":("on_hand","number"), "Minimum Amt":("minimum_amt","number"), "To Order":("to_order","number")}},
    "OfficeSuppliesCalcs": {"table": app_tables.office_calcs, "header": 7, "cols": {"Item":("item","string"), "$ Amount/each":("amount_each","number"), "Qty":("qty","number"), "Total":("total","number")}},
    "CenterSuppliesCalcs": {"table": app_tables.center_calcs, "header": 0, "cols": {"Item":("item","string"), "$ Amount/each":("amount_each","number"), "Quantity":("qty","number"), "Total":("total","number")}},
    "Master": {"table": app_tables.master_order_log, "header": 2, "cols": {"Item":("item","string"), "$ Amount/each":("amount_each","number"), "Total":("total","number"), "Employee requesting":("employee","string"), "Center":("location","string")}}
  }

  results = []

  # Fast Transaction Wrapper
  @anvil.tables.in_transaction
  def batch_insert(table, data):
    for r in data: table.add_row(**r)

  for sheet_name, cfg in SHEET_CONFIG.items():
    if sheet_name in all_sheets:
      try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, header=cfg['header'])
        df.columns = [str(c).strip() for c in df.columns]

        rows_to_add = []
        for _, row in df.iterrows():
          entry = {}
          val_found = False
          for ex_col, (db_col, dtype) in cfg['cols'].items():
            if ex_col in row:
              cleaned = clean_val(row[ex_col], dtype)
              entry[db_col] = cleaned
              if cleaned is not None: val_found = True
          if val_found: rows_to_add.append(entry)

        if rows_to_add:
          batch_insert(cfg['table'], rows_to_add)
        results.append(f"✓ {sheet_name}: {len(rows_to_add)} rows")
      except Exception as e:
        results.append(f"⚠ {sheet_name} Error: {str(e)}")

    # Special Handling for WM-Stock (Unpivoting)
  if "OfficeSupplies-WM-Stock" in all_sheets:
    try:
      df_wm = pd.read_excel(io.BytesIO(content), sheet_name="OfficeSupplies-WM-Stock", header=0)
      wm_count = 0
      for _, row in df_wm.iterrows():
        item_name = clean_val(row.iloc[0], 'string')
        if not item_name: continue
          # Loop through date columns (Column B, E, H, etc.)
        for i in range(1, len(df_wm.columns) - 1, 3): 
          date_val = clean_val(row.iloc[i], 'date')
          amt_val = clean_val(row.iloc[i+1], 'number')
          if date_val and amt_val is not None:
            app_tables.wm_stock_history.add_row(item=item_name, check_date=date_val, amount=amt_val)
            wm_count += 1
      results.append(f"✓ WM-Stock: {wm_count} data points")
    except Exception as e:
      results.append(f"⚠ WM-Stock Error: {str(e)}")

  return "\n".join(results)