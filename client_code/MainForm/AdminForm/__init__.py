from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class AdminForm(AdminFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def file_loader_1_change(self, file, **event_args):
    """This method is called when a new file is loaded into the FileLoader"""
    if file:
      try:
        # Show loading notification
        with Notification("Importing Excel file... This may take a minute.", 
                          style="info", timeout=None) as n:
          status = anvil.server.call('process_excel_import', file)

        if status:
          Notification(f"Import Successful! Processed {len(status)} sheets.", 
                       style="success", timeout=5).show()
        else:
          Notification("Import failed or no matching sheets found.", 
                       style="warning").show()
      except Exception as e:
        Notification(f"Import error: {str(e)}", style="danger").show()
    else:
      Notification("Please select a file to upload.", style="warning").show()

  def btn_clear_inventory_click(self, **event_args):
    """Optional button to wipe the inventory table if needed"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      app_tables.inventory.delete_all_rows()
      Notification("Inventory cleared.", style="success").show()

  def shopping_list_link_click(self, **event_args):
    """This handles the click event for the Shopping List link"""
    from ..ShoppingListForm import ShoppingListForm

    # Find the main form and switch to shopping list
    main_layout = get_open_form()
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())