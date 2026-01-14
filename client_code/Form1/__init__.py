from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.tables import app_tables

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set up the components as defined in the Design view
    self.init_components(**properties)

    # 1. Setup the filter dropdown
    self.drop_down_filter.items = [
      ("All Inventory", "All"), 
      ("Center", "Center"), 
      ("Office", "Office")
    ]
    self.drop_down_filter.selected_value = "All"

    # 2. Initial load of data
    self.refresh_inventory()

  def refresh_inventory(self, search_query=None):
    """Loads and filters the data grid based on current selection and search text"""
    cat = self.drop_down_filter.selected_value

    # Base filter: Category
    if cat == "All":
      items = app_tables.inventory.search()
    else:
      items = app_tables.inventory.search(Category=cat)

    # Secondary filter: Search Bar (Case-insensitive)
    if search_query and search_query.strip() != "":
      s = search_query.lower()
      items = [r for r in items if s in r['Item'].lower()]

    # Sort and display
    self.repeating_panel_1.items = sorted(list(items), key=lambda x: x['Item'])

  def drop_down_filter_change(self, **event_args):
    """Triggered by the DropDown 'change' event in Designer"""
    # Always pass the current search text so the filters work together
    self.refresh_inventory(self.text_box_search.text)

  def text_box_search_change(self, **event_args):
    """Triggered by the TextBox 'change' event in Designer"""
    # This runs every time you type a letter
    self.refresh_inventory(self.text_box_search.text)

  @handle("button_sync_files", "click")
  def button_sync_files_click(self, **event_args):
    """Reloads data from the CSV files in the 'Files' table"""
    if confirm("Reload data from CSV files?"):
      with Notification("Processing CSV files..."):
        count = anvil.server.call('sync_data_files')
      self.refresh_inventory()
      alert(f"Sync Complete! {count} items imported.")

  def button_add_click(self, **event_args):
    """Popup to manually add a new product"""
    n_box = TextBox()
    c_box = DropDown(items=["Office", "Center"])
    m_box = TextBox(type="number")

    c = ColumnPanel()
    c.add_component(Label(text="Name:"))
    c.add_component(n_box)
    c.add_component(Label(text="Category:"))
    c.add_component(c_box)
    c.add_component(Label(text="Min Stock:"))
    c.add_component(m_box)

    if alert(content=c, title="New Product", buttons=[("Save", True), ("Cancel", False)]):
      m_val = int(m_box.text) if m_box.text else 0
      app_tables.inventory.add_row(
        Item=n_box.text, 
        Category=c_box.selected_value, 
        On_Hand=0, 
        Minimum_Amt=m_val, 
        To_Order=m_val
      )
      self.refresh_inventory()

  def button_update_stock_click(self, **event_args):
    """Searches for an item and updates its quantity"""
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
        # Recalculate To Order amount
        min_amt = row['Minimum_Amt'] or 0
        row['To_Order'] = max(0, min_amt - val)

        self.refresh_inventory()
        Notification(f"Updated {name} to {val}").show()
      else:
        alert(f"Item '{name}' not found. Check spelling and capitalization!")

  @handle("text_box_search", "pressed_enter")
  def text_box_search_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    pass
