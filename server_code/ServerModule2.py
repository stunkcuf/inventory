import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import anvil.tables.query as q
import pandas as pd
import io
import numpy as np
import re
from datetime import datetime
import openpyxl


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
def get_inventory_fast(category="All", search_query=None, subcategory=None):
  """UNCHANGED - Your original code works perfectly"""
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  if subcategory and subcategory != "All":
    search_args['Subcategory'] = subcategory
  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")
  return app_tables.inventory.search(tables.order_by("Item", ascending=True), **search_args)

@anvil.server.callable
def get_subcategories(category="All"):
  """UNCHANGED - Your original code works perfectly"""
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category

  items = app_tables.inventory.search(**search_args)
  subcategories = set()
  for item in items:
    subcat = item.get('Subcategory')
    if subcat:
      subcategories.add(subcat)

  return sorted(list(subcategories))

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

@anvil.server.callable
def get_spending_summary_by_table(table_name='summary_2025'):
  """
  VERSION 2: Get spending summary from a specific table with AGGREGATION
  WHY: Handles both column name formats and aggregates multiple rows per location
  AGGREGATES: Sums multiple entries for the same location
  """
  print(f"=== get_spending_summary_by_table called for {table_name} ===")

  # Validate table name to prevent errors
  valid_tables = [
    'summary_2025',
    'inventory_summary_total',
    'inventory_summary_office',
    'inventory_summary_internal',
    'inventory_summary_center'
  ]

  if table_name not in valid_tables:
    print(f"Invalid table name: {table_name}")
    return [("No Data", 0)]

  try:
    # Get the table dynamically
    table = getattr(app_tables, table_name)
    data = list(table.search())

    print(f"Found {len(data)} rows in {table_name}")

    if not data:
      return [("No Data", 0)]

    # Check first row to see what columns exist
    first_row = data[0]
    available_columns = list(first_row.keys())
    print(f"Available columns in {table_name}: {available_columns}")

    # Build results - aggregate by location
    location_totals = {}

    for r in data:
      # Try different location column variations
      location = (
        r.get('location_name') or      # inventory summary tables (lowercase)
        r.get('Location') or            # summary_2025 format
        r.get('Location Name') or 
        r.get('Location #') or 
        None
      )

      # Try different cost column variations
      total_cost = (
        r.get('total_amt') or          # inventory summary tables (lowercase)
        r.get('Total_Cost') or         # summary_2025 format
        r.get('Total Amt') or 
        r.get('Total_Amt') or 
        0
      )

      # Convert to float if needed
      if isinstance(total_cost, str):
        total_cost = clean_num(total_cost)
      else:
        total_cost = float(total_cost) if total_cost else 0

      # Skip empty rows
      if location and location.strip():
        location = location.strip()

        # Aggregate totals by location
        if location in location_totals:
          location_totals[location] += total_cost
        else:
          location_totals[location] = total_cost

    # Convert to list of tuples and filter out zeros
    results = [
      (loc, cost) 
      for loc, cost in location_totals.items() 
      if cost > 0
    ]

    # Sort by location name
    results.sort(key=lambda x: x[0])

    print(f"Aggregated {len(data)} rows into {len(results)} locations")
    for loc, cost in results:
      print(f"  {loc}: ${cost:,.2f}")

    return results if results else [("No Data", 0)]

  except Exception as e:
    print(f"Error loading {table_name}: {e}")
    import traceback
    traceback.print_exc()
    return [("No Data", 0)]


@anvil.server.callable
def get_available_summary_tables():
  """
  NEW: Return list of available summary tables
  WHY: Populate dropdown with user-friendly names
  USAGE: Called by SummaryForm to populate dropdown options
  """
  return [
    ('2025 Summary', 'summary_2025'),
    ('Total Inventory Summary', 'inventory_summary_total'),
    ('Office Inventory Summary', 'inventory_summary_office'),
    ('Internal Inventory Summary', 'inventory_summary_internal'),
    ('Center Inventory Summary', 'inventory_summary_center'),
  ]

