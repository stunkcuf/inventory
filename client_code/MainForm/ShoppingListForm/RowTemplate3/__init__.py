from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    # Map data to labels
    self.label_1.text = self.item['Item']
    self.label_2.text = self.item['On_Hand']
    self.label_3.text = self.item['Minimum_Amt']
    self.label_4.text = self.item['To_Order']
    self.check_box_1.checked = self.item['Ordered']

  def check_box_1_change(self, **event_args):
    anvil.server.call('mark_as_ordered', self.item, self.check_box_1.checked)