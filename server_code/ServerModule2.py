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
  """Converts various formats to float, returns 0 on failure"""
  if val is None or val == "" or str(val).strip() == "0":
    return 0
  if isinstance(val, (int, float)):
    return val
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
  if not text or not isinstance(text, str):
    return None
  text = str(text).strip()
  if text.startswith('http://') or text.startswith('https://'):
    url = text
  elif ' -> ' in text:
    parts = text.split(' -> ')
    if len(parts) >= 2:
      url = parts[-1].strip()
      if not (url and url.lower() != 'none' and url.startswith('http')):
        return None
    else:
      return None
  else:
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
      url = url_match.group(1)
    else:
      return None
  if url:
    url = url.rstrip('.,;)\'"')
    if '.' not in url.replace('http://', '').replace('https://', ''):
      return None
    if len(url) <= 8:
      return None
    return url
  return None

def find_header_row(df):
  for i, row in df.iterrows():
    row_str = ' '.join([str(v).lower() for v in row.values if v is not None])
    if 'item' in row_str and ('amount' in row_str or 'qty' in row_str or 'url' in row_str or 'price' in row_str):
      return i
  return 0

def find_column_by_keywords(columns, *keywords):
  for col in columns:
    col_lower = str(col).lower().strip()
    for keyword in keywords:
      if keyword.lower() in col_lower:
        return col
  return None

def get_excel_column_index(df, column_name):
  try:
    return list(df.columns).index(column_name) + 1
  except:
    return None

# --- 2. DATA LOADERS ---
@anvil.server.callable
def get_inventory_fast(category="All", search_query=None, subcategory="All"):
  rows = app_tables.inventory.search()
  if category and category != "All":
    rows = [r for r in rows if r['Category'] == category]
  if subcategory and subcategory != "All":
    rows = [r for r in rows if r.get('Subcategory') == subcategory]
  if search_query and search_query.strip():
    search_query = search_query.lower()
    rows = [r for r in rows if search_query in (r['Item'] or "").lower()]
  return rows

@anvil.server.callable
def get_subcategories(category="All"):
  search_args = {}
  if category and category != "All":
    search_args['Category'] = category
  items = app_tables.inventory.search(**search_args)
  subcategories = set(item.get('Subcategory') for item in items if item.get('Subcategory'))
  return sorted(list(subcategories))

@anvil.server.callable
def get_spending_summary_by_table(table_name='summary_2025'):
  print(f"=== get_spending_summary_by_table called for {table_name} ===")
  valid_tables = [
    'summary_2025', 'inventory_summary_total', 'inventory_summary_office',
    'inventory_summary_internal', 'inventory_summary_center'
  ]
  if table_name not in valid_tables:
    print(f"Invalid table name: {table_name}")
    return [("Invalid table", 0, 0, 0)]
  try:
    table = getattr(app_tables, table_name)
    data = list(table.search())
    print(f"Found {len(data)} rows in {table_name}")
    if not data:
      return [("No Data", 0, 0, 0)]
    print(f"Sample row keys: {list(data[0].keys())}")
    location_totals = {}  # location → [gl, po, other]
    for r in data:
      location = (
        r.get('Location') or r.get('Location Name') or
        r.get('location_name') or r.get('Location #') or "Unknown"
      ).strip()
      if not location or location == "Unknown":
        continue
      gl = clean_num(r.get('GL_Amt') or r.get('gl_amt') or 0)
      po = clean_num(r.get('PO_Amt') or r.get('po_amt') or 0)
      other = clean_num(r.get('Other_Amt') or r.get('other_amt') or 0)
      if location not in location_totals:
        location_totals[location] = [0.0, 0.0, 0.0]
      location_totals[location][0] += gl
      location_totals[location][1] += po
      location_totals[location][2] += other
    results = []
    for loc, vals in location_totals.items():
      gl_sum, po_sum, other_sum = vals
      total = gl_sum + po_sum + other_sum
      if total > 0:
        results.append((loc, gl_sum, po_sum, other_sum))
    results.sort(key=lambda x: x[0])
    print(f"Returning {len(results)} locations with breakdown")
    for r in results[:5]:
      print(f"  {r[0]:<20} GL:${r[1]:>9,.0f} PO:${r[2]:>9,.0f} Other:${r[3]:>9,.0f}")
    return results if results else [("No Data", 0, 0, 0)]
  except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    return [("Error", 0, 0, 0)]

