from ._anvil_designer import OrderHistoryFormTemplate
from anvil import *
import anvil.users
import anvil.server
from datetime import datetime, timedelta

class OrderHistoryForm(OrderHistoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.setup_filters()
    self.refresh_history()

  def setup_filters(self):
    """Setup filter dropdowns"""
    if hasattr(self, 'dd_category_filter'):
      self.dd_category_filter.items = ["All", "Office", "Center"]
      self.dd_category_filter.selected_value = "All"

    if hasattr(self, 'dd_date_filter'):
      self.dd_date_filter.items = [
        "All Time",
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "This Year"
      ]
      self.dd_date_filter.selected_value = "All Time"

  def refresh_history(self):
    """Load order history from server"""
    print("Loading order history...")

    try:
      history = anvil.server.call('get_ordered_history')
      filtered_history = self.apply_filters(history)
      self.repeating_panel_history.items = filtered_history
      self.update_summary(filtered_history)

      if hasattr(self, 'lbl_empty'):
        self.lbl_empty.visible = len(filtered_history) == 0

      print(f"Loaded {len(filtered_history)} order history records")

    except Exception as e:
      print(f"Error loading history: {e}")
      import traceback
      traceback.print_exc()
      Notification(f"Error loading history: {str(e)}", style="danger").show()

  def apply_filters(self, history):
    """Apply category and date filters"""
    filtered = history

    if hasattr(self, 'dd_category_filter'):
      category = self.dd_category_filter.selected_value
      if category and category != "All":
        filtered = [item for item in filtered if item.get('Source') == category]

    if hasattr(self, 'dd_date_filter'):
      date_range = self.dd_date_filter.selected_value
      if date_range and date_range != "All Time":
        cutoff_date = self.get_cutoff_date(date_range)
        filtered = [
          item for item in filtered 
          if item.get('Date') and item['Date'] >= cutoff_date
        ]

    return filtered

  def get_cutoff_date(self, date_range):
    """Calculate cutoff date based on selected range"""
    today = datetime.now().date()

    if date_range == "Last 7 Days":
      return today - timedelta(days=7)
    elif date_range == "Last 30 Days":
      return today - timedelta(days=30)
    elif date_range == "Last 90 Days":
      return today - timedelta(days=90)
    elif date_range == "This Year":
      return datetime(today.year, 1, 1).date()

    return datetime(2000, 1, 1).date()

  def update_summary(self, history):
    """Update summary statistics"""
    if hasattr(self, 'lbl_summary'):
      total = len(history)
      office = sum(1 for item in history if item.get('Source') == 'Office')
      center = sum(1 for item in history if item.get('Source') == 'Center')

      if history:
        dates = [item['Date'] for item in history if item.get('Date')]
        if dates:
          oldest = min(dates)
          newest = max(dates)
          date_range = f"{oldest} to {newest}"
        else:
          date_range = "No dates"
      else:
        date_range = "N/A"

      self.lbl_summary.text = (
        f"Total Orders: {total} | "
        f"Office: {office} | "
        f"Center: {center} | "
        f"Range: {date_range}"
      )

  def dd_category_filter_change(self, **event_args):
    """Category filter changed"""
    self.refresh_history()

  def dd_date_filter_change(self, **event_args):
    """Date filter changed"""
    self.refresh_history()

  @handle("btn_refresh", "click")
  def btn_refresh_click(self, **event_args):
    """Refresh button clicked"""
    self.refresh_history()
    Notification("Order history refreshed", style="info", timeout=2).show()

  @handle("btn_export", "click")
  def btn_export_click(self, **event_args):
    """Export order history to CSV - FIXED: Server-side"""
    try:
      history = self.repeating_panel_history.items

      if not history:
        Notification("No history to export", style="warning").show()
        return

      # Call server to generate CSV
      csv_media = anvil.server.call('export_order_history_csv', history)

      if csv_media:
        anvil.media.download(csv_media)
        Notification("Order history exported!", style="success").show()
      else:
        Notification("Export failed", style="danger").show()

    except Exception as e:
      print(f"Export error: {e}")
      Notification(f"Export error: {str(e)}", style="danger").show()

  @handle("btn_clear_history", "click")
  def btn_clear_history_click(self, **event_args):
    """Clear all order history (reset Ordered flags)"""
    if confirm("Clear ALL order history? This will mark all items as not ordered."):
      try:
        count = anvil.server.call('clear_order_history')
        Notification(f"Cleared {count} order records", style="success").show()
        self.refresh_history()
      except Exception as e:
        Notification(f"Error: {str(e)}", style="danger").show()

  def link_shopping_list_click(self, **event_args):
    """Navigate to shopping list"""
    get_open_form().link_shopping_list_click()
