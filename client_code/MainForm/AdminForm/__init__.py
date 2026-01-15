from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.server

class AdminForm(AdminFormTemplate):
  def file_loader_1_change(self, file, **event_args):
    # Upload file to server
    status = anvil.server.call('import_master_inventory', file)
    alert(status)