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
      loading_notification = None
      try:
        # Show loading notification that won't auto-close
        loading_notification = Notification(
          "📥 Importing Excel file... This may take 1-2 minutes for large files. Please wait...", 
          style="info", 
          timeout=None
        )
        loading_notification.show()

        # Call server - Anvil handles timeout automatically
        result = anvil.server.call('process_excel_import', file)

        # Hide loading notification BEFORE showing results
        if loading_notification:
          loading_notification.hide()
          loading_notification = None

        # Show results
        if result.get('success'):
          stats = result['stats']
          msg = f"✅ Import Successful!\n\n"
          msg += f"📊 Imported {result['total_items']} total items:\n\n"
          msg += f"  • Inventory: {stats['inventory']}\n"
          msg += f"  • Office Calcs: {stats['office_calcs']}\n"
          msg += f"  • Center Calcs: {stats['center_calcs']}\n"
          msg += f"  • Summary 2025: {stats['summary_2025']}\n"
          msg += f"  • Summary Office: {stats['inventory_summary_office']}\n"
          msg += f"  • Summary Center: {stats['inventory_summary_center']}\n"
          msg += f"  • Summary Internal: {stats['inventory_summary_internal']}\n"

          if stats['warnings']:
            msg += f"\n⚠️ {len(stats['warnings'])} warnings (check console)"
            for warning in stats['warnings'][:5]:
              print(f"WARNING: {warning}")

          if stats['errors']:
            msg += f"\n❌ {len(stats['errors'])} errors occurred"
            for error in stats['errors']:
              print(f"ERROR: {error}")

          alert(msg, title="Import Complete", large=True)

        else:
          error_msg = result.get('error', 'Unknown error')
          alert(f"❌ Import failed: {error_msg}", title="Import Failed")

      except anvil.server.TimeoutError:
        # Handle timeout specifically
        if loading_notification:
          loading_notification.hide()
        alert(
          "⏱️ Import timed out.\n\n"
          "The data may still be importing in the background.\n"
          "Please wait 30 seconds, then refresh the page to check if data was imported.",
          title="Timeout",
          large=True
        )

      except Exception as e:
        # Handle any other errors
        if loading_notification:
          loading_notification.hide()
        print(f"❌ Error in file_loader_1_change: {e}")
        alert(f"❌ Import error: {str(e)}", title="Error")

    else:
      Notification("Please select a file to upload.", style="warning").show()

  def btn_clear_inventory_click(self, **event_args):
    """Clear all inventory data"""
    if confirm("Are you sure you want to clear ALL inventory data?"):
      try:
        app_tables.inventory.delete_all_rows()
        Notification("✅ Inventory cleared successfully.", style="success", timeout=3).show()
      except Exception as e:
        print(f"❌ Error clearing inventory: {e}")
        Notification(f"❌ Error clearing inventory: {str(e)}", style="danger", timeout=5).show()

  def shopping_list_link_click(self, **event_args):
    """Navigate to Shopping List"""
    try:
      main_form = get_open_form()
      main_form.link_shopping_list_click()
    except Exception as e:
      print(f"❌ Error navigating to shopping list: {e}")
      Notification("Error navigating to shopping list", style="danger").show()

  def link_order_history_click(self, **event_args):
    """Navigate to Order History"""
    try:
      print("AdminForm: Order History link clicked!")
      main_form = get_open_form()
      main_form.link_order_history_click()
    except Exception as e:
      print(f"❌ Error navigating to order history: {e}")
      Notification("Error navigating to order history", style="danger").show()

  def link_audit_logs_click(self, **event_args):
    """Navigate to Audit Logs - Admin Only"""
    try:
      from ..AuditLogForm import AuditLogForm
      main_layout = get_open_form()
      main_layout.content_panel.clear()
      main_layout.content_panel.add_component(AuditLogForm())
      print("✅ Navigated to Audit Logs")
    except Exception as e:
      print(f"❌ Error in link_audit_logs_click: {e}")
      Notification(f"Error loading audit logs: {str(e)}", style="danger", timeout=5).show()