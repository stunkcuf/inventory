from ._anvil_designer import InventoryFormTemplate
from anvil import *
import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

class InventoryForm(InventoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Setup the filter dropdown
    self.drop_down_filter.items = [
      ("All Inventory", "All"), 
      ("Center", "Center"), 
      ("Office", "Office")
    ]
    self.drop_down_filter.selected_value = "All"

    self.refresh_inventory()

  def refresh_inventory(self, **event_args):
    """Calls the server to get data. Fast and no SuspensionErrors."""
    cat = self.drop_down_filter.selected_value
    search_query = self.tb_search.text 

    # We call the server-side function we just created
    self.repeating_panel_1.items = anvil.server.call('get_inventory_fast', cat, search_query)

  @handle("drop_down_filter", "change")
  def drop_down_filter_change(self, **event_args):
    self.refresh_inventory()

  def tb_search_change(self, **event_args):
    self.refresh_inventory()

  def button_add_click(self, **event_args):
    """Add a new item manually"""
    n_box = TextBox()
    if alert(content=n_box, title="New Item Name:"):
      app_tables.inventory.add_row(
        Item=n_box.text, 
        On_Hand=0, 
        Minimum_Amt=0, 
        Category="Office"
      )
      self.refresh_inventory()

  def button_update_stock_click(self, **event_args):
    """Updates quantity and recalculates To_Order"""
    n_box = TextBox(placeholder="Item Name (Exact Match)")
    a_box = TextBox(type="number", placeholder="New Total Count")

    c = ColumnPanel()
    c.add_component(Label(text="Search Item Name:"))
    c.add_component(n_box)
    c.add_component(Label(text="Set New Quantity On Hand:"))
    c.add_component(a_box)

    if alert(content=c, title="Update Stock", buttons=[("Update", True), ("Cancel", False)]):
      name = n_box.text.strip() if n_box.text else ""
      row = app_tables.inventory.get(Item=name)
      if row:
        val = int(a_box.text) if a_box.text else 0
        row['On_Hand'] = val

        # Auto-recalculate To_Order (using your table's specific spelling)
        min_amt = row['Minimum_Amt'] or 0
        row['To_oreder'] = max(0, min_amt - val)

        self.refresh_inventory()
        Notification(f"Updated {name} to {val}").show()
      else:
        alert(f"Item '{name}' not found!")

  @handle("tb_search", "pressed_enter")
  def tb_search_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    pass
