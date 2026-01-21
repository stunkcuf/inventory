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
  if val is None or val == "" or str(val).strip() == "0": return 0
  if isinstance(val, (int, float)): return val
  clean_val = str(val).replace('$', '').replace(',', '').strip()
  match = re.search(r'(\d+(\.\d+)?)', clean_val)
  return float(match.group(1)) if match else 0

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

def extract_url_from_text(text):
  """Extract URL from text"""
  if not text or not isinstance(text, str):
    return None

  text = str(text).strip()

  # Direct URL check
  if text.startswith('http://') or text.startswith('https://'):
    return text

  # Look for -> URL pattern
  if ' -> ' in text:
    parts = text.split(' -> ')
    if len(parts) >= 2:
      url = parts[-1].strip()
      if url and url.lower() != 'none' and url.startswith('http'):
        return url

  # Look for any http URL in the text
  url_match = re.search(r'(https?://[^\s]+)', text)
  if url_match:
    return url_match.group(1)

  return None

def find_header_row(df):
  """Find the row that contains column headers like 'Item', '$ Amount/each', etc."""
  for i, row in df.iterrows():
    row_str = ' '.join([str(v).lower() for v in row.values if v is not None])
    # Look for key header indicators - be flexible with variations
    if 'item' in row_str and ('amount' in row_str or 'qty' in row_str or 'url' in row_str or 'price' in row_str):
      return i
  return 0

def find_column_by_keywords(columns, *keywords):
  """Find a column that matches any of the given keywords (case-insensitive)"""
  for col in columns:
    col_lower = str(col).lower().strip()
    for keyword in keywords:
      if keyword.lower() in col_lower:
        return col
  return None

def get_excel_column_index(df, column_name):
  """Get the Excel column index (1-based) for a given pandas column name"""
  try:
    return list(df.columns).index(column_name) + 1
  except:
    return None

# --- 2. DATA LOADERS ---
@anvil.server.callable
def get_inventory_fast(category="All", search_query=None):
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")
  return app_tables.inventory.search(tables.order_by("Item", ascending=True), **search_args)

@anvil.server.callable
def get_spending_summary():
  data = app_tables.summary_2025.search()
  results = [(r['Location'], r['Total_Cost']) for r in data]
  return results if results else [("No Data", 0)]

