import anvil.server
from anvil.tables import app_tables

@anvil.server.callable
def update_stock_logic(name, amount):
  try:
    adjustment = int(amount)
  except:
    return "Error: Invalid number."

  row = app_tables.inventory.get(product_name=name)
  if row:
    row['stock'] += adjustment
    return f"Success! {name} updated to {row['stock']}."
  return "Error: Product not found."

@anvil.server.callable
def add_new_product(name, desc, stock):
  # Prevent duplicate names
  existing = app_tables.inventory.get(product_name=name)
  if existing:
    return f"Error: '{name}' already exists."

  app_tables.inventory.add_row(
    product_name=name,
    description=desc,
    stock=int(stock) if stock else 0
  )
  return f"Success: {name} added."

@anvil.server.callable
def delete_product_logic(name):
  row = app_tables.inventory.get(product_name=name)
  if row:
    row.delete()
    return "Product deleted."
  return "Error: Product not found."