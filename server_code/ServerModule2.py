import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.tables as tables
import pandas as pd
import numpy as np
import io                  # <--- This is built-in, no install needed!
from datetime import datetime

@anvil.server.callable
def get_inventory_fast(category="All", search_query=None):
  """Handles filtering and sorting on the server for speed."""

  # 1. Base query with sorting
  # Note: Using your Capitalized column keys
  if category == "All":
    items = app_tables.inventory.search(tables.order_by("Item"))
  else:
    items = app_tables.inventory.search(tables.order_by("Item"), Category=category)

    # 2. Add search query if provided
  if search_query and search_query.strip() != "":
    # We re-run the search with the ilike operator for the search term
    if category == "All":
      items = app_tables.inventory.search(
        tables.order_by("Item"),
        Item=q.ilike(f"%{search_query}%")
      )
    else:
      items = app_tables.inventory.search(
        tables.order_by("Item"),
        Item=q.ilike(f"%{search_query}%"),
        Category=category
      )

  return items