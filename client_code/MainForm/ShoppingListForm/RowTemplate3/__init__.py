from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # 1. Bind Data
    self.lbl_dept.text = self.item['Source'] + " - " + self.item['Category']
    self.link_item.text = self.item['Item']
    self.link_item.url = self.item['Item_Link']
    self.lbl_price.text = f"${self.item['Price']:.2f}"
    self.lbl_qty.text = self.item['On_Hand']
    self.check_ordered.checked = self.item['Ordered']

    # 2. Visual Cues
    if not self.item['Item_Link']:
      self.link_item.foreground = "black"
      self.link_item.role = None
    else:
      self.link_item.foreground = "blue"

  def check_ordered_change(self, **event_args):
    # 3. Call server with ID and Table Name
    anvil.server.call('mark_as_ordered', 
                      self.item['row_id'], 
                      self.item['table_name'], 
                      self.check_ordered.checked)

    # Optional: Grey out text
    color = "#999" if self.check_ordered.checked else "black"
    if self.item['Item_Link']: color = "blue" # keep links blue if unchecked
    self.link_item.foreground = color