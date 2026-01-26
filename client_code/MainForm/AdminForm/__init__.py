from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class AdminForm(AdminFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def file_loader_1_change(self, file, **event_args):
    """Import Excel file with detailed feedback"""
    if file:
      try:
        with Notification("Importing Excel file... This may take a minute.", 
                          style="info", timeout=None) as n:
          result = anvil.server.call('process_excel_import', file)

        if result.get('success'):
          stats = result['stats']

          msg = f"✅ Import Successful!\n\n"
          msg += f"📊 Imported {result['total_items']} total items:\n"
          msg += f"  • Inventory: {stats['inventory']}\n"
          msg += f"  • Office Calcs: {stats['office_calcs']}\n"
          msg += f"  • Center Calcs: {stats['center_calcs']}\n"
          msg += f"  • Summary: {stats['summary_2025']}\n"

          if stats['warnings']:
            msg += f"\n⚠️ {len(stats['warnings'])} warnings (check console)"
            for warning in stats['warnings'][:5]:
              print(f"WARNING: {warning}")

          if stats['errors']:
            msg += f"\n❌ {len(stats['errors'])} errors occurred"
            for error in stats['errors']:
              print(f"ERROR: {error}")

          alert(msg, title="Import Complete")
        else:
          error_msg = result.get('error', 'Unknown error')
          Notification(f"Import failed: {error_msg}", style="danger", timeout=10).show()

      except Exception as e:
        Notification(f"Import error: {str(e)}", style="danger").show()
        print(f"Import exception: {e}")
    else:
      Notification("Please select a file to upload.", style="warning").show()

  def btn_clear_inventory_click(self, **event_args):
    """Clear all inventory data"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      app_tables.inventory.delete_all_rows()
      Notification("Inventory cleared.", style="success").show()

  def shopping_list_link_click(self, **event_args):
    """Navigate to Shopping List"""
    from ..ShoppingListForm import ShoppingListForm
    main_layout = get_open_form()
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())

  def link_order_history_click(self, **event_args):
    """Navigate to Order History"""
    print("AdminForm: Order History link clicked!")  # DEBUG
    try:
      main_form = get_open_form()
      print(f"Got main form: {main_form}")  # DEBUG
      main_form.link_order_history_click()
      print("Called main form navigation")  # DEBUG
    except Exception as e:
      print(f"Navigation error: {e}")  # DEBUG
      import traceback
      traceback.print_exc()