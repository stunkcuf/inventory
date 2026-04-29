from ._anvil_designer import AuditViewerTemplate
from anvil import *
import anvil.server

class AuditViewer(AuditViewerTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    print("AuditViewer initialized")
    self.setup_filters()
    self.refresh_logs()

  def setup_filters(self):
    """Setup filter dropdown"""
    self.dd_table_filter.items = [
      "All",
      "inventory",
      "stock_transactions",
      "office_calcs",
      "center_calcs"
    ]
    self.dd_table_filter.selected_value = "All"

  def refresh_logs(self):
    """Load audit logs"""
    try:
      self.label_summary.text = "Loading..."

      table_filter = self.dd_table_filter.selected_value
      logs = anvil.server.call('get_audit_logs', limit=200, table_filter=table_filter)

      self.repeating_panel_logs.items = logs
      self.label_summary.text = f"Showing {len(logs)} audit log entries"

      print(f"Loaded {len(logs)} audit logs")

    except Exception as e:
      print(f"Error loading logs: {e}")
      self.label_summary.text = f"Error: {str(e)}"
      Notification(f"Error: {str(e)}", style="danger").show()

  def dd_table_filter_change(self, **event_args):
    self.refresh_logs()

  def btn_refresh_click(self, **event_args):
    self.refresh_logs()
    Notification("Refreshed", style="info", timeout=2).show()