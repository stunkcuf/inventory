import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import anvil.tables.query as q
import io
import json
from hmac import compare_digest
from urllib.parse import parse_qs, urlsplit
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from itertools import islice


# --- LOCATION MAPPING SYSTEM ---
# Master lookup table for location codes and names
LOCATION_MAP = {
  10: "Main Office",
  11: "CCR&R",  # CCR&R/DECL/DELC
  12: "PEHS",   # Pendleton EHS 
  14: "PELC",
  15: "Annex",
  16: "LaGrande",
  21: "NELC",  # NELC only
  22: "Umatilla",
  24: "Pine Tree",
  25: "CWELC",  # CWELC/CW
  26: "PEHS",
  31: "Victory Square",
  32: "HCDC",  # Hermiston CDC
  33: "HCSR Lil Pups",
  34: "FACE",
  41: "Milton-Freewater",
  51: "Irrigon",
  60: "Airport Way",
  62: "PELC",
  63: "Enterprise",
  64: "CCR&R",
  68: "Bus Barn",
  69: "Patriot Heights",
  441: "MO"
}

def normalize_location_name(name):
  """Clean up location name variations"""
  if not name:
    return name

  name = str(name).strip()

  # Handle common variations
  variations = {
    # Name variations
    'Milton Freewater': 'Milton-Freewater',
    'Milton-Freewate': 'Milton-Freewater',
    'MiltonFreewater': 'Milton-Freewater',
    'Pinetree': 'Pine Tree',
    'LaG': 'LaGrande',
    'La Grande': 'LaGrande',
    'Stanfield/PH': 'Patriot Heights',
    'PH/Stanfield': 'Patriot Heights',
    'Stanfield / PH': 'Patriot Heights',
    'Lil Pups 3': 'HCSR Lil Pups',
    'Lil Pups 1': 'HCSR Lil Pups',
    'HCSR Lil Pups 1': 'HCSR Lil Pups',
    'HCSR Lil Pups 3': 'HCSR Lil Pups',
    'Main Office WIC': 'Main Office',
    'MO WIC': 'Main Office',
    'MO HR': 'Main Office',
    'MO': 'Main Office',
    'MAIN': 'Main Office',
    'WIC': 'Main Office',
    'VS': 'Victory Square',
    'CW': 'CWELC',
    'HCDC': 'HCDC',
    'Hermiston CDC': 'HCDC',
    'HCSR': 'HCDC',  # Based on code 32 correction
    'HCSR1': 'HCDC',
    'Pendleton EHS': 'PEHS',
    'DECL': 'CCR&R',
    'DELC': 'CCR&R',
    'NE$LC': 'NELC',  # Typo variation
    'PEHS / PELC': 'PEHS',  # Combined entry
    '12 & 14': 'PEHS',  # Combined location codes
  }
  
  return variations.get(name, name)

def get_complete_location_display(location_code, location_name):
  """
  Build complete location display: [code] name
  Uses master mapping to fill in missing parts
  """
  # Normalize the name if provided
  if location_name:
    location_name = normalize_location_name(location_name)
  
  # Try to get complete info from mapping
  if location_code and location_code in LOCATION_MAP:
    canonical_name = LOCATION_MAP[location_code]
    return f"[{location_code}] {canonical_name}"
  
  # If we have both, use them
  if location_code and location_name:
    return f"[{location_code}] {location_name}"
  
  # If only code, use it
  if location_code:
    return f"[{location_code}] Location {location_code}"
  
  # If only name, return as-is (no code available)
  if location_name:
    return location_name
  
  return "Unknown"


# --- 1. HELPERS ---
def clean_num(val):
  """UNCHANGED - Your original code works perfectly"""
  if val is None or val == "" or str(val).strip() == "0": return 0
  if isinstance(val, (int, float)): return val
  clean_val = str(val).replace('$', '').replace(',', '').strip()
  match = re.search(r'(\d+(\.\d+)?)', clean_val)
  return float(match.group(1)) if match else 0

def get_latest_sheet(sheet_list, keyword):
  """UNCHANGED - Your original code works perfectly"""
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

def extract_url_from_text(text):
  """
  IMPROVED: Added validation to prevent malformed URLs
  WHY: Prevents saving incomplete or invalid URLs like "http://" or "http://example.com."
  """
  if not text or not isinstance(text, str):
    return None

  text = str(text).strip()

  # Direct URL check
  if text.startswith('http://') or text.startswith('https://'):
    url = text
  # Look for -> URL pattern
  elif ' -> ' in text:
    parts = text.split(' -> ')
    if len(parts) >= 2:
      url = parts[-1].strip()
      if not (url and url.lower() != 'none' and url.startswith('http')):
        return None
    else:
      return None
  # Look for any http URL in the text
  else:
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
      url = url_match.group(1)
    else:
      return None

  # ADDED: Validate and clean the URL
  if url:
    # Remove trailing punctuation that's not part of URL
    url = url.rstrip('.,;)\'"')

    # Must have at least one dot (domain.com)
    if '.' not in url.replace('http://', '').replace('https://', ''):
      return None

    # Must be longer than just "http://" or "https://"
    if len(url) <= 8:
      return None

    return url

  return None

def find_header_row(df):
  """UNCHANGED - Your original code works perfectly"""
  for i, row in df.iterrows():
    row_str = ' '.join([str(v).lower() for v in row.values if v is not None])
    if 'item' in row_str and ('amount' in row_str or 'qty' in row_str or 'url' in row_str or 'price' in row_str):
      return i
  return 0

def find_column_by_keywords(columns, *keywords):
  """UNCHANGED - Your original code works perfectly"""
  for col in columns:
    col_lower = str(col).lower().strip()
    for keyword in keywords:
      if keyword.lower() in col_lower:
        return col
  return None

def get_excel_column_index(df, column_name):
  """UNCHANGED - Your original code works perfectly"""
  try:
    return list(df.columns).index(column_name) + 1
  except:
    return None

# --- 2. DATA LOADERS ---
@anvil.server.callable
def get_inventory_fast(category="All", search_query=None, subcategory=None, limit=100):
  """
  Load inventory with optional limit to prevent crashes on large datasets
  Default limit: 100 items (prevents memory issues with 1000+ item inventory)
  """
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  if subcategory and subcategory != "All":
    search_args['Subcategory'] = subcategory
  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")

  # Get results
  results = app_tables.inventory.search(tables.order_by("Item", ascending=True), **search_args)

  return list(islice(results, limit)) if limit else list(results)

@anvil.server.callable
def get_inventory_view(category="All", search_query=None):
  return {
    'items': get_inventory_fast(category, search_query),
    'subcategories': get_subcategories(category),
  }

@anvil.server.callable
def get_subcategories(category="All"):
  """
  Get unique subcategories - optimized for large datasets
  """
  try:
    search_args = {}
    if category and category != "All":
      search_args['Category'] = category

    items = app_tables.inventory.search(**search_args)
    subcategories = set()

    # Limit processing to prevent crashes with huge datasets
    count = 0
    max_items = 1000  # Safety limit

    for item in items:
      if count >= max_items:
        print(f"⚠️ Subcategory scan limited to {max_items} items")
        break

      subcat = item.get('Subcategory')
      if subcat:
        subcategories.add(subcat)
      count += 1

    result = sorted(list(subcategories))
    print(f"Found {len(result)} subcategories from {count} items")
    return result

  except Exception as e:
    print(f"Error in get_subcategories: {e}")
    return []

