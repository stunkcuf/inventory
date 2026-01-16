from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_list()

  def refresh_list(self):
    self.repeating_panel_1.items = anvil.server.call('get_shopping_list')

  def print_button_click(self, **event_args):
    import anvil.js
    anvil.js.window.print()

  def btn_reset_click(self, **event_args):
    if confirm("Reset all 'Ordered' checkboxes?"):
      anvil.server.call('reset_ordered_status')
      self.refresh_list()