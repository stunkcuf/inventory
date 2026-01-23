from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Calculate quantity to buy
    on_hand = self.item.get('On_Hand', 0)
    minimum = self.item.get('Minimum_Amt', 0)
    qty_to_buy = max(0, minimum - on_hand)

    # Bind data to UI
    self.lbl_dept.text = f"{self.item['Source']} - {self.item['Category']}"
    self.link_item.text = self.item['Item']
    self.link_item.url = self.item['Item_Link']
    self.lbl_price.text = f"${self.item['Price']:.2f}"
    self.lbl_qty.text = str(qty_to_buy)

    # MOBILE OPTIMIZATION: Add stock info to item name for smaller screens
    self.lbl_stock_info.text = f"Need: {qty_to_buy} (Have: {on_hand}/{minimum})"

    self.check_ordered.checked = self.item['Ordered']

    # Format links
    if not self.item['Item_Link']:
      self.link_item.foreground = "black"
      self.link_item.role = None
    else:
      self.link_item.foreground = "blue"

    # Apply grey-out if already checked
    if self.check_ordered.checked:
      self.link_item.foreground = "#999"
      self.lbl_dept.foreground = "#999"
      self.lbl_price.foreground = "#999"
      self.lbl_qty.foreground = "#999"
      self.lbl_stock_info.foreground = "#999"

  def check_ordered_change(self, **event_args):
    """Checkbox toggled"""
    try:
      new_status = self.check_ordered.checked
      self.item['Ordered'] = new_status

      # Visual feedback
      color = "#999" if new_status else ("blue" if self.item['Item_Link'] else "black")
      self.link_item.foreground = color

      dept_color = "#999" if new_status else "black"
      self.lbl_dept.foreground = dept_color
      self.lbl_price.foreground = dept_color
      self.lbl_qty.foreground = dept_color
      self.lbl_stock_info.foreground = dept_color

      # Update server
      result = anvil.server.call('check_ordered', self.item['Item'], self.item['Category'], new_status)

      if not result:
        alert(f"Warning: Could not find '{self.item['Item']}' in the database tables.")

    except Exception as e:
      print(f"Error calling server: {e}")
      alert(f"Communication Error: {e}")