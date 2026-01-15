import anvil.server
import anvil.media
import pandas as pd
import numpy as np
import io
from datetime import datetime
from anvil.tables import app_tables

def clean_val(val, target_type):
  """
    The ultimate cleaner. 
    Handles the 'float NaN to integer' error by catching all null types first.
    """
  # 1. Use pandas' isna to catch None, NaN, and NaT (Not a Time)
  if pd.isna(val):
    return None

  val_str = str(val).strip()
  # 2. Catch strings that represent nulls
  if val_str.lower() in ["nan", "none", "", "nat"]:
    return None

  try:
    if target_type == 'number':
      # Remove currency symbols, commas, and spaces
      clean_num = val_str.replace('$', '').replace(',', '').replace(' ', '')
      # Handle accounting 'dash' for zero
      if clean_num == "-" or not clean_num:
        return None
      return float(clean_num)

    elif target_type == 'date':
      # If it's already a datetime object (common in Excel)
      if isinstance(val, datetime):
        return val.date()
        # Otherwise, try to parse it
      parsed_date = pd.to_datetime(val_str, errors='coerce')
      return parsed_date.date() if not pd.isna(parsed_date) else None

    return val_str # Default to string
  except:
    return None

@anvil.server.callable
def import_master_inventory(file):
  content = file.get_bytes()
  all_sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)

  SHEET_CONFIG = {
    "2025-Summary-Internal": {
      "table": app_tables.inventory_summary_internal,
      "header_row": 0,
      "columns": {
        "Date Requested": ("date_requested", "date"),
        "Location Name": ("location_name", "string"),
        "Employee": ("employee", "string"),
        "Total Amt": ("total_amt", "number"),
        "Date Filled": ("date_filled", "date")
      }
    },
    "2025-Summary-Office": {
      "table": app_tables.inventory_summary_office,
      "header_row": 0,
      "columns": {
        "Date Requested": ("date_requested", "date"),
        "Location Name": ("location_name", "string"),
        "Employee": ("employee", "string"),
        "Total Amt": ("total_amt", "number"),
        "Date Filled": ("date_filled", "date")
      }
    },
    "OfficeSuppliesInventory": {
      "table": app_tables.office_supplies,
      "header_row": 0,
      "columns": {
        "Item": ("item", "string"),
        "On Hand": ("on_hand", "number"),
        "Minimum Amt": ("minimum_amt", "number"),
        "To Order": ("to_order", "number"),
        "Notes": ("notes", "string")
      }
    },
    "OfficeSuppliesCalcs": {
      "table": app_tables.office_calcs,
      "header_row": 7, 
      "columns": {
        "Item": ("item", "string"),
        "$ Amount/each": ("amount_each", "number"),
        "Qty": ("qty", "number"),
        "Total": ("total", "number"),
        "Notes": ("notes", "string")
      }
    }
  }

  messages = []
  for sheet_name, config in SHEET_CONFIG.items():
    if sheet_name in all_sheets:
      try:
        # Load the sheet
        df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, header=config['header_row'])

        # PRE-CLEAN: Strip header spaces and replace ALL NaNs with None immediately
        df.columns = [str(c).strip() for c in df.columns]
        df = df.replace({np.nan: None})

        table = config['table']
        col_map = config['columns']
        rows_added = 0

        for _, row in df.iterrows():
          new_db_row = {}
          has_real_data = False

          for excel_col, (anvil_col, dtype) in col_map.items():
            if excel_col in row:
              cleaned = clean_val(row[excel_col], dtype)
              new_db_row[anvil_col] = cleaned
              # Mark that this row actually has content
              if cleaned is not None:
                has_real_data = True

                # Only add if the row isn't just empty Excel padding
          if has_real_data:
            table.add_row(**new_db_row)
            rows_added += 1

        messages.append(f"✓ {sheet_name}: Imported {rows_added} rows")
      except Exception as e:
        messages.append(f"⚠ Error in {sheet_name}: {str(e)}")
    else:
      messages.append(f"× Sheet '{sheet_name}' not found.")

  return "\n".join(messages)