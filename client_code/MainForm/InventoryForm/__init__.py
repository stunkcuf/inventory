from ._anvil_designer import InventoryFormTemplate
from anvil import *
import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

class InventoryForm(InventoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # 1. Setup Delete Listener (communicates with RowTemplate2)
    self.repeating_panel_1.set_event_handler('x-refresh', self.refresh_inventory)

    # 2. Setup Dropdown
    self.drop_down_filter.items = [("All Inventory", "All"), ("Center", "Center"), ("Office", "Office")]
    self.drop_down_filter.selected_value = "All"

    self.refresh_inventory()

  def refresh_inventory(self, **event_args):
    """Calls the high-speed server search"""
    cat = self.drop_down_filter.selected_value
    search_query = self.tb_search.text 
    self.repeating_panel_1.items = anvil.server.call('get_inventory_fast', cat, search_query)

  def drop_down_filter_change(self, **event_args):
    self.refresh_inventory()

  def tb_search_change(self, **event_args):
    self.refresh_inventory()

  def button_add_click(self, **event_args):
    """Add new item using table keys: Item, Category, On_Hand, Minimum_Amt, To_oreder"""
    n_box = TextBox()
    if alert(content=n_box, title="New Item Name:"):
      app_tables.inventory.add_row(
        Item=n_box.text, 
        Category="Office", 
        On_Hand=0, 
        Minimum_Amt=0, 
        To_oreder=0
      )
      self.refresh_inventory()

  def button_update_stock_click(self, **event_args):
    """Updates quantity by searching for exact Item name"""
    n_box = TextBox(placeholder="Item Name (Exact Match)")
    a_box = TextBox(type="number", placeholder="New Total Count")
    c = ColumnPanel()
    c.add_component(Label(text="Item Name:"))
    c.add_component(n_box)
    c.add_component(Label(text="New Quantity:"))
    c.add_component(a_box)

    if alert(content=c, title="Update Stock", buttons=[("Update", True), ("Cancel", False)]):
      name = n_box.text.strip() if n_box.text else ""
      row = app_tables.inventory.get(Item=name)
      if row:
        val = int(a_box.text or 0)
        row['On_Hand'] = val
        # Recalculate 'To Order'
        min_amt = row['Minimum_Amt'] or 0
        row['To_oreder'] = max(0, min_amt - val)
        self.refresh_inventory()
      else:
        alert(f"Item '{name}' not found!")