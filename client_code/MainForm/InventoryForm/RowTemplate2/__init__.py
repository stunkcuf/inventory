from ._anvil_designer import RowTemplate2Template
from anvil import *
import anvil.server

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def btn_plus_click(self, **event_args):
    """Increment stock and update To_Order"""
    self.item['On_Hand'] += 1
    ma = self.item['Minimum_Amt'] or 0
    self.item['To_Order'] = max(0, ma - self.item['On_Hand'])
    self.refresh_data_bindings()

  def btn_minus_click(self, **event_args):
    """Decrement stock and update To_Order"""
    if self.item['On_Hand'] > 0:
      self.item['On_Hand'] -= 1
      ma = self.item['Minimum_Amt'] or 0
      self.item['To_Order'] = max(0, ma - self.item['On_Hand'])
      self.refresh_data_bindings()

  def btn_delete_click(self, **event_args):
    """Delete this row from the database"""
    if confirm(f"Delete {self.item['Item']}?"):
      self.item.delete()
      self.parent.raise_event('x-refresh')