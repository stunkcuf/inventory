from ._anvil_designer import AdminFormTemplate
from anvil import *
from anvil.js import await_promise, window
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class AdminForm(AdminFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def machform_integration_click(self, **event_args):
    try:
      settings = anvil.server.call('get_machform_webhook_settings')
    except Exception:
      Notification("Unable to load MachForm settings.", style="danger").show()
      return

    panel = LinearPanel()
    status = ("Paste this URL into the webhook settings for forms 161659 and 161453."
              if settings['enabled'] else
              "Receiver disabled. Configure machform_webhook_secret in Anvil App Secrets.")
    panel.add_component(Label(text=status))
    panel.add_component(TextBox(text=settings['url'], enabled=False))
    copy_button = Button(text="Copy webhook URL", icon="fa:clipboard")

    def copy_url(**event_args):
      try:
        await_promise(window.navigator.clipboard.writeText(settings['url']))
        Notification("Webhook URL copied.", style="success").show()
      except Exception:
        alert(settings['url'], title="Copy this webhook URL")

    copy_button.set_event_handler('click', copy_url)
    panel.add_component(copy_button)
    alert(panel, title="MachForm Integration", large=True)

  def file_loader_1_change(self, file, **event_args):
    """Import Excel file with chunked import options"""
    if file:
      # Ask user which import mode they want
      mode = alert(
        content="Choose import strategy:",
        title="Import Mode",
        buttons=[
          ("Quick (Calcs + Small Summaries)", 'quick'),
          ("Main Summary Only (2025-Summary)", 'main_summary'),
          ("Full Import (May Timeout)", 'full'),
          ("Cancel", None)
        ],
        large=True
      )

      if not mode:
        return  # User cancelled

      loading_notification = None
      try:
        # Show loading notification
        mode_text = {
          'quick': 'Quick import (calcs + small summaries)',
          'main_summary': 'Main summary (2025-Summary only)',
          'full': 'Full import (all sheets)'
        }.get(mode, mode)

        loading_notification = Notification(
          f"📥 {mode_text}... Please wait...", 
          style="info", 
          timeout=None
        )
        loading_notification.show()

        # Call server with selected mode
        result = anvil.server.call('process_excel_import', file, mode)

        # Hide loading notification
        if loading_notification:
          loading_notification.hide()
          loading_notification = None

        # Show results
        if result.get('success'):
          stats = result['stats']
          mode_used = result.get('import_mode', 'unknown')

          msg = f"✅ Import Complete ({mode_used} mode)!\n\n"
          msg += f"📊 Imported {result['total_items']} total items:\n\n"

          if stats['office_calcs'] > 0:
            msg += f"  • Office Calcs: {stats['office_calcs']}\n"
          if stats['center_calcs'] > 0:
            msg += f"  • Center Calcs: {stats['center_calcs']}\n"
          if stats['summary_2025'] > 0:
            msg += f"  • Summary 2025: {stats['summary_2025']}\n"
          if stats['inventory_summary_office'] > 0:
            msg += f"  • Summary Office: {stats['inventory_summary_office']}\n"
          if stats['inventory_summary_center'] > 0:
            msg += f"  • Summary Center: {stats['inventory_summary_center']}\n"
          if stats['inventory_summary_internal'] > 0:
            msg += f"  • Summary Internal: {stats['inventory_summary_internal']}\n"

          if stats['warnings']:
            msg += f"\n⚠️ {len(stats['warnings'])} warnings"
          if stats['errors']:
            msg += f"\n❌ {len(stats['errors'])} errors"

          # Suggest next steps if not full import
          if mode_used == 'quick':
            msg += "\n\n💡 Next: Run 'Main Summary Only' to import 2025-Summary sheet"
          elif mode_used == 'main_summary':
            msg += "\n\n✅ Import complete! If you need calcs/other summaries, run 'Quick' import"

          alert(msg, title="Import Complete", large=True)

        else:
          alert(f"❌ Import failed: {result.get('error', 'Unknown error')}", title="Import Failed")

      except anvil.server.TimeoutError:
        if loading_notification:
          loading_notification.hide()
        alert(
          "⏱️ Import timed out.\n\n"
          "Try using 'Quick' mode first, then 'Main Summary Only' mode.\n"
          "This splits the import into two faster passes.",
          title="Timeout",
          large=True
        )

      except Exception as e:
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
    """Navigate to Audit Logs"""
    print("🔍 Audit logs link clicked!")

    try:
      from ..AuditViewer import AuditViewer  # NEW NAME
      print("✅ Import successful!")

      main_layout = get_open_form()
      main_layout.content_panel.clear()
      main_layout.content_panel.add_component(AuditViewer())

      print("✅ Navigated to Audit Logs!")

    except Exception as e:
      print(f"❌ ERROR: {e}")
      alert(f"Error: {str(e)}", title="Error")