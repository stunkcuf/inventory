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
    """Updates the list with filtering and A-Z sorting"""
    if search_query:
      # This performs a 'fuzzy' search (case-insensitive)
      items = app_tables.inventory.search(
        product_name=q.ilike(f"%{search_query}%")
      )
    else:
      items = app_tables.inventory.search()

    # Sorts the items so they appear alphabetically
    self.repeating_panel_1.items = sorted(items, key=lambda x: x['product_name'])

  def text_box_search_change(self, **event_args):
    """This triggers as you type each letter"""
    self.refresh_inventory(self.text_box_search.text)

  @handle("text_box_search", "pressed_enter")
  def text_box_search_pressed_enter(self, **event_args):
    """This triggers when you hit 'Enter' or 'Search' on mobile"""
    self.refresh_inventory(self.text_box_search.text)

  def button_1_click(self, **event_args):
    """Update Stock Popup"""
    product_names = [row['product_name'] for row in app_tables.inventory.search()]
    product_dropdown = DropDown(items=sorted(product_names))
    amount_input = TextBox(type="number", placeholder="e.g. 5")

    content = ColumnPanel()
    content.add_component(Label(text="Select Product:"))
    content.add_component(product_dropdown)
    content.add_component(amount_input)

    if alert(content=content, title="Update Stock", large=True):
      if amount_input.text:
        res = anvil.server.call('update_stock_logic', product_dropdown.selected_value, amount_input.text)
        self.refresh_inventory()
        Notification(res).show()

  def button_2_click(self, **event_args):
    """Add Product Popup"""
    n_box = TextBox(placeholder="Name")
    d_box = TextBox(placeholder="Description")
    s_box = TextBox(type="number", placeholder="Stock")

    content = ColumnPanel()
    content.add_component(n_box)
    content.add_component(d_box)
    content.add_component(s_box)

    if alert(content=content, title="New Product", large=True):
      if n_box.text:
        res = anvil.server.call('add_new_product', n_box.text, d_box.text, s_box.text)
        self.refresh_inventory()
        Notification(res).show()