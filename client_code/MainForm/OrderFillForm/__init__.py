from ._anvil_designer import OrderFillFormTemplate
from anvil import *
import anvil.server

class OrderFillForm(OrderFillFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)