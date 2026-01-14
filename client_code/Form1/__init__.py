from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_inventory()

  def refresh_inventory(self, search_query=None):
    if search_query:
      items = app_tables.inventory.search(product_name=q.ilike(f"%{search_query}%"))
    else:
      items = app_tables.inventory.search()
    self.repeating_panel_1.items = sorted(items, key=lambda x: x['product_name'])

  def text_box_search_change(self, **event_args):
    self.refresh_inventory(self.text_box_search.text)

  def button_add_click(self, **event_args):
    """Opens popup to add a brand new item"""
    n_box = TextBox(placeholder="Product Name")
    d_box = TextBox(placeholder="Description")
    s_box = TextBox(type="number", placeholder="Initial Stock", text="0")

    content = ColumnPanel()
    content.add_component(n_box)
    content.add_component(d_box)
    content.add_component(s_box)

    if alert(content=content, title="Add New Product", large=True, buttons=[("Save", True), ("Cancel", False)]):
      if n_box.text:
        anvil.server.call('add_new_product', n_box.text, d_box.text, s_box.text)
        self.refresh_inventory()
      else:
        Notification("Name is required").show()

  def button_update_stock_click(self, **event_args):
    """Opens popup to manually update stock for an existing item"""
    n_box = TextBox(placeholder="Exact Product Name")
    a_box = TextBox(type="number", placeholder="Amount to add (e.g. 10 or -10)")

    content = ColumnPanel()
    content.add_component(n_box)
    content.add_component(a_box)

    if alert(content=content, title="Manual Stock Update", buttons=[("Update", True), ("Cancel", False)]):
      if n_box.text and a_box.text:
        result = anvil.server.call('update_stock_logic', n_box.text, a_box.text)
        if result is not None:
          self.refresh_inventory()
        else:
          alert(f"Product '{n_box.text}' not found!")