@anvil.server.callable
def get_spending_summary():
  """
  IMPROVED: Fixed iterator consumption issue
  WHY: Was calling search() 4 times unnecessarily - now only calls once
  PERFORMANCE: 4x faster database access
  NOTE: This is the legacy function - use get_spending_summary_by_table for new code
  """
  print("=== get_spending_summary called ===")

  # Convert to list once
  data = list(app_tables.summary_2025.search())
  print(f"Found {len(data)} rows in summary_2025")

  if not data:
    return [("No Data", 0)]

  # Check what columns exist (first row only)
  first_row = data[0]
  print(f"Available columns: {list(first_row.keys())}")
  print(f"First row data: {dict(first_row)}")

  # Build results from the already-loaded list
  results = []
  for r in data:
    location = r.get('Location') or r.get('Location Name') or r.get('Location #') or "Unknown"
    total_cost = r.get('Total_Cost') or r.get('Total Amt') or r.get('Total_Amt') or 0
    results.append((location, total_cost))
    print(f"  {location}: ${total_cost}")

  print(f"Returning {len(results)} results")
  return results

def reconcile_2025_spending():
  """Compare the 2025 summary with the legacy total export at currency precision."""
  annual_rows = list(app_tables.summary_2025.search())
  total_rows = list(app_tables.inventory_summary_total.search())
  if not annual_rows or not total_rows:
    return [], "Both 2025 sources are needed to verify spending."

  def cents(value):
    return int(round(Decimal(str(value or 0)) * 100))

  def location(name):
    return normalize_location_name(re.sub(r'^\[\d+\]\s*', '', name or '').strip())

  primary = Counter()
  primary_amounts = Counter()
  breakdown = []
  for row in annual_rows:
    name = location(row['Location'])
    amount = cents(row['Total_Cost'])
    amounts = [cents(row[field]) for field in ('GL_Amt', 'PO_Amt', 'Other_Amt')]
    if sum(amounts) != amount or (amount and not name):
      return [], "2025 Summary contains an incomplete or inconsistent spending row."
    if amount:
      primary[name] += amount
      primary_amounts[amount] += 1
    breakdown.append((name, *(value / 100 for value in amounts)))

  compared = Counter()
  compared_amounts = Counter()
  seen = set()
  fields = ('location_name', 'date_requested', 'date_filled', 'employee',
            'Location_Code', 'GL_Amt', 'PO_Amt', 'Other_Amt')
  for row in total_rows:
    amount = cents(row['total_amt'])
    if not amount:
      continue
    key = (amount, *(row[field] for field in fields))
    if key in seen:
      continue
    seen.add(key)
    # These spellings are reconciled against the 2025 export only.
    name = row['location_name']
    code = row['Location_Code']
    if code is not None:
      name = LOCATION_MAP.get(code)
      if name is None:
        return [], "Total Inventory Summary contains an unknown location code."
    elif name in ('HCSR', 'HCSR1'):
      name = 'HCSR Lil Pups'
    compared[location(name)] += amount
    compared_amounts[amount] += 1

  annual_total = sum(primary.values())
  compared_total = sum(compared.values())
  different_locations = sum(primary[name] != compared[name] for name in primary.keys() | compared.keys())
  if primary_amounts != compared_amounts or different_locations:
    return [], (
      f"Sources disagree. 2025 Summary: ${annual_total / 100:,.2f}<br>"
      f"Total Inventory Summary after removing repeated rows: ${compared_total / 100:,.2f}<br>"
      f"Difference: ${abs(annual_total - compared_total) / 100:,.2f}. "
      f"Locations with different totals: {different_locations}."
    )
  if not primary_amounts:
    return [], "No spending data loaded for 2025."
  return breakdown, f"2025 spending verified across both summaries: ${annual_total / 100:,.2f}"


@anvil.server.callable
def get_spending_summary_by_table(table_name='summary_2025'):
  """
  Get spending summary with GL, PO, Other breakdown
  Returns: list of tuples (location, gl_amt, po_amt, other_amt)
  
  """
  print(f"=== get_spending_summary_by_table called for {table_name} ===")

  if table_name == 'inventory_summary_total':
    rows, _ = reconcile_2025_spending()
    return rows

  valid_tables = [
    'summary_2025',
    'inventory_summary_total',
    'inventory_summary_office',
    'inventory_summary_internal',
    'inventory_summary_center'
  ]

  if table_name not in valid_tables:
    print(f"Invalid table name: {table_name}")
    return [("No Data", 0, 0, 0)]

  try:
    table = getattr(app_tables, table_name)
    data = list(table.search())

    print(f"Found {len(data)} rows in {table_name}")

    if not data:
      return [("No Data", 0, 0, 0)]

    results = []

    # Return full breakdown for all summary tables
    for r in data:
      # Try both column name formats
      location = r.get('Location') or r.get('location_name') or "Unknown"
      location_code = r.get('Location_Code')  # This is a number
      gl_amt = r.get('GL_Amt') or 0
      po_amt = r.get('PO_Amt') or 0
      other_amt = r.get('Other_Amt') or 0

      # Location name already has formatting from import, use as-is
      display_name = location

      results.append((display_name, gl_amt, po_amt, other_amt))

      # Only print first 5 to avoid log spam
      if len(results) <= 5:
        print(f"  {display_name}: GL=${gl_amt}, PO=${po_amt}, Other=${other_amt}")


    print(f"Returning {len(results)} results")
    return results

  except Exception as e:
    print(f"Error loading {table_name}: {e}")
    import traceback
    traceback.print_exc()
    return [("Error", 0, 0, 0)]


@anvil.server.callable
def get_available_summary_tables():
  """
  NEW: Return list of available summary tables
  WHY: Populate dropdown with user-friendly names
  USAGE: Called by SummaryForm to populate dropdown options
  """
  return [
    ('2025 Summary', 'summary_2025'),
    ('2026 Summary', 'summary_2026'),
    ('Total Inventory Summary', 'inventory_summary_total'),
    ('Office Inventory Summary', 'inventory_summary_office'),
    ('Internal Inventory Summary', 'inventory_summary_internal'),
    ('Center Inventory Summary', 'inventory_summary_center'),
  ]

