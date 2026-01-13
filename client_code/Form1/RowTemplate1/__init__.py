from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    # This initializes the row and fills it with your Data Table info
    self.init_components(**properties)

  def button_delete_click(self, **event_args):
    """The Trash Can Button on the specific Row"""
    product_name = self.item['product_name']

    # confirm() creates a mobile-friendly popup
    if confirm(f"Are you sure you want to permanently delete {product_name}?"):
      anvil.server.call('delete_product_logic', product_name)

      # This tells the main screen to refresh the list
      get_open_form().refresh_inventory()