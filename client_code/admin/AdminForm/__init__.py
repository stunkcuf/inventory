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
    panel.add_component(Label(text="In MachForm, open Notifications → Send Form Data to Another Website. "
                                   "Paste the URL for that form and send the submission fields. "
                                   "Anvil saves them in the MachForm inbox."))
    panel.add_component(Label(text="The MachForm admin must add the webhook credential "
                                   "as the X-MachForm-Token header or webhook_token POST field."))
    if not settings['enabled']:
      panel.add_component(Label(text="Inbox disabled. Set machform_webhook_secret in Anvil App Secrets."))

    for form_id, url in settings['urls']:
      button = Button(text=f"Copy URL for form {form_id}", icon="fa:clipboard")

      def copy_url(url=url, **event_args):
        try:
          await_promise(window.navigator.clipboard.writeText(url))
          Notification("Webhook URL copied.", style="success").show()
        except Exception:
          alert(TextBox(text=url), title="Copy webhook URL")

      button.set_event_handler('click', copy_url)
      panel.add_component(button)

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

  def link_audit_logs_click(self, **event_args):
    get_open_form().show_audit_logs()