@anvil.server.callable
def get_available_summary_tables():
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
  import_stats = {
    'inventory': 0, 'office_calcs': 0, 'center_calcs': 0,
    'summary_2025': 0, 'inventory_summary_total': 0,
    'inventory_summary_office': 0, 'inventory_summary_internal': 0,
    'inventory_summary_center': 0,
    'errors': [], 'warnings': []
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
    if latest_off: target_assignments.append((latest_off, "inventory"))
    if latest_cen: target_assignments.append((latest_cen, "inventory"))
    for s in all_sheets:
      ls = s.lower()
      if s == "2025-Summary":
        target_assignments.append((s, "summary_2025"))
        print(f"Assigning sheet '{s}' to table 'summary_2025'")
      elif "total" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_total"))
      elif "office" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_office"))
      elif "internal" in ls and "summary" in ls:
        target_assignments.append((s, "inventory_summary_internal"))
      elif ("center" in ls or "centre" in ls) and "summary" in ls:
        target_assignments.append((s, "inventory_summary_center"))
      elif "calcs" in ls:
        table = "office_calcs" if "office" in ls else "center_calcs"
        target_assignments.append((s, table))
      elif "master" in ls:
        target_assignments.append((s, "center_calcs"))
    for tbl in ["inventory", "summary_2025", "office_calcs", "center_calcs",
                "inventory_summary_total", "inventory_summary_office",
                "inventory_summary_internal", "inventory_summary_center"]:
      if any(t == tbl for s, t in target_assignments):
        getattr(app_tables, tbl).delete_all_rows()
        print(f"Cleared table: {tbl}")
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
            print(f" Found subcategory: {current_subcategory}")
            continue
          if item_name.isupper() and len(item_name.split()) <= 3:
            current_subcategory = item_name
            print(f" Found subcategory: {current_subcategory}")
            continue
          excel_row_num = idx + header_row_idx + 2
          extracted_url = None
          # PRIORITY 1: Scan columns E through L (5-12) for URLs
          for col_num in range(5, 13):
            try:
              cell = ws.cell(row=excel_row_num, column=col_num)
              if cell.hyperlink and cell.hyperlink.target:
                extracted_url = cell.hyperlink.target
                print(f" -> Found hyperlink in column {col_num}: {extracted_url}")
                break
              cell_val = str(cell.value) if cell.value else ""
              if "=HYPERLINK" in cell_val.upper():
                match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                if match:
                  extracted_url = match.group(1)
                  print(f" -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                  break
              if cell_val and 'http' in cell_val.lower():
                cell_url = extract_url_from_text(cell_val)
                if cell_url:
                  extracted_url = cell_url
                  print(f" -> Found URL text in column {col_num}: {extracted_url}")
                  break
            except:
              continue
              # PRIORITY 2: If URL column exists
          if not extracted_url and url_col_name and url_col_index:
            if url_col_name in raw and raw[url_col_name]:
              url_from_col = extract_url_from_text(str(raw[url_col_name]))
              if url_from_col:
                extracted_url = url_from_col
                print(f" -> Found URL in '{url_col_name}' column (text): {extracted_url}")
            if not extracted_url:
              try:
                cell = ws.cell(row=excel_row_num, column=url_col_index)
                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f" -> Found hyperlink in URL column: {extracted_url}")
                elif cell.value:
                  cell_val = str(cell.value)
                  if "=HYPERLINK" in cell_val.upper():
                    match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                    if match:
                      extracted_url = match.group(1)
                      print(f" -> Found HYPERLINK formula in URL column: {extracted_url}")
              except:
                pass
                # PRIORITY 3: URL in item name
          if not extracted_url:
            url_from_text = extract_url_from_text(item_name)
            if url_from_text:
              extracted_url = url_from_text
              if ' -> ' in item_name:
                item_name = item_name.split(' -> ')[0].strip()
              print(f" -> Found URL in item name: {extracted_url}")
              # PRIORITY 4: Columns F and G
          if not extracted_url:
            for col_num in [6, 7]:
              try:
                cell = ws.cell(row=excel_row_num, column=col_num)
                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f" -> Found hyperlink in column {col_num}: {extracted_url}")
                  break
                cell_val = str(cell.value) if cell.value else ""
                if "=HYPERLINK" in cell_val.upper():
                  match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                  if match:
                    extracted_url = match.group(1)
                    print(f" -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                    break
                if cell_val and 'http' in cell_val.lower():
                  cell_url = extract_url_from_text(cell_val)
                  if cell_url:
                    extracted_url = cell_url
                    print(f" -> Found URL text in column {col_num}: {extracted_url}")
                    break
              except:
                continue
                # PRIORITY 5: Scan all remaining columns
          if not extracted_url:
            max_col = ws.max_column if ws.max_column else 20
            for col_num in range(1, min(max_col + 1, 50)):
              if 5 <= col_num <= 12:
                continue
              try:
                cell = ws.cell(row=excel_row_num, column=col_num)
                if cell.hyperlink and cell.hyperlink.target:
                  extracted_url = cell.hyperlink.target
                  print(f" -> Found hyperlink in column {col_num}: {extracted_url}")
                  break
                cell_val = str(cell.value) if cell.value else ""
                if "=HYPERLINK" in cell_val.upper():
                  match = re.search(r'["\'](http[s]?://.*?)["\']', cell_val)
                  if match:
                    extracted_url = match.group(1)
                    print(f" -> Found HYPERLINK formula in column {col_num}: {extracted_url}")
                    break
                if cell_val and 'http' in cell_val.lower():
                  cell_url = extract_url_from_text(cell_val)
                  if cell_url:
                    extracted_url = cell_url
                    print(f" -> Found URL text in column {col_num}: {extracted_url}")
                    break
              except:
                continue
          if item_name.startswith('[') and ']' in item_name:
            item_name = item_name[item_name.index(']')+1:].strip()
          if extracted_url:
            print(f"[{excel_sheet}] {item_name} -> {extracted_url}")
            # Save logic
          if table_name == "inventory":
            cat = "Office" if "office" in excel_sheet.lower() else "Center"
            on_hand = int(clean_num(raw.get('On Hand', 0)))
            min_amt = int(clean_num(raw.get('Minimum Amt', 0)))
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
            if not extracted_url:
              import_stats['warnings'].append(f"{item_name}: No URL found")
            if price == 0:
              import_stats['warnings'].append(f"{item_name}: No price found")
            getattr(app_tables, table_name).add_row(
              Item=item_name, Item_Link=extracted_url, Price=price, Ordered=False
            )
            import_stats[table_name] += 1
          elif "summary" in table_name:
            location = None
            gl_amt = 0.0
            po_amt = 0.0
            other_amt = 0.0
            total_amt = 0.0
            for loc_col in ['Location', 'Location Name', 'Location #', 'Loc', 'Site']:
              if loc_col in raw and raw[loc_col]:
                location = str(raw[loc_col]).strip()
                break
            if not location:
              continue
            cols_lower = {k.lower().strip(): k for k in raw}
            # GL
            for k in ['gl amt', 'gl_amt', 'gl amount', 'general ledger', 'gl']:
              if k in cols_lower:
                gl_amt = clean_num(raw[cols_lower[k]])
                break
                # PO
            for k in ['po orders', 'po amt', 'po_amount', 'purchase order', 'po', 'po order amt']:
              if k in cols_lower:
                po_amt = clean_num(raw[cols_lower[k]])
                break
                # Other
            for k in ['other', 'other amt', 'other_amount', 'misc', 'other cost', 'misc amt']:
              if k in cols_lower:
                other_amt = clean_num(raw[cols_lower[k]])
                break
                # Total fallback
            for k in ['total amt', 'total_amt', 'total cost', 'total_cost', 'total', 'amt']:
              if k in cols_lower:
                total_amt = clean_num(raw[cols_lower[k]])
                break
            if gl_amt == 0 and po_amt == 0 and other_amt == 0 and total_amt > 0:
              other_amt = total_amt
              print(f"Fallback to Other: ${total_amt:,.2f} for {location}")
            row_total = gl_amt + po_amt + other_amt
            if row_total > 0:
              getattr(app_tables, table_name).add_row(
                Location=location,
                GL_Amt=gl_amt,
                PO_Amt=po_amt,
                Other_Amt=other_amt,
                Total_Cost=row_total
              )
              import_stats[table_name] += 1
              print(f"Imported summary: {location} | GL:${gl_amt:,.2f} PO:${po_amt:,.2f} Other:${other_amt:,.2f}")
      except Exception as sheet_error:
        error_msg = f"Error processing sheet '{excel_sheet}': {str(sheet_error)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        import_stats['errors'].append(error_msg)
        continue
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
    total_items = sum(import_stats.values()) - len(import_stats['errors']) - len(import_stats['warnings'])
    return {
      'success': True,
      'sheets_processed': [s for s, t in target_assignments],
      'stats': import_stats,
      'total_items': total_items
    }
  except Exception as e:
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
  off_m = {r['Item']: r for r in app_tables.office_calcs.search()}
  cen_m = {r['Item']: r for r in app_tables.center_calcs.search()}
  print(f"Office calcs items: {len(off_m)}")
  print(f"Center calcs items: {len(cen_m)}")
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
  return sorted(items, key=lambda x: (x.get('Ordered', False), x['Category'], x['Item']))

# ... (keep all your other functions like check_ordered, get_ordered_history, etc. unchanged)