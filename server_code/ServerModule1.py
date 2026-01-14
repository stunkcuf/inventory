import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def add_new_product(name, description, stock):
  stock_level = int(stock) if stock else 0
  app_tables.inventory.add_row(
    product_name=name,
    description=description,
    stock=stock_level
  )

@anvil.server.callable
def update_stock_logic(name, amount):
  row = app_tables.inventory.get(product_name=name)
  if row:
    # Handles both adding (5) and subtracting (-5)
    row['stock'] += int(amount)
    return row['stock']
  else:
    return None

@anvil.server.callable
def delete_product_logic(name):
  row = app_tables.inventory.get(product_name=name)
  if row:
    row.delete()