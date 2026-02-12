from ._anvil_designer import OrderHistoryRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.js

class OrderHistoryRowTemplate(OrderHistoryRowTemplateTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Display shopping list order data (NOT MachForm data)
    self.label_date.text = str(self.item.get('Date', 'No date'))
    self.label_item.text = self.item.get('Item', 'Unknown')
    self.label_category.text = self.item.get('Source', 'Unknown')

    # Show/hide link
    link = self.item.get('Link')
    if link:
      self.link_view.url = link
      self.link_view.visible = True
    else:
      self.link_view.visible = False

  def link_view_click(self, **event_args):
    """Open item link in new tab"""
    if self.item.get('Link'):
      anvil.js.window.open(self.item['Link'], '_blank')