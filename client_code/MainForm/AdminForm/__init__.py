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
    """
    IMPROVED: Better user feedback with detailed import results
    WHY: Shows exactly what was imported and any issues
    """
    if file:
      try:
        with Notification("Importing Excel file... This may take a minute.", 
                          style="info", timeout=None) as n:
          result = anvil.server.call('process_excel_import', file)

        if result.get('success'):
          stats = result['stats']

          # Build success message
          msg = f"✅ Import Successful!\n\n"
          msg += f"📊 Imported {result['total_items']} total items:\n"
          msg += f"  • Inventory: {stats['inventory']}\n"
          msg += f"  • Office Calcs: {stats['office_calcs']}\n"
          msg += f"  • Center Calcs: {stats['center_calcs']}\n"
          msg += f"  • Summary: {stats['summary_2025']}\n"

          # Show warnings if any
          if stats['warnings']:
            msg += f"\n⚠️ {len(stats['warnings'])} warnings (check console)"
            for warning in stats['warnings'][:5]:  # Show first 5
              print(f"WARNING: {warning}")

          # Show errors if any
          if stats['errors']:
            msg += f"\n❌ {len(stats['errors'])} errors occurred"
            for error in stats['errors']:
              print(f"ERROR: {error}")

          alert(msg, title="Import Complete")

        else:
          # Import failed
          error_msg = result.get('error', 'Unknown error')
          Notification(f"Import failed: {error_msg}", style="danger", timeout=10).show()

      except Exception as e:
        Notification(f"Import error: {str(e)}", style="danger").show()
        print(f"Import exception: {e}")
    else:
      Notification("Please select a file to upload.", style="warning").show()

  def btn_clear_inventory_click(self, **event_args):
    """UNCHANGED - Your original code works perfectly"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      app_tables.inventory.delete_all_rows()
      Notification("Inventory cleared.", style="success").show()

  def shopping_list_link_click(self, **event_args):
    """UNCHANGED - Your original code works perfectly"""
    from ..ShoppingListForm import ShoppingListForm
    main_layout = get_open_form()
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())