# --- 3. THE "DEEP SCAN" EXCEL IMPORT ---
@anvil.server.callable
def process_excel_import(file):
  """
  IMPROVED: Added comprehensive error handling, import statistics, and support for multiple summary tables
  WHY: Users need to know what succeeded/failed during import
  ADDED: Returns detailed import summary instead of just sheet names
  """

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
                existing_item['Ordered'] = False
                existing_item['Date_Ordered'] = None

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
            # NEW: Handle all summary tables (2025, total, office, internal, center)
            location = None
            total_cost = 0

            for loc_col in ['Location Name', 'Location', 'Location #']:
              if loc_col in raw and raw[loc_col]:
                location = raw[loc_col]
                break

            for cost_col in ['Total Amt', 'Total_Amt', 'Total_Cost', 'Total Cost', 'Amt', 'GL Amt']:
              if cost_col in raw and raw[cost_col]:
                total_cost = clean_num(raw[cost_col])
                if total_cost > 0:
                  break

            if location:
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

    # UNCHANGED: Final sweep to reset 'Ordered' status (your logic is correct)
    print("Running final stock check to reset 'Ordered' status...")
    for inv_row in app_tables.inventory.search():
      oh = inv_row['On_Hand'] or 0
      ma = inv_row['Minimum_Amt'] or 0
      item_nm = inv_row['Item']
      cat = inv_row['Category']

      if oh >= ma:
        calcs_table = app_tables.office_calcs if cat == "Office" else app_tables.center_calcs
        matching_calcs = calcs_table.search(Item=item_nm)
        for existing_calc in matching_calcs:
          if existing_calc.get('Ordered'):
            existing_calc['Ordered'] = False
            existing_calc['Date_Ordered'] = None
            print(f"Restocked: Reset {item_nm} in {cat} calcs.")

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

    return {
      'success': True,
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
    cat = inv.get('Category', 'Office')
    master = off_m if cat == "Office" else cen_m
    info = master.get(item_nm, {})
    oh, ma = (inv.get('On_Hand') or 0), (inv.get('Minimum_Amt') or 0)

    if oh < ma:
      price = info.get('Price', 0) if info else 0
      item_link = info.get('Item_Link') if info else None
      ordered = info.get('Ordered', False) if info else False

      if len(items) < 3:
        print(f"Shopping item: {item_nm} | Cat: {cat} | Found in calcs: {item_nm in master} | Price: {price} | URL: {item_link}")

      items.append({
        'Item': item_nm, 
        'On_Hand': oh, 
        'Minimum_Amt': ma,
        'Category': cat, 
        'Source': cat, 
        'Price': price,
        'Item_Link': item_link, 
        'Ordered': ordered
      })

  print(f"Total shopping list items: {len(items)}")
  # ADDED: Sort with ordered items last for better UX
  return sorted(items, key=lambda x: (x.get('Ordered', False), x['Category'], x['Item']))

@anvil.server.callable
def check_ordered(item_name, category, status):
  """
  IMPROVED: Better error handling and feedback + AUDIT LOGGING
  WHY: Prevents silent failures, handles duplicates properly, tracks all changes
  """
  table = app_tables.office_calcs if category == "Office" else app_tables.center_calcs

  # Use .search() to handle potential duplicates
  matching_rows = list(table.search(Item=str(item_name).strip()))

  if not matching_rows:
    print(f"Warning: Item '{item_name}' not found in {category} calcs table")
    return False

  # Update all matching rows (handles duplicates if they exist)
  for row in matching_rows:
    old_status = row['Ordered']  # Save old value for audit
    row['Ordered'] = status
    row['Date_Ordered'] = datetime.now().date() if status else None

    # AUDIT LOG
    log_audit(
      action='UPDATE',
      table_name=f'{category.lower()}_calcs',
      item_name=item_name,
      old_value=f"Ordered: {old_status}",
      new_value=f"Ordered: {status}",
      details=f"Shopping list: Marked as {'ordered' if status else 'not ordered'}"
    )

  if len(matching_rows) > 1:
    print(f"Warning: Found {len(matching_rows)} duplicate entries for '{item_name}'")

  return True

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
          row['Ordered'] = False
          row['Date_Ordered'] = None
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

    writer.writerow(['Date Ordered', 'Item', 'Category', 'Link'])

    for item in history:
      writer.writerow([
        str(item.get('Date', '')),
        item.get('Item', ''),
        item.get('Source', ''),
        item.get('Link', '')
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
  reset_count = 0

  for table in [app_tables.office_calcs, app_tables.center_calcs]:
    for row in table.search(Ordered=True):
      row['Ordered'] = False
      row['Date_Ordered'] = None
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
  """Get MachForm orders with optional status filter"""
  try:
    search_args = {}
    if status_filter and status_filter != "All":
      search_args['status'] = status_filter

    orders = app_tables.machform_orders.search(
      tables.order_by('date_requested', ascending=False),
      **search_args
    )

    result = []
    for order in orders:
      result.append({
        'order_id': order.get_id(),
        'date_requested': order['date_requested'],
        'requester_name': order['requester_name'],
        'location': order['location'],
        'category': order['category'],
        'items_summary': order['items_summary'],
        'total_cost': order['total_cost'],
        'status': order['status']
      })

    print(f"Retrieved {len(result)} orders")
    return result

  except Exception as e:
    print(f"❌ Error getting orders: {e}")
    import traceback
    traceback.print_exc()
    return []


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
  try:
    search_args = {}
    if table_filter and table_filter != "All":
      search_args['table_name'] = table_filter
    
    logs = app_tables.audit_logs.search(
      tables.order_by('timestamp', ascending=False),
      **search_args
    )
    
    result = []
    for log in list(logs)[:limit]:
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