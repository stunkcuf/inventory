from ._anvil_designer import OrderFillFormTemplate
from anvil import *
import anvil.users
import anvil.server
from datetime import datetime

class OrderFillForm(OrderFillFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.setup_form()
    self.refresh_orders()

  def setup_form(self):
    """Setup dropdowns"""
    # Category
    if hasattr(self, 'dd_category'):
      self.dd_category.items = ["Office", "Center"]
      self.dd_category.selected_value = "Office"

    # All locations
    if hasattr(self, 'dd_location'):
      self.dd_location.items = [
        "Main Office", "Bus Barn", "NELC", "FACE", "Airport Way",
        "Patriot Heights", "PELC", "PEHS", "Umatilla", "Milton-Freewater",
        "HCDC", "Pinetree", "Rocky Heights", "Victory Square", 
        "CWELC", "Annex La Grande", "Irrigon", "CCR&R"
      ]

    # Status filter
    if hasattr(self, 'dd_filter_status'):
      self.dd_filter_status.items = ["All", "Pending", "Filled", "Cancelled"]
      self.dd_filter_status.selected_value = "All"

    # Date default
    if hasattr(self, 'date_requested'):
      self.date_requested.date = datetime.now().date()

  def refresh_orders(self):
    """Load orders with filters"""
    try:
      # Get filter values
      status_filter = self.dd_filter_status.selected_value if hasattr(self, 'dd_filter_status') else "All"

      # Get orders from server
      orders = anvil.server.call('get_machform_orders', status_filter)

      # Update list
      if hasattr(self, 'repeating_panel_orders'):
        self.repeating_panel_orders.items = orders

      # Update summary
      if hasattr(self, 'label_summary'):
        pending = sum(1 for o in orders if o.get('status') == 'Pending')
        filled = sum(1 for o in orders if o.get('status') == 'Filled')
        total_cost = sum(o.get('total_cost', 0) for o in orders if o.get('status') == 'Pending')

        self.label_summary.text = (
          f"Total: {len(orders)} | "
          f"Pending: {pending} | "
          f"Filled: {filled} | "
          f"Pending Cost: ${total_cost:,.2f}"
        )

      print(f"Loaded {len(orders)} orders")

    except Exception as e:
      print(f"Error loading orders: {e}")
      Notification(f"Error: {str(e)}", style="danger").show()

  def btn_save_click(self, **event_args):
    """Save new order"""
    try:
      # Validate
      if not self.text_requester.text:
        alert("Requester name required!")
        return

      if not self.dd_location.selected_value:
        alert("Location required!")
        return

      # Save
      order_data = {
        'date_requested': self.date_requested.date,
        'requester_name': self.text_requester.text,
        'location': self.dd_location.selected_value,
        'category': self.dd_category.selected_value,
        'items_summary': self.text_items.text,
        'total_cost': float(self.num_total.text) if self.num_total.text else 0,
        'status': 'Pending',
        'notes': self.text_notes.text if hasattr(self, 'text_notes') else ""
      }

      anvil.server.call('save_machform_order', order_data)

      Notification("✅ Order saved!", style="success", timeout=2).show()
      self.clear_form()
      self.refresh_orders()

    except Exception as e:
      print(f"Save error: {e}")
      alert(f"Error: {str(e)}")

  def clear_form(self):
    """Clear entry form"""
    self.text_requester.text = ""
    self.text_items.text = ""
    self.num_total.text = None
    if hasattr(self, 'text_notes'):
      self.text_notes.text = ""
    self.date_requested.date = datetime.now().date()

  def dd_filter_status_change(self, **event_args):
    """Status filter changed"""
    self.refresh_orders()

  def btn_refresh_click(self, **event_args):
    """Refresh button"""
    self.refresh_orders()
    Notification("Refreshed", style="info", timeout=1).show()