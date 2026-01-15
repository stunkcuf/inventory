from ._anvil_designer import RowTemplate1Template
from anvil import *

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.update_ui()

  def update_ui(self):
    row = self.item

    # 1. Item Name
    if hasattr(self, 'label_name'):
      self.label_name.text = row['Item']

    # 2. Description (Pulling specifically from 'Notes' column)
    if hasattr(self, 'label_desc'):
      db_notes = row['Notes']
      self.label_desc.text = db_notes if db_notes else "-"

    # 3. Stock Level
    if hasattr(self, 'label_stock'):
      self.label_stock.text = str(row['On_Hand'])

    # 4. Order Logic & Visual Feedback
    qty_to_order = row['To_Order'] or 0
    if hasattr(self, 'label_to_order'):
      self.label_to_order.text = str(qty_to_order) if qty_to_order > 0 else "-"
      self.label_to_order.foreground = "red" if qty_to_order > 0 else "gray"

    # 5. Apply the Responsive CSS Role based on Stock Level
    # This triggers the '.anvil-role-low-stock-row' style in your theme.css
    if qty_to_order > 0:
      self.role = 'low-stock-row'
    else:
      # If you aren't using the 'elevated-card' role on the RepeatingPanel, 
      # you can change this to None or 'default'
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