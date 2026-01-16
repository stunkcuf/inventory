from ._anvil_designer import RowTemplate2Template
from anvil import *

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    self.init_components(**properties)

  def btn_plus_click(self, **event_args):
    self.item['On_Hand'] += 1
    ma = self.item['Minimum_Amt'] or 0
    self.item['To_Order'] = max(0, ma - self.item['On_Hand'])
    self.refresh_data_bindings()

  def btn_minus_click(self, **event_args):
    if self.item['On_Hand'] > 0:
      self.item['On_Hand'] -= 1
      ma = self.item['Minimum_Amt'] or 0
      self.item['To_Order'] = max(0, ma - self.item['On_Hand'])
      self.refresh_data_bindings()

  def btn_delete_click(self, **event_args):
    if confirm(f"Delete {self.item['Item']}?"):
      self.item.delete()
      self.parent.raise_event('x-refresh')