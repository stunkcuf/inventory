from ._anvil_designer import AdminFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..MainForm.helpers import show_success, show_error, show_warning, log_error

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
          show_error(f"Import failed: {error_msg}", timeout=10)

      except Exception as e:
        log_error("file_loader_1_change", e)
        show_error(f"Import error: {str(e)}")
    else:
      show_warning("Please select a file to upload.")

  def btn_clear_inventory_click(self, **event_args):
    """Clear all inventory data"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      app_tables.inventory.delete_all_rows()
      show_success("Inventory cleared.")

  def shopping_list_link_click(self, **event_args):
    """Navigate to Shopping List"""
    from ..ShoppingListForm import ShoppingListForm
    main_layout = get_open_form()
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())

  def link_order_history_click(self, **event_args):
    """Navigate to Order History"""
    print("AdminForm: Order History link clicked!")
    try:
      main_form = get_open_form()
      print(f"Got main form: {main_form}")
      main_form.link_order_history_click()
      print("Called main form navigation")
    except Exception as e:
      log_error("link_order_history_click", e)

  @handle("link_audit_logs", "click")
  def link_audit_logs_click(self, **event_args):
    """Navigate to Audit Logs - Admin Only"""
    try:
      from ..AuditLogForm import AuditLogForm
      main_layout = get_open_form()
      main_layout.content_panel.clear()
      main_layout.content_panel.add_component(AuditLogForm())
      print("Navigated to Audit Logs")
    except Exception as e:
      log_error("link_audit_logs_click", e)
      show_error(f"Error loading audit logs: {str(e)}")