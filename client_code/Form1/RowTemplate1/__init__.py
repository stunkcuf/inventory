from ._anvil_designer import RowTemplate1Template
from anvil import *
import anvil.server

class RowTemplate1(RowTemplate1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.update_ui()

  def update_ui(self):
    stock = self.item['stock'] or 0
    self.label_name.text = self.item['product_name']
    self.label_desc.text = self.item['description']
    self.label_stock.text = str(stock)
    self.label_stock.foreground = "#ff0000" if stock < 5 else ""

  def button_plus_click(self, **event_args):
    self.item['stock'] = anvil.server.call('update_stock_logic', self.item['product_name'], 1)
    self.update_ui()

  def button_minus_click(self, **event_args):
    if self.item['stock'] > 0:
      self.item['stock'] = anvil.server.call('update_stock_logic', self.item['product_name'], -1)
      self.update_ui()

  @handle("button_delete", "click")
  def button_delete_click(self, **event_args):
    if confirm(f"Delete {self.item['product_name']}?"):
      anvil.server.call('delete_product_logic', self.item['product_name'])
      get_open_form().refresh_inventory()