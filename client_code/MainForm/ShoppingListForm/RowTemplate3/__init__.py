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
    try:
      new_status = self.check_ordered.checked
      self.item['Ordered'] = new_status

      # Visual cue: Grey out if checked
      if new_status:
        self.link_item.foreground = "#999"
      else:
        self.link_item.foreground = "blue" if self.item['Item_Link'] else "black"

      # Update server
      result = anvil.server.call(
        'check_ordered', 
        self.item['Item'], 
        self.item['Category'], 
        new_status
      )

      if not result:
        alert(f"Warning: Could not find '{self.item['Item']}' in the database tables.")
      else:
        # Update parent form's summary
        parent_form = self.parent.parent.parent
        if hasattr(parent_form, 'update_summary'):
          parent_form.update_summary()

    except Exception as e:
      print(f"Error calling server: {e}")
      alert(f"Communication Error: {e}")