import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import io
import csv

@anvil.server.callable
def sync_data_files():
  # 1. Clear the inventory table to start fresh
  app_tables.inventory.delete_all_rows()
  total_added = 0

  # 2. Get all rows from your 'Files' table
  all_file_rows = app_tables.files.search()

  for row in all_file_rows:
    csv_media = row['file'] # Assumes column name is 'file'
    if csv_media:
      file_name_text = csv_media.name or ""

      # Determine Category based on filename
      category = ""
      if "Center" in file_name_text: category = "Center"
      elif "Office" in file_name_text: category = "Office"

      if category:
        csv_bytes = csv_media.get_bytes()
        csv_str = csv_bytes.decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_str))

        for csv_row in reader:
          item_name = csv_row.get('Item', '').strip()
          if not item_name or item_name.endswith(':'): continue

            # Extract numbers for stock and minimums
          on_hand = 0
          min_amt = 0
          for k, v in csv_row.items():
            k_low = k.lower()
            if 'hand' in k_low: 
              try: on_hand = int(float(v)) if v else 0
              except: on_hand = 0
            elif 'min' in k_low: 
              try: min_amt = int(float(v)) if v else 0
              except: min_amt = 0

                # Map CSV Description/Notes to Table 'Notes' column
          desc = csv_row.get('Description') or csv_row.get('Notes') or ""

          app_tables.inventory.add_row(
            Item=item_name,
            On_Hand=on_hand,
            Minimum_Amt=min_amt,
            To_Order=max(0, min_amt - on_hand),
            Category=category,
            Notes=desc.strip()
          )
          total_added += 1
  return total_added