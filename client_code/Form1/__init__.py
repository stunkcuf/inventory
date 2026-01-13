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

  # BUTTON 1: ADJUST STOCK
  def button_1_click(self, **event_args):
    product_names = [row['product_name'] for row in app_tables.inventory.search() if row['product_name']]
    product_names.sort()

    product_dropdown = DropDown(items=product_names)
    amount_input = TextBox(placeholder="e.g. 5 or -5", type="number")

    content = ColumnPanel()
    content.add_component(Label(text="Select Product:"))
    content.add_component(product_dropdown)
    content.add_component(Label(text="Adjustment Amount:"))
    content.add_component(amount_input)

    if alert(content=content, title="Adjust Stock", buttons=[("Update", True), ("Cancel", False)]):
      if amount_input.text is not None:
        res = anvil.server.call('update_stock_logic', product_dropdown.selected_value, amount_input.text)
        self.refresh_inventory()
        Notification(res).show()

  # BUTTON 2: ADD NEW PRODUCT
  def button_2_click(self, **event_args):
    name_box = TextBox(placeholder="New Product Name")
    desc_box = TextBox(placeholder="Description")
    stock_box = TextBox(placeholder="Starting Stock", type="number")

    content = ColumnPanel()
    content.add_component(Label(text="Enter Details:"))
    content.add_component(name_box)
    content.add_component(desc_box)
    content.add_component(stock_box)

    if alert(content=content, title="Add New Product", buttons=[("Save", True), ("Cancel", False)]):
      if name_box.text:
        res = anvil.server.call('add_new_product', name_box.text, desc_box.text, stock_box.text)
        self.refresh_inventory()
        Notification(res).show()
      else:
        Notification("Error: Name required.").show()