# --- 3. THE "DEEP SCAN" EXCEL IMPORT ---
@anvil.server.callable
def process_excel_import(file):
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

  for s in all_sheets:
    ls = s.lower()
    if "summary" in ls: 
      target_assignments.append((s, "summary_2025"))
    # Look for "Calcs" sheets specifically (not "OrderForm")
    if "calcs" in ls:
      table = "office_calcs" if "office" in ls else "center_calcs"
      target_assignments.append((s, table))
      print(f"Assigning sheet '{s}' to table '{table}' (URLS HERE)")
    # Also check for "master" sheets
    elif "master" in ls:
      table = "center_calcs"  # or you can make this smarter
      target_assignments.append((s, table))
      print(f"Assigning sheet '{s}' to table '{table}'")

  for tbl in ["inventory", "summary_2025", "office_calcs", "center_calcs"]:
    if any(t == tbl for s, t in target_assignments):
      getattr(app_tables, tbl).delete_all_rows()

  for excel_sheet, table_name in target_assignments:
    print(f"\n=== Processing sheet: {excel_sheet} ===")
    ws = wb[excel_sheet]

    # Read sheet without assuming header position
    raw_df = xl.parse(excel_sheet, header=None)

    # Find where the actual header row is
    header_row_idx = find_header_row(raw_df)
    print(f"Found header at row {header_row_idx}")

    # Now read the data starting from that header
    df = xl.parse(excel_sheet, skiprows=header_row_idx).replace({np.nan: None})

    # Clean up column names (remove $ and extra spaces)
    df.columns = [str(col).strip().replace('$', '').strip() for col in df.columns]
    print(f"Columns found: {list(df.columns)}")

    # Intelligently find the URL column (handles different names/positions)
    url_col_name = find_column_by_keywords(df.columns, 'url', 'link', 'hyperlink', 'web', 'source')
    url_col_index = get_excel_column_index(df, url_col_name) if url_col_name else None

    if url_col_name:
      print(f"Found URL column: '{url_col_name}' at Excel column {url_col_index}")
    else:
      print("No URL column header found - will search all columns")

    # Find item column (handles variations)
    item_col_name = find_column_by_keywords(df.columns, 'item', 'product', 'name', 'description')

    # Find price column (handles variations)
    price_col_name = find_column_by_keywords(df.columns, 'amount', 'price', 'cost', 'each')

    for idx, row in df.iterrows():
      raw = dict(row)

      # Get item name using intelligent column detection
      item_name = None
      if item_col_name and item_col_name in raw:
        item_name = str(raw[item_col_name]).strip()
      else:
        # Fallback to checking common variations
        for col in ['Item', 'item', 'Items', 'Product', 'Name']:
          if col in raw and raw[col]:
            item_name = str(raw[col]).strip()
            break

      if not item_name or item_name in ["None", "Item", "nan"] or item_name.endswith(':'):
        continue

      # Skip section headers (usually all caps or end with colon)
      if item_name.isupper() and len(item_name.split()) <= 3:
        continue

      # --- COMPREHENSIVE URL EXTRACTION ---
      excel_row_num = idx + header_row_idx + 2
      extracted_url = None

      # Debug: Check first 5 rows in detail - scan ALL columns to find where URLs are
      if idx < 5:
        print(f"  Checking item: {item_name} (Excel row {excel_row_num})")
        max_col = ws.max_column if ws.max_column else 20
        for test_col in range(1, min(max_col + 1, 15)):
          try:
            test_cell = ws.cell(row=excel_row_num, column=test_col)
            if test_cell.value or (test_cell.hyperlink and test_cell.hyperlink.target):
              cell_val_preview = str(test_cell.value)[:40] if test_cell.value else "empty"
              has_hyperlink = "YES" if (test_cell.hyperlink and test_cell.hyperlink.target) else "no"
              if has_hyperlink == "YES":
                print(f"    Col {test_col}: HYPERLINK -> {test_cell.hyperlink.target}")
              elif test_cell.value:
                print(f"    Col {test_col}: '{cell_val_preview}'")
          except:
            pass

      # PRIORITY 1: Scan columns E through L (5-12) for URLs
      for col_num in range(5, 13):  # E=5 through L=12
        try:
          cell = ws.cell(row=excel_row_num, column=col_num)
          
          # Check Excel hyperlink object
          if cell.hyperlink and cell.hyperlink.target:
            extracted_url = cell.hyperlink.target
            print(f"  -> Found hyperlink in column {col_num}: {extracted_url}")
            break

          # Check HYPERLINK formula
          cell_val = str(cell.value) if cell.value else ""
          if "=HYPERLINK" in cell_val.upper():
            match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
            if match:
              extracted_url = match.group(1)
              print(f"  -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
              break

          # Check for plain URL in cell
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
        # First check the pandas dataframe value
        if url_col_name in raw and raw[url_col_name]:
          url_from_col = extract_url_from_text(str(raw[url_col_name]))
          if url_from_col:
            extracted_url = url_from_col
            print(f"  -> Found URL in '{url_col_name}' column (text): {extracted_url}")
        
        # If not found, check the Excel cell directly for hyperlinks
        if not extracted_url:
          try:
            cell = ws.cell(row=excel_row_num, column=url_col_index)
            
            # Check for Excel hyperlink object
            if cell.hyperlink and cell.hyperlink.target:
              extracted_url = cell.hyperlink.target
              print(f"  -> Found hyperlink in URL column (col {url_col_index}): {extracted_url}")
            
            # Check for HYPERLINK formula
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

      # PRIORITY 3: Scan columns F and G specifically (common URL locations)
      if not extracted_url:
        for col_num in [6, 7]:  # F=6, G=7
          try:
            cell = ws.cell(row=excel_row_num, column=col_num)
            
            # Check Excel hyperlink object
            if cell.hyperlink and cell.hyperlink.target:
              extracted_url = cell.hyperlink.target
              print(f"  -> Found hyperlink in column {col_num}: {extracted_url}")
              break

            # Check HYPERLINK formula
            cell_val = str(cell.value) if cell.value else ""
            if "=HYPERLINK" in cell_val.upper():
              match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
              if match:
                extracted_url = match.group(1)
                print(f"  -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                break

            # Check for plain URL in cell
            if cell_val and 'http' in cell_val.lower():
              cell_url = extract_url_from_text(cell_val)
              if cell_url:
                extracted_url = cell_url
                print(f"  -> Found URL text in column {col_num}: {extracted_url}")
                break
          except:
            continue
      
      # PRIORITY 4: Last resort - scan all remaining columns
      if not extracted_url:
        max_col = ws.max_column if ws.max_column else 20
        for col_num in range(1, min(max_col + 1, 50)):
          if 5 <= col_num <= 12:  # Already checked these
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

      # Clean up item name - remove category prefix if present
      if item_name.startswith('[') and ']' in item_name:
        item_name = item_name[item_name.index(']')+1:].strip()

      if extracted_url:
        print(f"[{excel_sheet}] {item_name} -> {extracted_url}")
      
      # Save to appropriate table
      if table_name == "inventory":
        cat = "Office" if "office" in excel_sheet.lower() else "Center"
        app_tables.inventory.add_row(
          Item=item_name, Category=cat, 
          On_Hand=int(clean_num(raw.get('On Hand', 0))), 
          Minimum_Amt=int(clean_num(raw.get('Minimum Amt', 0)))
        )
      elif "calcs" in table_name:
        # Use intelligent price column detection
        price = 0
        if price_col_name and price_col_name in raw:
          price = clean_num(raw[price_col_name])
        else:
          # Fallback: try multiple possible column names
          for price_col in ['Amount/each', 'Amount', 'Price', 'Cost', 'Unit Price', 'Each']:
            if price_col in raw:
              price = clean_num(raw[price_col])
              if price > 0:
                break
        
        getattr(app_tables, table_name).add_row(
          Item=item_name, Item_Link=extracted_url, Price=price, Ordered=False
        )
      elif table_name == "summary_2025":
        app_tables.summary_2025.add_row(
          Location=raw.get('Location') or item_name,
          Total_Cost=clean_num(raw.get('Total_Cost') or 0)
        )

  return [s for s, t in target_assignments]

# --- 4. SHOPPING & HISTORY ---
@anvil.server.callable
def get_shopping_list():
  off_m = {r['Item']: dict(r) for r in app_tables.office_calcs.search()}
  cen_m = {r['Item']: dict(r) for r in app_tables.center_calcs.search()}
  items = []
  for inv in app_tables.inventory.search():
    item_nm = inv['Item']
    cat = inv.get('Category', 'Office')
    master = off_m if cat == "Office" else cen_m
    info = master.get(item_nm, {})
    oh, ma = (inv.get('On_Hand') or 0), (inv.get('Minimum_Amt') or 0)
    if oh < ma and not info.get('Ordered', False):
      items.append({
        'Item': item_nm, 'On_Hand': oh, 'Minimum_Amt': ma,
        'Category': cat, 'Source': cat, 'Price': info.get('Price', 0),
        'Item_Link': info.get('Item_Link'), 'Ordered': False
      })
  return sorted(items, key=lambda x: (x['Category'], x['Item']))

@anvil.server.callable
def mark_as_ordered(item_name, category, status):
  table = app_tables.office_calcs if category == "Office" else app_tables.center_calcs
  row = table.get(Item=item_name)
  if row:
    row['Ordered'] = status
    row['Date_Ordered'] = datetime.now().date() if status else None

@anvil.server.callable
def get_ordered_history():
  history = []
  for table in [app_tables.office_calcs, app_tables.center_calcs]:
    source = "Office" if table == app_tables.office_calcs else "Center"
    for r in table.search(Ordered=True):
      history.append({
        'Item': r['Item'], 'Source': source,
        'Date': r['Date_Ordered'], 'Link': r['Item_Link']
      })
  return sorted(history, key=lambda x: str(x['Date']), reverse=True)