from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
  
    # 1. Bind Data to UI Elements
    # self.item comes from the 'items' list returned by get_shopping_list
    self.lbl_dept.text = f"{self.item['Source']} - {self.item['Category']}"
    self.link_item.text = self.item['Item']
    self.link_item.url = self.item['Item_Link']
    self.lbl_price.text = f"${self.item['Price']:.2f}"
    self.lbl_qty.text = str(self.item['On_Hand'])
    self.check_ordered.checked = self.item['Ordered']
    
    # 2. Initial Visual Cues (Formatting links)
    if not self.item['Item_Link']:
      self.link_item.foreground = "black"
      self.link_item.role = None
    else:
      self.link_item.foreground = "blue"

    # 3. Apply grey-out if already checked on load
    if self.check_ordered.checked:
      self.link_item.foreground = "#999"

  def check_ordered_change(self, **event_args):
    """This method is called when the checkbox is toggled"""
    try:
      # Capture the current state of the checkbox
      new_status = self.check_ordered.checked

      # Update the local 'item' dictionary so the state 'sticks' 
      # while the user is on this page.
      self.item['Ordered'] = new_status

      # Visual cue: Grey out the text if checked, restore if unchecked
      if new_status:
        self.link_item.foreground = "#999"
      else:
        self.link_item.foreground = "blue" if self.item['Item_Link'] else "black"

      # CALL THE SERVER: This must match the name in your ServerModule
      result = anvil.server.call(
        'check_ordered', 
        self.item['Item'], 
        self.item['Category'], 
        new_status
      )

      # Verify if the database actually found the row to update
      if not result:
        alert(f"Warning: Could not find '{self.item['Item']}' in the database tables.")

    except Exception as e:
      # This catches errors like 'No server function registered'
      print(f"Error calling server: {e}")
      alert(f"Communication Error: {e}")