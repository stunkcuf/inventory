from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

  @handle("button_delete", "click")
  def button_delete_click(self, **event_args):
    """This runs when the trash can next to an item is clicked"""
    product_name = self.item['product_name']

    # 1. Ask the user to be sure
    if confirm(f"Permanently delete {product_name}?"):
      # 2. Call the server to remove from database
      anvil.server.call('delete_product_logic', product_name)

      # 3. Tell the main form to refresh the list so it disappears
      get_open_form().refresh_inventory()