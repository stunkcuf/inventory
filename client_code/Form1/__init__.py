from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set up the visual components
    self.init_components(**properties)
    # Load the full list on startup
    self.refresh_inventory()

  def refresh_inventory(self, search_query=None):
    """Updates the list with optional search filtering and sorting"""
    if search_query and search_query != "":
      # 'q.ilike' searches for text regardless of capital letters
      items = app_tables.inventory.search(
        product_name=q.ilike(f"%{search_query}%")
      )
    else:
      # If search is empty, show everything
      items = app_tables.inventory.search()

    # Sort items A-Z by name before displaying
    self.repeating_panel_1.items = sorted(items, key=lambda x: x['product_name'])

  def text_box_search_change(self, **event_args):
    """This function runs every time you type a character in the search bar"""
    self.refresh_inventory(self.text_box_search.text)

  @handle("button_1", "click")
  def button_1_click(self, **event_args):
    """The 'Update Stock' Popup"""
    product_names = [row['product_name'] for row in app_tables.inventory.search()]
    product_dropdown = DropDown(items=sorted(product_names))
    amount_input = TextBox(type="number", placeholder="Enter amount (e.g., -5)")

    content = ColumnPanel()
    content.add_component(Label(text="Select Product:"))
    content.add_component(product_dropdown)
    content.add_component(Label(text="Adjustment:"))
    content.add_component(amount_input)

    # 'large=True' makes the buttons much easier to press on a phone screen
    if alert(content=content, title="Update Stock", large=True, buttons=[("Confirm", True), ("Cancel", False)]):
      if amount_input.text:
        res = anvil.server.call('update_stock_logic', product_dropdown.selected_value, amount_input.text)
        self.refresh_inventory()
        Notification(res, style="info").show()

  @handle("button_2", "click")
  def button_2_click(self, **event_args):
    """The 'Add Product' Popup"""
    n_box = TextBox(placeholder="Product Name")
    d_box = TextBox(placeholder="Description")
    s_box = TextBox(type="number", placeholder="Starting Stock")

    content = ColumnPanel()
    content.add_component(n_box)
    content.add_component(d_box)
    content.add_component(s_box)

    if alert(content=content, title="New Product", large=True, buttons=[("Add to List", True), ("Back", False)]):
      if n_box.text:
        res = anvil.server.call('add_new_product', n_box.text, d_box.text, s_box.text)
        self.refresh_inventory()
        Notification(res, style="success").show()

  @handle("text_box_1", "pressed_enter")
  def text_box_1_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    pass