@anvil.server.callable
def get_spending_chart_figure(table_name='summary_2025'):
  """
  Generate a clean Plotly figure for spending breakdown
  Only shows bars for categories with non-zero values
  Returns a Plotly figure dict ready for client rendering
  """
  print(f"=== Generating chart for {table_name} ===")
  
  summary_title = None
  if table_name == 'summary_2026':
    data, summary_title = [], "No spending data loaded for 2026."
  elif table_name == 'inventory_summary_total':
    data, summary_title = reconcile_2025_spending()
  else:
    data = get_spending_summary_by_table(table_name)

  if not data and summary_title:
    return {'data': [], 'layout': {
      'annotations': [{'text': summary_title, 'xref': 'paper', 'yref': 'paper',
                       'x': 0.5, 'y': 0.5, 'showarrow': False}],
      'xaxis': {'visible': False}, 'yaxis': {'visible': False},
    }}
  
  if not data or len(data) == 0:
    print("No data found")
    return None
  
  # Aggregate by location and filter out Unknown/$0 entries
  location_totals = {}
  
  for item in data:
    location, gl, po, other = item
    
    # Skip if location is "Unknown" and all amounts are 0
    if location == "Unknown" and gl == 0 and po == 0 and other == 0:
      continue
    
    # Skip if all amounts are 0
    if gl == 0 and po == 0 and other == 0:
      continue
    
    # Aggregate by location
    if location not in location_totals:
      location_totals[location] = {'gl': 0, 'po': 0, 'other': 0}
    
    location_totals[location]['gl'] += gl
    location_totals[location]['po'] += po
    location_totals[location]['other'] += other
  
  if len(location_totals) == 0:
    print("No spending found after filtering")
    return None
  
  # Sort by total spending (descending)
  sorted_locations = sorted(
    location_totals.items(), 
    key=lambda x: x[1]['gl'] + x[1]['po'] + x[1]['other'],
    reverse=True
  )
  
  # Separate into lists
  locations = [loc for loc, _ in sorted_locations]
  gl_amounts = [totals['gl'] for _, totals in sorted_locations]
  po_amounts = [totals['po'] for _, totals in sorted_locations]
  other_amounts = [totals['other'] for _, totals in sorted_locations]
  
  # Build traces - only include if there's ANY spending in that category
  traces = []
  
  # Check if there's any GL spending across all locations
  if any(gl_amounts):
    traces.append({
      'type': 'bar',
      'name': 'GL Spending',
      'x': locations,
      'y': gl_amounts,
      'marker': {'color': '#4A90E2'},  # Blue
      'hovertemplate': '<b>%{x}</b><br>GL: $%{y:,.2f}<extra></extra>'
    })
  
  # Check if there's any PO spending
  if any(po_amounts):
    traces.append({
      'type': 'bar',
      'name': 'PO Orders',
      'x': locations,
      'y': po_amounts,
      'marker': {'color': '#50C878'},  # Green
      'hovertemplate': '<b>%{x}</b><br>PO: $%{y:,.2f}<extra></extra>'
    })
  
  # Check if there's any Other spending
  if any(other_amounts):
    traces.append({
      'type': 'bar',
      'name': 'Other',
      'x': locations,
      'y': other_amounts,
      'marker': {'color': '#FF9500'},  # Orange
      'hovertemplate': '<b>%{x}</b><br>Other: $%{y:,.2f}<extra></extra>'
    })
  
  # If no traces at all, return None
  if len(traces) == 0:
    print("No spending found in any category")
    return None
  
  # Build the figure
  figure = {
    'data': traces,
    'layout': {
      'title': {
        'text': summary_title or f'Spending Breakdown - {table_name.replace("_", " ").title()}',
        'font': {'size': 20}
      },
      'barmode': 'stack',
      'xaxis': {
        'title': 'Location',
        'tickangle': -45,
        'automargin': True
      },
      'yaxis': {
        'title': 'Amount ($)',
        'tickformat': '$,.0f'
      },
      'hovermode': 'closest',
      'showlegend': True,
      'legend': {
        'orientation': 'h',
        'yanchor': 'bottom',
        'y': 1.02,
        'xanchor': 'right',
        'x': 1
      },
      'margin': {'b': 120, 't': 60, 'l': 60, 'r': 20}
    }
  }
  
  print(f"Generated figure with {len(traces)} traces for {len(locations)} locations (filtered from {len(data)} raw entries)")
  return figure

