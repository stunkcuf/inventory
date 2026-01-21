from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server
import anvil.js

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_list()

  def refresh_list(self):
    # This calls the consolidated function from ServerModule2
    items = anvil.server.call('get_shopping_list')
    self.repeating_panel_1.items = items

    # Check if label_empty exists before trying to use it
    if hasattr(self, 'label_empty'):
      self.label_empty.visible = len(items) == 0
      
  def btn_print_click(self, **event_args):
    import anvil.js
    anvil.js.window.print()

  def print_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass
