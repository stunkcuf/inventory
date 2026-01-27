from ._anvil_designer import AuditLogFormTemplate
from anvil import *
import anvil.server

class AuditLogForm(AuditLogFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Check admin access with fallback
    try:
      is_admin = anvil.server.call('is_admin')
      if not is_admin:
        alert("Admin access required to view audit logs")
        return
    except Exception as e:
      # Fallback: Allow access if function not loaded yet
      print(f"Admin check skipped: {e}")

    self.setup_filters()
    self.refresh_logs()

  def setup_filters(self):
    """Setup filter dropdown"""
    if hasattr(self, 'dd_table_filter'):
      self.dd_table_filter.items = [
        "All",
        "inventory",
        "office_calcs",
        "center_calcs",
        "machform_orders"
      ]
      self.dd_table_filter.selected_value = "All"

  def refresh_logs(self):
    """Load audit logs"""
    try:
      table_filter = self.dd_table_filter.selected_value if hasattr(self, 'dd_table_filter') else "All"
      logs = anvil.server.call('get_audit_logs', limit=200, table_filter=table_filter)

      if hasattr(self, 'repeating_panel_logs'):
        self.repeating_panel_logs.items = logs

      if hasattr(self, 'label_summary'):
        self.label_summary.text = f"Showing {len(logs)} audit log entries"

      print(f"Loaded {len(logs)} audit logs")

    except Exception as e:
      print(f"Error loading logs: {e}")
      Notification(f"Error: {str(e)}", style="danger").show()

  @handle("dd_table_filter", "change")
  def dd_table_filter_change(self, **event_args):
    """Filter changed"""
    self.refresh_logs()

  @handle("btn_refresh", "click")
  def btn_refresh_click(self, **event_args):
    """Refresh button"""
    self.refresh_logs()
    Notification("Logs refreshed", style="info", timeout=2).show()