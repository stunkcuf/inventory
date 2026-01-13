from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.tables import app_tables

class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_inventory()

  def refresh_inventory(self):
    """Updates the Data Grid display"""
    self.repeating_panel_1.items = app_tables.inventory.search()

  @handle("button_1", "click")
  def button_1_click(self, **event_args):
    """BUTTON: Update Stock Levels"""
    product_names = [row['product_name'] for row in app_tables.inventory.search() if row['product_name']]
    if not product_names:
      Notification("No products to update.").show()
      return

    product_dropdown = DropDown(items=sorted(product_names))
    amount_input = TextBox(type="number", placeholder="e.g. 5 or -5")

    content = ColumnPanel()
    content.add_component(Label(text="Select Product:"))
    content.add_component(product_dropdown)
    content.add_component(Label(text="Change Amount (Negative to subtract):"))
    content.add_component(amount_input)

    if alert(content=content, title="Adjust Stock", buttons=[("Update", True), ("Cancel", False)]):
      if amount_input.text:
        res = anvil.server.call('update_stock_logic', product_dropdown.selected_value, amount_input.text)
        self.refresh_inventory()
        Notification(res).show()

  @handle("button_2", "click")
  def button_2_click(self, **event_args):
    """BUTTON: Add New Product to List"""
    name_box = TextBox(placeholder="Product Name")
    desc_box = TextBox(placeholder="Description")
    stock_box = TextBox(type="number", placeholder="Initial Stock")

    content = ColumnPanel()
    content.add_component(Label(text="New Product Name:"))
    content.add_component(name_box)
    content.add_component(Label(text="Description:"))
    content.add_component(desc_box)
    content.add_component(Label(text="Stock:"))
    content.add_component(stock_box)

    if alert(content=content, title="Add New Product", buttons=[("Add", True), ("Cancel", False)]):
      if name_box.text:
        res = anvil.server.call('add_new_product', name_box.text, desc_box.text, stock_box.text)
        self.refresh_inventory()
        Notification(res).show()