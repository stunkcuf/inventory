from ._anvil_designer import RowTemplate2Template
from anvil import *
import anvil.server

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    # Data bindings handle the display; 
    # logic for red text is in the Design tab bindings.

  def button_minus_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def button_plus_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def button_delete_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass
