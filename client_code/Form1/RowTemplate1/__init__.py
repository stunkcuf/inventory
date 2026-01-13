from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.update_ui()

  def update_ui(self):
    """Updates the stock label text and color"""
    # Use 0 if the database value is empty
    val = self.item['stock'] if self.item['stock'] is not None else 0

    # This matches the name 'label_stock' you set in Step 1
    self.label_stock.text = str(val)

    # Mobile-friendly low stock warning
    if val < 5:
      self.label_stock.foreground = "#ff0000"
      self.label_stock.bold = True
    else:
      self.label_stock.foreground = ""
      self.label_stock.bold = False

  def button_plus_click(self, **event_args):
    """Triggered by the plus button event"""
    anvil.server.call('update_stock_logic', self.item['product_name'], 1)
    self.item['stock'] += 1
    self.update_ui()

  def button_minus_click(self, **event_args):
    """Triggered by the minus button event"""
    if self.item['stock'] > 0:
      anvil.server.call('update_stock_logic', self.item['product_name'], -1)
      self.item['stock'] -= 1
      self.update_ui()
    else:
      Notification("Stock is already 0").show()