from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class AdminForm(AdminFormTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def file_loader_1_change(self, file, **event_args):
    """This method is called when a new file is loaded into the FileLoader"""
    if file:
      # --- LINE 13 FIX: CHANGED TO process_excel_import ---
      status = anvil.server.call('process_excel_import', file)

      if status:
        Notification(f"Import Successful: {status}", style="success").show()
      else:
        Notification("Import failed or no matching sheets found.", style="warning").show()
    else:
      Notification("Please select a file to upload.").show()

  def btn_clear_inventory_click(self, **event_args):
    """Optional button to wipe the inventory table if needed"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      app_tables.inventory.delete_all_rows()
      Notification("Inventory cleared.").show()
      def shopping_list_link_click(self, **event_args):
        """This stops the error and lets you navigate to the shopping list"""
    from ..ShoppingListForm import ShoppingListForm
    get_open_form().content_panel.clear()
    get_open_form().content_panel.add_component(ShoppingListForm())
    def shopping_list_link_click(self, **event_args):
      """This handles the click event for the Shopping List link"""
    from ..ShoppingListForm import ShoppingListForm
    self.content_panel.clear()
    self.content_panel.add_component(ShoppingListForm())

  def shopping_list_link_click(self, **event_args):
    """This handles the click event for the Shopping List link"""
    # 1. Import the form we want to show
    from ..ShoppingListForm import ShoppingListForm
  
    # 2. Find the main form (usually where the content_panel lives)
    main_layout = get_open_form()
  
    # 3. Clear the main form's content area and add the new form
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())
