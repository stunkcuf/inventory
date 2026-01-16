from ._anvil_designer import RowTemplate2Template
from anvil import *
import anvil.server
from anvil.tables import app_tables

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    self.init_components(**properties)

  def btn_plus_click(self, **event_args):
    """Increments stock"""
    self.item['On_Hand'] += 1
    # Auto-update 'To Order'
    min_amt = self.item['Minimum_Amt'] or 0
    self.item['To_oreder'] = max(0, min_amt - self.item['On_Hand'])
    self.refresh_data_bindings()

  def btn_minus_click(self, **event_args):
    """Decrements stock"""
    if self.item['On_Hand'] > 0:
      self.item['On_Hand'] -= 1
      min_amt = self.item['Minimum_Amt'] or 0
      self.item['To_oreder'] = max(0, min_amt - self.item['On_Hand'])
      self.refresh_data_bindings()

  def btn_delete_click(self, **event_args):
    """Deletes row and notifies parent to refresh"""
    if confirm(f"Delete {self.item['Item']}?"):
      self.item.delete()
      self.parent.raise_event('x-refresh')