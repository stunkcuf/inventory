from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server
import anvil.js

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_list()

  def refresh_list(self):
    # 1. First, tell the server to clean up any restocked items
    resets = anvil.server.call('sync_inventory_status')
  
    # 2. Now get the clean list to show the user
    items = anvil.server.call('get_shopping_list')
    self.repeating_panel_1.items = items
  
    if hasattr(self, 'label_empty'):
      self.label_empty.visible = len(items) == 0
      
  def btn_print_click(self, **event_args):
    import anvil.js
    anvil.js.window.print()

  def print_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass
