from ._anvil_designer import InventoryFormTemplate
from anvil import *
import anvil.users
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

class InventoryForm(InventoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.repeating_panel_1.set_event_handler('x-refresh', self.refresh_inventory)

    self.drop_down_filter.items = [("All Inventory", "All"), ("Center", "Center"), ("Office", "Office")]
    self.load_subcategories()
    self.refresh_inventory()

  def load_subcategories(self):
    category = self.drop_down_filter.selected_value or "All"
    subcats = anvil.server.call('get_subcategories', category)

    if hasattr(self, 'drop_down_subcategory'):
      self.drop_down_subcategory.items = [("All Subcategories", "All")] + [(s, s) for s in subcats]
      self.drop_down_subcategory.selected_value = "All"

  def refresh_inventory(self, **event_args):
    cat = self.drop_down_filter.selected_value
    search = self.tb_search.text

    subcat = None
    if hasattr(self, 'drop_down_subcategory'):
      subcat = self.drop_down_subcategory.selected_value

    self.repeating_panel_1.items = anvil.server.call('get_inventory_fast', cat, search, subcat)

  def drop_down_filter_change(self, **event_args):
    self.load_subcategories()
    self.refresh_inventory()

  def drop_down_subcategory_change(self, **event_args):
    self.refresh_inventory()

  def tb_search_change(self, **event_args):
    self.refresh_inventory()

  def button_add_click(self, **event_args):
    n_box, oh_box, ma_box = TextBox(), TextBox(type="number"), TextBox(type="number")
    cat_dd = DropDown(items=["Office", "Center"])
    subcat_box = TextBox(placeholder="Optional subcategory")

    layout = LinearPanel()
    for label, comp in [("Item:", n_box), ("Category:", cat_dd), ("Subcategory:", subcat_box), ("On Hand:", oh_box), ("Min Amt:", ma_box)]:
      layout.add_component(Label(text=label))
      layout.add_component(comp)

    if alert(content=layout, title="Add New Product", buttons=[("Save", True), ("Cancel", False)], large=True):
      if n_box.text:
        oh, ma = int(oh_box.text or 0), int(ma_box.text or 0)
        app_tables.inventory.add_row(
          Item=n_box.text, 
          Category=cat_dd.selected_value,
          Subcategory=subcat_box.text or None,
          On_Hand=oh, 
          Minimum_Amt=ma, 
          To_Order=max(0, ma-oh)
        )
        self.refresh_inventory()
        self.load_subcategories()

  def button_update_stock_click(self, **event_args):
    all_items = app_tables.inventory.search(tables.order_by("Item"))
    item_sel = DropDown(items=[(r['Item'], r) for r in all_items])
    oh_box, ma_box = TextBox(type="number"), TextBox(type="number")
    cat_dd = DropDown(items=["Office", "Center"])
    subcat_box = TextBox(placeholder="Optional subcategory")

    def selector_change(**event_args):
      row = item_sel.selected_value
      if row:
        oh_box.text = row['On_Hand']
        ma_box.text = row['Minimum_Amt']
        cat_dd.selected_value = row['Category']
        subcat_box.text = row.get('Subcategory') or ""

    item_sel.set_event_handler('change', selector_change)
    if item_sel.items: 
      selector_change()

    layout = LinearPanel()
    for label, comp in [("Select:", item_sel), ("Category:", cat_dd), ("Subcategory:", subcat_box), ("On Hand:", oh_box), ("Min Amt:", ma_box)]:
      layout.add_component(Label(text=label))
      layout.add_component(comp)

    if alert(content=layout, title="Update Stock", buttons=[("Save", True), ("Cancel", False)], large=True):
      row = item_sel.selected_value
      if row:
        oh, ma = int(oh_box.text or 0), int(ma_box.text or 0)
        row.update(
          On_Hand=oh, 
          Minimum_Amt=ma, 
          Category=cat_dd.selected_value,
          Subcategory=subcat_box.text or None,
          To_Order=max(0, ma-oh)
        )
        self.refresh_inventory()
        self.load_subcategories()