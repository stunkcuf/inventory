from ._anvil_designer import RowTemplate1Template
from anvil import *

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.update_ui()

  def update_ui(self):
    row = self.item

    # Text Mappings
    self.label_name.text = row['Item']
    self.label_desc.text = row['Notes'] if row['Notes'] else "-"
    self.label_stock.text = str(row['On_Hand'])

    # Stock Calculation
    qty = row['To_Order'] or 0
    self.label_to_order.text = str(qty) if qty > 0 else "-"
    self.label_to_order.foreground = "red" if qty > 0 else "gray"

    # CSS Role Trigger: applies the 'low-stock-row' class from theme.css
    if qty > 0:
      self.role = 'low-stock-row'
    else:
      self.role = 'elevated-card'

  def button_plus_click(self, **event_args):
    self.item['On_Hand'] += 1
    self.item['To_Order'] = max(0, (self.item['Minimum_Amt'] or 0) - self.item['On_Hand'])
    self.update_ui()

  def button_minus_click(self, **event_args):
    if self.item['On_Hand'] > 0:
      self.item['On_Hand'] -= 1
      self.item['To_Order'] = max(0, (self.item['Minimum_Amt'] or 0) - self.item['On_Hand'])
      self.update_ui()

  def button_delete_click(self, **event_args):
    if confirm(f"Delete {self.item['Item']}?"):
      self.item.delete()
      self.remove_from_parent()