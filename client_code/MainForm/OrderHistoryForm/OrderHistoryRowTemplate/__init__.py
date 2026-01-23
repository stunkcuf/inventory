from ._anvil_designer import OrderHistoryRowTemplateTemplate
from anvil import *
import anvil.js

class OrderHistoryRowTemplate(OrderHistoryRowTemplateTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Bind data
    self.lbl_date.text = str(self.item.get('Date', 'No date'))
    self.lbl_item.text = self.item.get('Item', 'Unknown')
    self.lbl_category.text = self.item.get('Source', 'Unknown')

    # Format link
    link = self.item.get('Link')
    if link:
      self.link_url.text = "🔗 View"
      self.link_url.url = link
      self.link_url.visible = True
    else:
      self.link_url.visible = False

  def link_url_click(self, **event_args):
    """Open link in new tab"""
    if self.item.get('Link'):
      anvil.js.window.open(self.item['Link'], '_blank')