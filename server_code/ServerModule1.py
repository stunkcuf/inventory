import anvil.server
from anvil.tables import app_tables

@anvil.server.callable
def update_stock_logic(name, amount):
  try:
    adjustment = int(amount)
  except (ValueError, TypeError):
    return "Error: Please enter a valid whole number."

  row = app_tables.inventory.get(product_name=name)
  if row:
    new_total = row['stock'] + adjustment
    if new_total < 0:
      return f"Error: Cannot reduce stock below zero. (Current: {row['stock']})"
    row['stock'] = new_total
    return f"Success! {name} stock is now {new_total}."
  return "Error: Product not found."

@anvil.server.callable
def add_new_product(name, desc, stock):
  existing = app_tables.inventory.get(product_name=name)
  if existing:
    return f"Error: '{name}' already exists."

  app_tables.inventory.add_row(
    product_name=name,
    description=desc,
    stock=int(stock) if stock else 0
  )
  return f"Success: {name} added to inventory."

@anvil.server.callable
def delete_product_logic(name):
  row = app_tables.inventory.get(product_name=name)
  if row:
    row.delete()
    return f"Success: {name} removed."
  return "Error: Product not found."