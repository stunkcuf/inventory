from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.users
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Calculate quantity to buy
    on_hand = self.item.get('On_Hand', 0)
    minimum = self.item.get('Minimum_Amt', 0)
    qty_to_buy = max(0, minimum - on_hand)

    # Bind Data to UI Elements
    self.lbl_dept.text = f"{self.item['Source']} - {self.item['Category']}"
    self.link_item.text = self.item['Item']
    self.link_item.url = self.item['Item_Link']
    self.lbl_price.text = f"${self.item['Price']:.2f}"
    self.lbl_qty.text = str(qty_to_buy)
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

  def check_ordered_change(self, **event_args):
    """This method is called when the checkbox is toggled"""
    previous_status = self.item['Ordered']
    new_status = self.check_ordered.checked
    self.check_ordered.enabled = False
    try:
      result = anvil.server.call(
        'check_ordered', self.item['Item'], self.item['Category'], new_status
      )
    except Exception as e:
      self.check_ordered.checked = previous_status
      alert(f"Could not save order status: {e}")
      return
    finally:
      self.check_ordered.enabled = True

    if not result:
      self.check_ordered.checked = previous_status
      alert(f"Could not find '{self.item['Item']}' in the ordering table.")
      return

    self.item['Ordered'] = new_status
    if new_status:
      self.link_item.foreground = "#999"
    else:
      self.link_item.foreground = "blue" if self.item['Item_Link'] else "black"
    from anvil import get_open_form
    for component in get_open_form().content_panel.get_components():
      if hasattr(component, 'update_summary'):
        component.update_summary()
