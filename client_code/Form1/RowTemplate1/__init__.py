from ._anvil_designer import RowTemplate2Template # Change 1 to 2
from anvil import *
import anvil.server

class RowTemplate2(RowTemplate2Template): # Change 1 to 2
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run for every single row