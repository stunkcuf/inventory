import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def add_new_product(name, description, stock):
  """Adds a brand new item to the database"""
  # Convert stock to integer to ensure math works later
  stock_level = int(stock) if stock else 0

  app_tables.inventory.add_row(
    product_name=name,
    description=description,
    stock=stock_level
  )
  return f"Successfully added {name}!"

@anvil.server.callable
def update_stock_logic(name, amount):
  """Adjusts stock level. 'amount' can be positive (e.g., 1 or 10) or negative (e.g., -1 or -10)"""
  row = app_tables.inventory.get(product_name=name)
  if row:
    # We use += so that a negative number subtracts and a positive number adds
    row['stock'] += int(amount)
    return f"Stock updated for {name}."
  else:
    return "Error: Product not found."

@anvil.server.callable
def delete_product_logic(name):
  """Permanently removes a product from the database"""
  row = app_tables.inventory.get(product_name=name)
  if row:
    row.delete()
    return f"{name} has been removed."