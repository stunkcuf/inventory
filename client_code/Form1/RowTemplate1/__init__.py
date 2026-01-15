from ._anvil_designer import RowTemplate1Template
from anvil import *

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Initialize the UI with data from the row
    self.update_ui()

  def update_ui(self):
    """Refreshes the labels and visual style based on the current item data."""
    row = self.item

    # 1. Map Item Name
    if hasattr(self, 'label_name'):
      self.label_name.text = row['Item']

    # 2. Map Description (Notes)
    if hasattr(self, 'label_desc'):
      # Display a dash if notes are empty
      db_notes = row['Notes']
      self.label_desc.text = db_notes if db_notes else "-"

    # 3. Map Stock Level (On Hand)
    if hasattr(self, 'label_stock'):
      self.label_stock.text = str(row['On_Hand'])

    # 4. Map Order Logic
    # Calculate how many need to be ordered
    qty_to_order = row['To_Order'] or 0

    if hasattr(self, 'label_to_order'):
      # Show a dash if nothing is needed, otherwise show the red number
      self.label_to_order.text = str(qty_to_order) if qty_to_order > 0 else "-"
      self.label_to_order.foreground = "red" if qty_to_order > 0 else "gray"

    # 5. Apply the Visual Role (The "CSS Trigger")
    # This switches the background based on the 'low-stock-row' CSS class
    if qty_to_order > 0:
      self.role = 'low-stock-row'
    else:
      # Use 'elevated-card' for the standard white card look
      self.role = 'elevated-card'

  def button_plus_click(self, **event_args):
    """Increments stock and recalculates order amount."""
    self.item['On_Hand'] += 1
    # Ensure To_Order doesn't go below zero
    self.item['To_Order'] = max(0, (self.item['Minimum_Amt'] or 0) - self.item['On_Hand'])
    self.update_ui()

  def button_minus_click(self, **event_args):
    """Decrements stock and recalculates order amount."""
    if self.item['On_Hand'] > 0:
      self.item['On_Hand'] -= 1
      self.item['To_Order'] = max(0, (self.item['Minimum_Amt'] or 0) - self.item['On_Hand'])
      self.update_ui()

  def button_delete_click(self, **event_args):
    """Deletes the item from the Data Table after confirmation."""
    if confirm(f"Are you sure you want to delete {self.item['Item']}?"):
      self.item.delete()
      self.remove_from_parent()