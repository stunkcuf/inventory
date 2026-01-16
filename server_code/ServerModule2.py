import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.tables as tables

@anvil.server.callable
def get_inventory_fast(category="All", search_query=None):
  """Returns a live search object for fast, lazy-loading display."""
  search_args = {}

  if category != "All":
    search_args['Category'] = category

  if search_query and search_query.strip() != "":
    search_args['Item'] = q.ilike(f"%{search_query}%")

    # This allows Anvil to load rows only as the user scrolls
  return app_tables.inventory.search(
    tables.order_by("Item", ascending=True),
    **search_args
  )