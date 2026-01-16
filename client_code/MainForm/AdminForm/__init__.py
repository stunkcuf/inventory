from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.server
from ..ShoppingListForm import ShoppingListForm 

class AdminForm(AdminFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def shopping_list_link_click(self, **event_args):
    # This reaches out to the MainForm to swap the view
    parent = get_open_form()
    parent.content_panel.clear()
    parent.content_panel.add_component(ShoppingListForm())

  def file_loader_1_change(self, file, **event_args):
    with Notification("Updating Database..."):
      anvil.server.call('process_excel_import', file)
    alert("Import Successful!")