# --- 3. THE "DEEP SCAN" EXCEL IMPORT ---
@anvil.server.callable
def process_excel_import(file, import_mode='full'):
  """
  IMPROVED: Added chunked import support to prevent timeouts
  
  import_mode options:
  - 'full': Import everything (default, may timeout on large files)
  - 'calcs': Import only calcs sheets (URLs)
  - 'summaries': Import only summary sheets
  - 'main_summary': Import only 2025-Summary sheet
  - 'quick': Import calcs + small summaries (skip 2025-Summary)
  
  WHY: Large files timeout - chunking allows completion
  RETURNS: Detailed import summary with what was processed
  """

  require_admin()
  import numpy as np
  import openpyxl
  import pandas as pd

  # Initialize import statistics
  import_stats = {
    'inventory': 0,
    'office_calcs': 0,
    'center_calcs': 0,
    'summary_2025': 0,
    'inventory_summary_total': 0,
    'inventory_summary_office': 0,
    'inventory_summary_internal': 0,
    'inventory_summary_center': 0,
    'errors': [],
    'warnings': []
  }

  try:
    file_bytes = file.get_bytes()
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    all_sheets = xl.sheet_names
    print(f"\nAll sheets in Excel file: {all_sheets}")

    target_assignments = []
    latest_off = get_latest_sheet(all_sheets, "Office")
    latest_cen = get_latest_sheet(all_sheets, "Center")

    print(f"Latest Office inventory sheet: {latest_off}")
    print(f"Latest Center inventory sheet: {latest_cen}")

    if latest_off: target_assignments.append((latest_off, "inventory"))
    if latest_cen: target_assignments.append((latest_cen, "inventory"))

    # IMPROVED: Added support for multiple summary tables
    for s in all_sheets:
      ls = s.lower()

      # Main 2025 Summary
      if s == "2025-Summary":
        target_assignments.append((s, "summary_2025"))
        print(f"Assigning sheet '{s}' to table 'summary_2025'")

      # Inventory Summary Tables (NEW)
      elif "total" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_total"))
        print(f"Assigning sheet '{s}' to table 'inventory_summary_total'")
      elif "office" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_office"))
        print(f"Assigning sheet '{s}' to table 'inventory_summary_office'")
      elif "internal" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_internal"))
        print(f"Assigning sheet '{s}' to table 'inventory_summary_internal'")
      elif ("center" in ls or "centre" in ls) and "summary" in ls:
        target_assignments.append((s, "inventory_summary_center"))
        print(f"Assigning sheet '{s}' to table 'inventory_summary_center'")

      # Calcs sheets
      elif "calcs" in ls:
        table = "office_calcs" if "office" in ls else "center_calcs"
        target_assignments.append((s, table))
        print(f"Assigning sheet '{s}' to table '{table}' (URLS HERE)")

      # Master sheets
      elif "master" in ls:
        table = "center_calcs"
        target_assignments.append((s, table))
        print(f"Assigning sheet '{s}' to table '{table}'")

    # FILTER ASSIGNMENTS BASED ON IMPORT MODE
    if import_mode == 'calcs':
      # Only calcs sheets
      target_assignments = [(s, t) for s, t in target_assignments if 'calcs' in t.lower()]
      print(f"\n🔄 IMPORT MODE: calcs - Processing {len(target_assignments)} calcs sheets only")
      
    elif import_mode == 'summaries':
      # Only summary sheets (not 2025-Summary)
      target_assignments = [(s, t) for s, t in target_assignments 
                           if 'summary' in t.lower() and t != 'summary_2025']
      print(f"\n🔄 IMPORT MODE: summaries - Processing {len(target_assignments)} small summary sheets")
      
    elif import_mode == 'main_summary':
      # Only 2025-Summary sheet
      target_assignments = [(s, t) for s, t in target_assignments if t == 'summary_2025']
      print(f"\n🔄 IMPORT MODE: main_summary - Processing 2025-Summary sheet only")
      
    elif import_mode == 'quick':
      # Calcs + small summaries (skip main 2025-Summary)
      target_assignments = [(s, t) for s, t in target_assignments 
                           if 'calcs' in t.lower() or (t != 'summary_2025' and 'summary' in t.lower())]
      print(f"\n🔄 IMPORT MODE: quick - Processing {len(target_assignments)} sheets (no main summary)")
      
    else:  # 'full'
      print(f"\n🔄 IMPORT MODE: full - Processing ALL {len(target_assignments)} sheets")

    # UNCHANGED: Delete all rows before import (this is correct)
    for tbl in ["inventory", "summary_2025", "office_calcs", "center_calcs", 
                "inventory_summary_total", "inventory_summary_office", 
                "inventory_summary_internal", "inventory_summary_center"]:
      if any(t == tbl for s, t in target_assignments):
        getattr(app_tables, tbl).delete_all_rows()
        print(f"Cleared table: {tbl}")

    # IMPROVED: Wrapped each sheet in try/except to handle partial failures
    for excel_sheet, table_name in target_assignments:
      try:
        print(f"\n=== Processing sheet: {excel_sheet} ===")
        ws = wb[excel_sheet]

        raw_df = xl.parse(excel_sheet, header=None)
        header_row_idx = find_header_row(raw_df)
        print(f"Found header at row {header_row_idx}")

        df = xl.parse(excel_sheet, skiprows=header_row_idx).replace({np.nan: None})
        df.columns = [str(col).strip().replace('$', '').strip() for col in df.columns]
        print(f"Columns found: {list(df.columns)}")

        url_col_name = find_column_by_keywords(df.columns, 'url', 'link', 'hyperlink', 'web', 'source')
        url_col_index = get_excel_column_index(df, url_col_name) if url_col_name else None

        if url_col_name:
          print(f"Found URL column: '{url_col_name}' at Excel column {url_col_index}")
        else:
          print("No URL column header found - will search all columns")

        item_col_name = find_column_by_keywords(df.columns, 'item', 'product', 'name', 'description')
        price_col_name = find_column_by_keywords(df.columns, 'amount', 'price', 'cost', 'each')

        current_subcategory = None

        for idx, row in df.iterrows():
          raw = dict(row)

          item_name = None
          if item_col_name and item_col_name in raw:
            item_name = str(raw[item_col_name]).strip()
          else:
            for col in ['Item', 'item', 'Items', 'Product', 'Name']:
              if col in raw and raw[col]:
                item_name = str(raw[col]).strip()
                break

          if not item_name or item_name in ["None", "Item", "nan"]:
            continue

          # Only detect subcategories in calcs/inventory sheets, NOT summary sheets
          if "calcs" in table_name.lower() or table_name == "inventory":
            if item_name.endswith(':'):
              current_subcategory = item_name.rstrip(':')
              print(f"  Found subcategory: {current_subcategory}")
              continue

            if item_name.isupper() and len(item_name.split()) <= 3:
              current_subcategory = item_name
              print(f"  Found subcategory: {current_subcategory}")
              continue

          # --- UNCHANGED: Your comprehensive URL extraction (works perfectly) ---
          excel_row_num = idx + header_row_idx + 2
          extracted_url = None

          # PRIORITY 1: Scan columns E through L (5-12) for URLs
          for col_num in range(5, 13):
            try:
              cell = ws.cell(row=excel_row_num, column=col_num)

              if cell.hyperlink and cell.hyperlink.target:
                extracted_url = cell.hyperlink.target
                print(f"  -> Found hyperlink in column {col_num}: {extracted_url}")
                break

              cell_val = str(cell.value) if cell.value else ""
              if "=HYPERLINK" in cell_val.upper():
                match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                if match:
                  extracted_url = match.group(1)
                  print(f"  -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                  break

              if cell_val and 'http' in cell_val.lower():
                cell_url = extract_url_from_text(cell_val)
                if cell_url:
                  extracted_url = cell_url
                  print(f"  -> Found URL text in column {col_num}: {extracted_url}")
                  break
            except:
              continue

          # PRIORITY 2: If we found a URL column header, check that specific column
          if not extracted_url and url_col_name and url_col_index:
            if url_col_name in raw and raw[url_col_name]:
              url_from_col = extract_url_from_text(str(raw[url_col_name]))
              if url_from_col:
                extracted_url = url_from_col
                print(f"  -> Found URL in '{url_col_name}' column (text): {extracted_url}")

            if not extracted_url:
              try:
                cell = ws.cell(row=excel_row_num, column=url_col_index)

                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f"  -> Found hyperlink in URL column (col {url_col_index}): {extracted_url}")

                elif cell.value:
                  cell_val = str(cell.value)
                  if "=HYPERLINK" in cell_val.upper():
                    match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                    if match:
                      extracted_url = match.group(1)
                      print(f"  -> Found HYPERLINK formula in URL column: {extracted_url}")
              except:
                pass

          # PRIORITY 3: Check if URL is embedded in item name
          if not extracted_url:
            url_from_text = extract_url_from_text(item_name)
            if url_from_text:
              extracted_url = url_from_text
              if ' -> ' in item_name:
                item_name = item_name.split(' -> ')[0].strip()
              print(f"  -> Found URL in item name: {extracted_url}")

          # PRIORITY 4: Scan columns F and G specifically
          if not extracted_url:
            for col_num in [6, 7]:
              try:
                cell = ws.cell(row=excel_row_num, column=col_num)

                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f"  -> Found hyperlink in column {col_num}: {extracted_url}")
                  break

                cell_val = str(cell.value) if cell.value else ""
                if "=HYPERLINK" in cell_val.upper():
                  match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                  if match:
                    extracted_url = match.group(1)
                    print(f"  -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                    break

                if cell_val and 'http' in cell_val.lower():
                  cell_url = extract_url_from_text(cell_val)
                  if cell_url:
                    extracted_url = cell_url
                    print(f"  -> Found URL text in column {col_num}: {extracted_url}")
                    break
              except:
                continue

          # PRIORITY 5: Last resort - scan all remaining columns
          if not extracted_url:
            max_col = ws.max_column if ws.max_column else 20
            for col_num in range(1, min(max_col + 1, 50)):
              if 5 <= col_num <= 12:
                continue
              try:
                cell = ws.cell(row=excel_row_num, column=col_num)

                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f"  -> Found hyperlink in column {col_num}: {extracted_url}")
                  break

                cell_val = str(cell.value) if cell.value else ""
                if "=HYPERLINK" in cell_val.upper():
                  match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                  if match:
                    extracted_url = match.group(1)
                    print(f"  -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                    break

                if cell_val and 'http' in cell_val.lower():
                  cell_url = extract_url_from_text(cell_val)
                  if cell_url:
                    extracted_url = cell_url
                    print(f"  -> Found URL text in column {col_num}: {extracted_url}")
                    break
              except:
                continue

          # Clean up item name
          if item_name.startswith('[') and ']' in item_name:
            item_name = item_name[item_name.index(']')+1:].strip()

          if extracted_url:
            print(f"[{excel_sheet}] {item_name} -> {extracted_url}")

          # Save to appropriate table
          if table_name == "inventory":
            cat = "Office" if "office" in excel_sheet.lower() else "Center"
            on_hand = int(clean_num(raw.get('On Hand', 0)))
            min_amt = int(clean_num(raw.get('Minimum Amt', 0)))

            # ADDED: Warning for unusual minimum amounts
            if min_amt > 1000:
              import_stats['warnings'].append(f"{item_name}: High minimum ({min_amt})")
            elif min_amt == 0:
              import_stats['warnings'].append(f"{item_name}: Minimum is 0")

            app_tables.inventory.add_row(
              Item=item_name, 
              Category=cat,
              Subcategory=current_subcategory,
              On_Hand=on_hand, 
              Minimum_Amt=min_amt
            )
            import_stats['inventory'] += 1

            if on_hand >= min_amt:
              calcs_table = app_tables.office_calcs if cat == "Office" else app_tables.center_calcs
              matching_items = calcs_table.search(Item=item_name)
              for existing_item in matching_items:
                existing_item.update(Ordered=False, Date_Ordered=None, PO_Number=None)

          elif "calcs" in table_name:
            price = 0
            if price_col_name and price_col_name in raw:
              price = clean_num(raw[price_col_name])
            else:
              for price_col in ['Amount/each', 'Amount', 'Price', 'Cost', 'Unit Price', 'Each']:
                if price_col in raw:
                  price = clean_num(raw[price_col])
                  if price > 0:
                    break

            # ADDED: Warning for missing data
            if not extracted_url:
              import_stats['warnings'].append(f"{item_name}: No URL found")
            if price == 0:
              import_stats['warnings'].append(f"{item_name}: No price found")

            getattr(app_tables, table_name).add_row(
              Item=item_name, Item_Link=extracted_url, Price=price, Ordered=False
            )
            import_stats[table_name] += 1

          elif "summary" in table_name:
            # Handle all summary tables
            location = None
            location_code = None  # Will store as integer or None
            gl_amt = 0
            po_amt = 0
            other_amt = 0
            total_cost = 0
            
            # Extract Location Code (Column B) - store as NUMBER
            for loc_code_col in ['Location #', 'Location Code', 'Location_Code', 'Loc Code', 'Code', 'Loc #', 'Site Code', 'Site #']:
              if loc_code_col in raw and pd.notna(raw[loc_code_col]):
                raw_value = raw[loc_code_col]
                
                # Try to convert to integer
                try:
                  if isinstance(raw_value, (int, float)):
                    location_code = int(raw_value)  # Store as actual number
                  elif isinstance(raw_value, str):
                    # Try to parse string as number
                    location_code = int(float(raw_value.strip()))
                  
                  if location_code:
                    break
                except (ValueError, TypeError):
                  # If it's not a number (like "NELC"), skip it - it's probably the location name
                  continue
            
            # Extract Location Name
            for loc_col in ['Location Name', 'Location', 'Center', 'Site', 'Facility']:
              if loc_col in raw and pd.notna(raw[loc_col]):
                loc_value = str(raw[loc_col]).strip()
                # Skip if it's just a number or looks like a code
                if loc_value and not loc_value.replace('.', '').replace('-', '').isdigit():
                  location = loc_value
                  break
            
            # Use the complete location display function
            location = get_complete_location_display(location_code, location)
            
            # Extract GL Amount (Column H)
            for gl_col in ['GL Amt', 'GL_Amt', 'GL Amount', 'General Ledger', 'GL', 'G/L']:
              if gl_col in raw and pd.notna(raw[gl_col]):
                gl_amt = clean_num(raw[gl_col])
                if gl_amt != 0:
                  break
            
            # Extract PO Amount (Column I)
            for po_col in ['PO Amt', 'PO_Amt', 'PO Orders', 'PO Amount', 'Purchase Orders', 'PO']:
              if po_col in raw and pd.notna(raw[po_col]):
                po_amt = clean_num(raw[po_col])
                if po_amt != 0:
                  break
            
            # Extract Other Amount (Column J)
            for other_col in ['Other Amt', 'Other_Amt', 'Other', 'Misc', 'Miscellaneous']:
              if other_col in raw and pd.notna(raw[other_col]):
                other_amt = clean_num(raw[other_col])
                if other_amt != 0:
                  break
            
            # Extract Total Amount (Column K)
            for cost_col in ['Total Amt', 'Total_Amt', 'Total Cost', 'Total_Cost', 'Total', 'Amount', 'Amt']:
              if cost_col in raw and pd.notna(raw[cost_col]):
                total_cost = clean_num(raw[cost_col])
                if total_cost != 0:
                  break
            
            # Validation warning
            if table_name == "summary_2025":
              calculated_total = gl_amt + po_amt + other_amt
              if abs(calculated_total - total_cost) > 0.01 and total_cost > 0:
                print(f"  ⚠️  Totals mismatch for {location}: GL+PO+Other=${calculated_total:.2f}, Total=${total_cost:.2f}")
            
            # Skip completely empty rows (formatting-only rows with no actual data)
            # A row is considered empty ONLY if it has NO location data at all AND all amounts are zero
            has_any_location = bool(location) or bool(location_code)
            has_any_amount = (gl_amt != 0 or po_amt != 0 or other_amt != 0 or total_cost != 0)
            
            is_empty_row = (not has_any_location) and (not has_any_amount)
            
            if is_empty_row:
              continue  # Skip this row entirely
            
            # Insert row
            if location or location_code:
              # All summary tables get full breakdown
              if table_name in ["summary_2025", "inventory_summary_office", 
                                "inventory_summary_center", "inventory_summary_internal"]:
                
                table = getattr(app_tables, table_name)
                
                # Build row data based on available columns
                # Check first row to see which column names exist
                sample_row = list(table.search())
                has_Location = 'Location' in (sample_row[0].keys() if sample_row else [])
                has_Total_Cost = 'Total_Cost' in (sample_row[0].keys() if sample_row else [])
                
                # Build kwargs dynamically
                kwargs = {
                  'Location_Code': location_code,
                  'GL_Amt': gl_amt,
                  'PO_Amt': po_amt,
                  'Other_Amt': other_amt,
                }
                
                # Add location with correct column name
                if has_Location or table_name == "summary_2025":
                  kwargs['Location'] = location or "Unknown"
                else:
                  kwargs['location_name'] = location or "Unknown"
                
                # Add total with correct column name
                if has_Total_Cost or table_name == "summary_2025":
                  kwargs['Total_Cost'] = total_cost
                else:
                  kwargs['total_amt'] = total_cost
                
                table.add_row(**kwargs)
                
                import_stats[table_name] += 1
                
                # Print progress less frequently (every 20 rows) to speed up import
                if import_stats[table_name] % 20 == 0:
                  print(f"  ✓ Processed {import_stats[table_name]} {table_name} entries...")
              else:
                # Any other future summary tables - simpler format
                getattr(app_tables, table_name).add_row(
                  Location=location,
                  Total_Cost=total_cost
                )
                import_stats[table_name] += 1

      except Exception as sheet_error:
        # ADDED: Per-sheet error handling
        error_msg = f"Error processing sheet '{excel_sheet}': {str(sheet_error)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        import_stats['errors'].append(error_msg)
        continue  # Continue with next sheet

    # Skip the slow inventory restocking check during import - can be done separately
    # This was taking too long and causing timeouts
    # print("Running final stock check to reset 'Ordered' status...")
    # (Commented out to speed up import)

    # IMPROVED: Return detailed statistics instead of just sheet names
    total_items = sum([
      import_stats['inventory'], 
      import_stats['office_calcs'], 
      import_stats['center_calcs'], 
      import_stats['summary_2025'],
      import_stats['inventory_summary_total'],
      import_stats['inventory_summary_office'],
      import_stats['inventory_summary_internal'],
      import_stats['inventory_summary_center']
    ])
    
    # Print final summary
    print("\n" + "="*60)
    print("📊 IMPORT COMPLETE - FINAL SUMMARY")
    print("="*60)
    print(f"Total Items Imported: {total_items}")
    print(f"  • Office Calcs: {import_stats['office_calcs']}")
    print(f"  • Center Calcs: {import_stats['center_calcs']}")
    print(f"  • Summary 2025: {import_stats['summary_2025']}")
    print(f"  • Summary Office: {import_stats['inventory_summary_office']}")
    print(f"  • Summary Center: {import_stats['inventory_summary_center']}")
    print(f"  • Summary Internal: {import_stats['inventory_summary_internal']}")
    print(f"  • Summary Total: {import_stats['inventory_summary_total']}")
    print(f"  • Inventory: {import_stats['inventory']}")
    print("="*60 + "\n")

    return {
      'success': True,
      'import_mode': import_mode,
      'sheets_processed': [s for s, t in target_assignments],
      'stats': import_stats,
      'total_items': total_items
    }

  except Exception as e:
    # ADDED: Top-level error handling
    print(f"CRITICAL ERROR in process_excel_import: {str(e)}")
    import traceback
    traceback.print_exc()

    return {
      'success': False,
      'error': str(e),
      'stats': import_stats
    }

# --- 4. SHOPPING & HISTORY ---
def shopping_ordering_source(item_link):
  """Derive the ordering source from the product URL without opening it."""
  url = (item_link or '').strip()
  if not url:
    return 'No ordering link', None
  if '://' not in url and not url.startswith(('/', '#')):
    url = 'https://' + url
  try:
    parsed = urlsplit(url)
    host = (parsed.hostname or '').rstrip('.')
  except ValueError:
    return 'No ordering link', None
  if parsed.scheme not in ('http', 'https') or '.' not in host or parsed.username is not None:
    return 'No ordering link', None
  if host == 'a.co' or host == 'amzn.to' or host == 'amazon.com' or host.endswith('.amazon.com'):
    return 'Amazon', url
  return host.removeprefix('www.'), url


@anvil.server.callable
def get_shopping_list():
  """
  IMPROVED: Performance optimization - load all data once instead of multiple queries
  WHY: Faster execution, especially with large datasets
  """
  # Load everything ONCE
  off_m = {r['Item']: r for r in app_tables.office_calcs.search()}
  cen_m = {r['Item']: r for r in app_tables.center_calcs.search()}

  print(f"Office calcs items: {len(off_m)}")
  print(f"Center calcs items: {len(cen_m)}")
  if off_m:
    sample_item = list(off_m.values())[0]
    print(f"Sample office item: {list(off_m.keys())[0]} -> Price: {sample_item.get('Price')}, URL: {sample_item.get('Item_Link')}")

  items = []
  for inv in app_tables.inventory.search():
    item_nm = inv['Item']
    cat = inv.get('Category') or 'Office'
    master = off_m if cat == "Office" else cen_m
    info = master.get(item_nm, {})
    oh, ma = (inv.get('On_Hand') or 0), (inv.get('Minimum_Amt') or 0)

    if oh < ma:
      price = (info.get('Price') or 0) if info else 0
      supplier, item_link = shopping_ordering_source(info.get('Item_Link') if info else None)
      ordered = bool(info.get('Ordered')) if info else False

      if len(items) < 3:
        print(f"Shopping item: {item_nm} | Cat: {cat} | Found in calcs: {item_nm in master} | Price: {price} | URL: {item_link}")

      items.append({
        'Item': item_nm, 
        'On_Hand': oh, 
        'Minimum_Amt': ma,
        'Category': cat, 
        'Source': cat,
        'Supplier': supplier,
        'Inventory_ID': inv.get_id(),
        'Price': price,
        'Item_Link': item_link, 
        'Ordered': ordered,
        'PO_Number': info.get('PO_Number') if ordered else None
      })

  print(f"Total shopping list items: {len(items)}")
  # ADDED: Sort with ordered items last for better UX
  return sorted(items, key=lambda x: (x.get('Ordered', False), x['Category'], x['Item']))

@anvil.server.callable
@tables.in_transaction
def check_ordered(item_name, category, status, po_number=None, ordered_quantity=None, inventory_id=None):
  """
  IMPROVED: Better error handling and feedback + AUDIT LOGGING
  WHY: Prevents silent failures, handles duplicates properly, tracks all changes
  """
  if status and po_number is not None:
    if not isinstance(po_number, str) or not po_number.strip() or len(po_number.strip()) > 100:
      raise ValueError("Enter a PO number of 1 to 100 characters.")
    po_number = po_number.strip()

  table = app_tables.office_calcs if category == "Office" else app_tables.center_calcs

  # Use .search() to handle potential duplicates
  matching_rows = list(table.search(Item=str(item_name).strip()))

  if not matching_rows:
    print(f"Warning: Item '{item_name}' not found in {category} calcs table")
    return False

  if ordered_quantity is not None:
    require_admin()
    quantity = whole_quantity(ordered_quantity)
    if not status or not po_number:
      raise ValueError("A PO number is required to save an ordered quantity.")
    inventory = app_tables.inventory.get_by_id(inventory_id)
    if inventory is None or inventory['Item'] != item_name or (inventory['Category'] or 'Office') != category:
      raise ValueError("This inventory item changed. Refresh the shopping list.")
    existing = app_tables.purchase_order_lines.get(
      po_number=po_number, item_name=item_name, category=category, canceled=False
    )
    if existing is None:
      if any(row['Ordered'] for row in matching_rows):
        raise ValueError("This item is already marked ordered. Refresh the shopping list.")
      app_tables.purchase_order_lines.add_row(
        po_number=po_number, item_name=item_name, category=category, inventory_item=inventory,
        ordered_quantity=quantity, received_quantity=0, canceled=False, ordered_at=datetime.now(),
      )
    elif existing['ordered_quantity'] != quantity or existing['inventory_item'] != inventory:
      raise ValueError("This item already has a different quantity or stock row on that PO.")
  elif not status:
    for previous_po in {row['PO_Number'] for row in matching_rows if row['Ordered'] and row['PO_Number']}:
      line = app_tables.purchase_order_lines.get(
        po_number=previous_po, item_name=item_name, category=category, canceled=False
      )
      if line is not None:
        require_admin()
        if line['received_quantity']:
          raise ValueError("This item already has a receipt and cannot be unchecked.")
        line['canceled'] = True

  # Update all matching rows (handles duplicates if they exist)
  for row in matching_rows:
    old_status = row['Ordered']
    saved_po = (po_number or row['PO_Number']) if status else None
    if old_status == status and row['PO_Number'] == saved_po:
      continue
    ordered_date = (row['Date_Ordered'] or datetime.now().date()) if status else None
    row.update(Ordered=status, Date_Ordered=ordered_date, PO_Number=saved_po)

    # AUDIT LOG
    log_audit(
      action='UPDATE',
      table_name=f'{category.lower()}_calcs',
      item_name=item_name,
      old_value=f"Ordered: {old_status}",
      new_value=f"Ordered: {status}",
      details=(f"Shopping list: Marked ordered (PO {po_number})" if status and po_number
               else f"Shopping list: Marked as {'ordered' if status else 'not ordered'}")
    )

  if len(matching_rows) > 1:
    print(f"Warning: Found {len(matching_rows)} duplicate entries for '{item_name}'")

  return True

def whole_quantity(value):
  if (isinstance(value, bool) or not isinstance(value, (int, float))
      or not 1 <= value <= 1000000 or int(value) != value):
    raise ValueError("Enter a whole quantity from 1 to 1,000,000.")
  return int(value)


@anvil.server.callable
def get_receiving_orders():
  require_admin()
  orders = {}
  for row in app_tables.purchase_order_lines.search(
      tables.order_by('ordered_at', ascending=False), canceled=False):
    orders.setdefault(row['po_number'], []).append({
      'id': row.get_id(), 'item': row['item_name'], 'category': row['category'],
      'ordered': row['ordered_quantity'], 'received': row['received_quantity'],
    })
  return orders


@anvil.server.callable
@tables.in_transaction
def record_po_receipt(line_id, quantity, delivery_reference):
  require_admin()
  quantity = whole_quantity(quantity)
  if not isinstance(delivery_reference, str) or not 1 <= len(delivery_reference.strip()) <= 100:
    raise ValueError("Enter a packing slip or delivery reference.")
  delivery_reference = delivery_reference.strip().casefold()
  line = app_tables.purchase_order_lines.get_by_id(line_id)
  if line is None or line['canceled']:
    raise ValueError("This purchase order line is unavailable.")

  previous = app_tables.stock_transactions.get(
    purchase_order_line_id=line_id, delivery_reference=delivery_reference
  )
  if previous is not None:
    if previous['change'] != quantity:
      raise ValueError("That delivery reference was already recorded for this item with a different count.")
    return False

  outstanding = line['ordered_quantity'] - line['received_quantity']
  if quantity > outstanding:
    raise ValueError(f"Only {outstanding} are due. Review the packing slip before receiving extras.")

  item = line['inventory_item']
  if item is None:
    # A workbook import may have replaced Data Table row IDs.
    matches = list(app_tables.inventory.search(Item=line['item_name'], Category=line['category']))
    if len(matches) != 1:
      raise ValueError("The inventory item is missing or duplicated. Check Inventory before receiving it.")
    item = matches[0]
  new_stock = (item['On_Hand'] or 0) + quantity
  item.update(On_Hand=new_stock, To_Order=max(0, (item['Minimum_Amt'] or 0) - new_stock))
  line.update(inventory_item=item, received_quantity=line['received_quantity'] + quantity)
  app_tables.stock_transactions.add_row(
    item=item, change=quantity, transaction_type='received', po_number=line['po_number'],
    user=anvil.users.get_user(), timestamp=datetime.now(),
    purchase_order_line_id=line_id, delivery_reference=delivery_reference,
  )
  return True


@anvil.server.callable
@tables.in_transaction
def add_missing_purchase_link(item_name, category, item_link):
  require_admin()
  if not isinstance(item_link, str) or len(item_link) > 2000:
    raise ValueError("Enter a product URL up to 2,000 characters.")
  _, url = shopping_ordering_source(item_link)
  if url is None or any(character.isspace() for character in url):
    raise ValueError("Enter a valid product URL.")
  table = app_tables.office_calcs if category == "Office" else app_tables.center_calcs
  rows = list(table.search(Item=item_name))
  if not rows:
    # The inventory item may predate its matching calculation row.
    if not list(app_tables.inventory.search(Item=item_name, Category=category)):
      raise ValueError("This inventory item is no longer available.")
    table.add_row(Item=item_name, Item_Link=url, Ordered=False)
  else:
    for row in rows:
      if shopping_ordering_source(row['Item_Link'])[1] is None:
        row['Item_Link'] = url
  return True


@anvil.server.callable
def get_machform_inbox():
  require_admin()
  rows = app_tables.machform_inbox.search(tables.order_by('received_at', ascending=False))
  return [
    {'form_id': row['form_id'], 'entry_id': row['entry_id'], 'received_at': row['received_at'],
     'payload': row['payload_json']}
    for row in islice(rows, 25)
  ]


@anvil.server.callable
def get_ordered_history():
  """UNCHANGED - Your original code works perfectly"""
  history = []
  for table in [app_tables.office_calcs, app_tables.center_calcs]:
    source = "Office" if table == app_tables.office_calcs else "Center"
    for r in table.search(Ordered=True):
      history.append({
        'Item': r['Item'], 
        'Source': source,
        'Date': r['Date_Ordered'],
        'PO_Number': r['PO_Number'],
        'Link': r['Item_Link']
      })
  return sorted(history, key=lambda x: str(x['Date']), reverse=True)

@anvil.server.callable
def sync_inventory_status():
  """UNCHANGED - Your original code works perfectly"""
  reset_count = 0
  for inv in app_tables.inventory.search():
    oh = inv['On_Hand'] or 0
    ma = inv['Minimum_Amt'] or 0

    if oh >= ma:
      item_nm = inv['Item']
      cat = inv['Category']

      tbl = app_tables.office_calcs if cat == "Office" else app_tables.center_calcs
      matching_rows = tbl.search(Item=item_nm)

      for row in matching_rows:
        if row['Ordered'] == True:
          row.update(Ordered=False, Date_Ordered=None, PO_Number=None)
          reset_count += 1

  return reset_count

# --- 5. UTILITY FUNCTIONS ---

@anvil.server.callable
def get_import_warnings():
  """
  NEW FUNCTION: Get data quality warnings
  WHY: Helps identify missing URLs, prices, or unusual minimums
  USAGE: Call after import to show user what needs attention
  """
  warnings = []

  # Check for missing URLs
  for table_name in ['office_calcs', 'center_calcs']:
    table = getattr(app_tables, table_name)
    for item in table.search():
      if not item.get('Item_Link'):
        warnings.append(f"{item['Item']} ({table_name}): Missing URL")
      if not item.get('Price') or item['Price'] == 0:
        warnings.append(f"{item['Item']} ({table_name}): Missing price")

  # Check for unusual minimum amounts
  for item in app_tables.inventory.search():
    min_amt = item.get('Minimum_Amt', 0)
    if min_amt > 1000:
      warnings.append(f"{item['Item']}: Unusually high minimum ({min_amt})")
    elif min_amt == 0:
      warnings.append(f"{item['Item']}: Minimum amount is 0")

  return warnings

@anvil.server.callable
def get_inventory_stats():
  """
  NEW FUNCTION: Get comprehensive inventory statistics
  WHY: Useful for dashboard/summary views
  USAGE: Call to display overview cards
  """
  all_items = list(app_tables.inventory.search())

  total_items = len(all_items)
  low_stock = sum(1 for item in all_items if (item['On_Hand'] or 0) < (item['Minimum_Amt'] or 0))
  office_items = sum(1 for item in all_items if item['Category'] == 'Office')
  center_items = sum(1 for item in all_items if item['Category'] == 'Center')

  # Category breakdown
  categories = {}
  for item in all_items:
    subcat = item.get('Subcategory', 'Uncategorized')
    categories[subcat] = categories.get(subcat, 0) + 1

  return {
    'total_items': total_items,
    'low_stock_count': low_stock,
    'office_count': office_items,
    'center_count': center_items,
    'subcategories': categories
  }

@anvil.server.callable
def export_order_history_csv(history):
  """Generate CSV file from order history"""
  import csv
  from io import StringIO

  try:
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(['Date Ordered', 'Item', 'Category', 'Link', 'PO Number'])

    for item in history:
      po_number = str(item.get('PO_Number') or '')
      if po_number.startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        po_number = "'" + po_number
      writer.writerow([
        str(item.get('Date', '')),
        item.get('Item', ''),
        item.get('Source', ''),
        item.get('Link', ''),
        po_number
      ])

    csv_data = output.getvalue()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')

    return anvil.BlobMedia(
      'text/csv',
      csv_data.encode(),
      name=f'order_history_{timestamp}.csv'
    )

  except Exception as e:
    print(f"Server CSV export error: {e}")
    import traceback
    traceback.print_exc()
    return None


@anvil.server.callable
def clear_order_history():
  """Clear all order history"""
  require_admin()
  reset_count = 0

  for table in [app_tables.office_calcs, app_tables.center_calcs]:
    for row in table.search(Ordered=True):
      row.update(Ordered=False, Date_Ordered=None, PO_Number=None)
      reset_count += 1

  print(f"Cleared {reset_count} order history records")
  return reset_count

@anvil.server.callable
def save_machform_order(order_data):
  """Save new MachForm order"""
  try:
    app_tables.machform_orders.add_row(
      date_requested=order_data['date_requested'],
      requester_name=order_data['requester_name'],
      location=order_data['location'],
      category=order_data['category'],
      items_summary=order_data['items_summary'],
      total_cost=order_data['total_cost'],
      status='Pending',
      date_filled=None,
      notes=order_data.get('notes', '')
    )
    print(f"✅ Saved MachForm order: {order_data['requester_name']}")
    return True
  except Exception as e:
    print(f"❌ Save error: {e}")
    import traceback
    traceback.print_exc()
    return False


@anvil.server.callable
def get_machform_orders(status_filter="All"):
  """Return a bounded, read-only preview using the configured order columns."""
  if anvil.users.get_user() is None:
    raise PermissionError("Sign in to view orders")
  filters = {}
  if status_filter and status_filter != "All":
    filters['fulfillment_status'] = status_filter
  orders = app_tables.machform_orders.search(
    tables.order_by('fulfilled_date', ascending=False), **filters
  )
  rows = list(islice(orders, 101))
  return {
    'orders': [
      {column: order[column] for column in (
        'items_json', 'fulfillment_status', 'fulfilled_by', 'fulfilled_date', 'notes'
      )}
      for order in rows[:100]
    ],
    'has_more': len(rows) > 100,
  }


@anvil.server.callable
def update_order_status(order_id, new_status):
  """Update MachForm order status"""
  try:
    order = app_tables.machform_orders.get_by_id(order_id)
    if order:
      order['status'] = new_status
      if new_status == 'Filled':
        order['date_filled'] = datetime.now().date()
      else:
        order['date_filled'] = None
      print(f"✅ Updated order {order_id} to {new_status}")
      return True
    else:
      print(f"❌ Order {order_id} not found")
      return False
  except Exception as e:
    print(f"❌ Status update error: {e}")
    import traceback
    traceback.print_exc()
    return False


@anvil.server.callable
def log_stock_transaction(item, change, po_number=None, req_number=None, transaction_type=None):
  """
  Log stock changes with PO# or Requisition#
  USAGE: log_stock_transaction(item_row, +1, po_number="PO12345", transaction_type='received')
  
  NOTE: Fails gracefully if stock_transactions table doesn't exist yet
  """
  try:
    # Check if table exists
    if not hasattr(app_tables, 'stock_transactions'):
      print("⚠️ stock_transactions table not found - skipping log")
      return
    
    user = anvil.users.get_user()
    
    app_tables.stock_transactions.add_row(
      item=item,
      change=change,
      transaction_type=transaction_type,
      po_number=po_number or "",
      req_number=req_number or "",
      user=user,
      timestamp=datetime.now()
    )
    
    print(f"📦 Stock Transaction: {item['Item']} {change:+d} - {transaction_type} - {po_number or req_number}")
    
  except AttributeError:
    print("⚠️ stock_transactions table not found - skipping log")
  except Exception as e:
    print(f"Stock transaction logging error: {e}")
    # Don't fail the main operation if logging fails


@anvil.server.callable
def log_audit(action, table_name, item_name, old_value=None, new_value=None, details=None):
  """
  Log an audit entry
  USAGE: log_audit('UPDATE', 'inventory', 'Paper Towels', '10', '25', 'On_Hand changed')
  """
  try:
    user = anvil.users.get_user()
    user_email = user['email'] if user else 'System'
    
    app_tables.audit_logs.add_row(
      timestamp=datetime.now(),
      user_email=user_email,
      action=action,
      table_name=table_name,
      item_name=item_name,
      old_value=str(old_value) if old_value is not None else None,
      new_value=str(new_value) if new_value is not None else None,
      details=details
    )
    
    print(f"📝 Audit: {user_email} - {action} - {table_name}/{item_name}")
    
  except Exception as e:
    print(f"Audit logging error: {e}")
    # Don't fail the main operation if audit logging fails


@anvil.server.callable
def get_audit_logs(limit=100, table_filter=None):
  """Get recent audit logs"""
  require_admin()
  try:
    search_args = {}
    if table_filter and table_filter != "All":
      search_args['table_name'] = table_filter
    
    logs = app_tables.audit_logs.search(
      tables.order_by('timestamp', ascending=False),
      **search_args
    )
    
    result = []
    for log in islice(logs, limit):
      result.append({
        'timestamp': log['timestamp'],
        'user_email': log['user_email'],
        'action': log['action'],
        'table_name': log['table_name'],
        'item_name': log['item_name'],
        'old_value': log['old_value'],
        'new_value': log['new_value'],
        'details': log['details']
      })
    
    return result
    
  except Exception as e:
    print(f"Error getting audit logs: {e}")
    return []


@anvil.server.callable
def get_current_user_role():
  """Get the current user's role"""
  user = anvil.users.get_user()
  if not user:
    return None
  return user.get('role', 'staff')


@anvil.server.callable
def is_admin():
  """Check if current user is admin"""
  role = get_current_user_role()
  return role == 'admin'


@anvil.server.callable
def require_admin():
  """Raise exception if user is not admin"""
  if not is_admin():
    raise Exception("Admin access required for this action")


@anvil.server.callable
def update_order_fulfillment(order_id, new_status, notes):
  """
  Update order fulfillment status
  WHY: Track which orders are complete/partial/pending
  """
  try:
    user = anvil.users.get_user()
    order = app_tables.machform_orders.get_by_id(order_id)
    
    if order:
      old_status = order['status']
      order['status'] = new_status
      order['notes'] = notes
      
      # Mark as fulfilled if status is Filled
      if new_status == 'Filled':
        order['fulfilled_by'] = user['email']
        order['fulfilled_date'] = datetime.now().date()
      
      # Audit log
      log_audit(
        action='UPDATE',
        table_name='machform_orders',
        item_name=order['requester_name'],
        old_value=f"Status: {old_status}",
        new_value=f"Status: {new_status}",
        details=f"Order fulfillment updated by {user['email']}"
      )
      
      print(f"✅ Updated order {order_id} to {new_status}")
      return True
    else:
      print(f"❌ Order {order_id} not found")
      return False
      
  except Exception as e:
    print(f"❌ Update error: {e}")
    import traceback
    traceback.print_exc()
    return False


MACHFORM_WEBHOOK_PATH = '/machform-orders'
MACHFORM_FORM_IDS = ('161659', '161453')


def _machform_webhook_secret():
  try:
    import anvil.secrets
    return anvil.secrets.get_secret('machform_webhook_secret')
  except Exception:
    # A missing Secrets service or unset secret leaves the receiver disabled.
    return None


@anvil.server.callable
def get_machform_webhook_settings():
  require_admin()
  base_url = anvil.server.get_app_origin().rstrip('/') + '/_/api' + MACHFORM_WEBHOOK_PATH
  return {
    'urls': [(form_id, f"{base_url}/{form_id}") for form_id in MACHFORM_FORM_IDS],
    'enabled': bool(_machform_webhook_secret()),
  }


@tables.in_transaction
def _save_machform_submission(form_id, entry_id, payload):
  inbox = app_tables.machform_inbox
  if entry_id and inbox.get(form_id=form_id, entry_id=entry_id) is not None:
    return False
  inbox.add_row(
    form_id=form_id,
    entry_id=entry_id,
    received_at=datetime.now(timezone.utc),
    payload_json=json.dumps(payload, ensure_ascii=False),
  )
  return True


@anvil.server.http_endpoint(MACHFORM_WEBHOOK_PATH + '/:form_id', methods=['POST'])
def receive_machform_order(form_id):
  request = anvil.server.request
  respond = anvil.server.HttpResponse
  if form_id not in MACHFORM_FORM_IDS:
    return respond(404, 'Unknown MachForm form.')
  secret = _machform_webhook_secret()
  if not secret:
    return respond(503, 'MachForm receiver is disabled.')

  content_type = request.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
  if content_type not in ('application/json', 'application/x-www-form-urlencoded'):
    return respond(415, 'Send JSON or URL-encoded form data.')

  try:
    body = request.body.get_bytes()
    if len(body) > 65536:
      return respond(413, 'Order payload is too large.')
    if content_type == 'application/json':
      order = json.loads(body.decode('utf-8'))
    else:
      fields = parse_qs(body.decode('utf-8'), keep_blank_values=True, max_num_fields=500)
      order = {name: values[0] if len(values) == 1 else values for name, values in fields.items()}
  except (ValueError, UnicodeError):
    return respond(400, 'Invalid order payload.')

  if not isinstance(order, dict):
    return respond(400, 'Expected an order object.')
  credential = request.headers.get('X-MachForm-Token') or order.get('webhook_token')
  if not isinstance(credential, str) or not compare_digest(
      credential.encode('utf-8'), secret.encode('utf-8')):
    return respond(401, 'Invalid webhook credential.')

  order.pop('webhook_token', None)
  if not order:
    return respond(400, 'No submission fields received.')

  entry_id = order.get('entry_id')
  if isinstance(entry_id, (str, int)) and not isinstance(entry_id, bool):
    entry_id = str(entry_id).strip() or None
  else:
    entry_id = None
  created = _save_machform_submission(form_id, entry_id, order)
  return respond(201 if created else 200, 'Submission saved.' if created else 'Submission already saved.')
