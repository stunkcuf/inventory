from ._anvil_designer import OrderHistoryFormTemplate
from anvil import *
import anvil.server
from datetime import datetime, timedelta

class OrderHistoryForm(OrderHistoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Set up date filter dropdowns
    self.setup_filters()

    # Load order history
    self.refresh_history()

  def setup_filters(self):
    """Setup filter dropdowns"""
    # Category filter
    if hasattr(self, 'dd_category_filter'):
      self.dd_category_filter.items = ["All", "Office", "Center"]
      self.dd_category_filter.selected_value = "All"

    # Date range filter
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
      # Get all ordered items
      history = anvil.server.call('get_ordered_history')

      # Apply filters
      filtered_history = self.apply_filters(history)

      # Update repeating panel
      self.repeating_panel_history.items = filtered_history

      # Update summary
      self.update_summary(filtered_history)

      # Show/hide empty message
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

    # Category filter
    if hasattr(self, 'dd_category_filter'):
      category = self.dd_category_filter.selected_value
      if category and category != "All":
        filtered = [item for item in filtered if item.get('Source') == category]

    # Date filter
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

    return datetime(2000, 1, 1).date()  # All time

  def update_summary(self, history):
    """Update summary statistics"""
    if hasattr(self, 'lbl_summary'):
      total = len(history)
      office = sum(1 for item in history if item.get('Source') == 'Office')
      center = sum(1 for item in history if item.get('Source') == 'Center')

      # Get date range
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

  def btn_refresh_click(self, **event_args):
    """Refresh button clicked"""
    self.refresh_history()
    Notification("Order history refreshed", style="info", timeout=2).show()

  def btn_export_click(self, **event_args):
    """Export order history to CSV"""
    try:
      import csv
      from io import StringIO

      history = self.repeating_panel_history.items

      if not history:
        Notification("No history to export", style="warning").show()
        return

      # Create CSV
      output = StringIO()
      writer = csv.writer(output)

      # Header
      writer.writerow(['Date Ordered', 'Item', 'Category', 'Link'])

      # Data rows
      for item in history:
        writer.writerow([
          item.get('Date', ''),
          item.get('Item', ''),
          item.get('Source', ''),
          item.get('Link', '')
        ])

      # Download
      csv_data = output.getvalue()
      timestamp = datetime.now().strftime('%Y%m%d_%H%M')
      anvil.media.download(
        anvil.BlobMedia('text/csv', csv_data.encode(), 
                        name=f'order_history_{timestamp}.csv')
      )

      Notification("Order history exported!", style="success").show()

    except Exception as e:
      print(f"Export error: {e}")
      Notification(f"Export error: {str(e)}", style="danger").show()

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
    from ..ShoppingListForm import ShoppingListForm
    main_layout = get_open_form()
    main_layout.content_panel.clear()
    main_layout.content_panel.add_component(ShoppingListForm())