from ._anvil_designer import OrderHistoryRowTemplateTemplate
from anvil import *
import anvil.server

class OrderHistoryRowTemplate(OrderHistoryRowTemplateTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Display data
    self.label_date.text = str(self.item.get('date_requested', ''))
    self.label_requester.text = self.item.get('requester_name', '')
    self.label_location.text = self.item.get('location', '')

    # Truncate items text
    items = self.item.get('items_summary', '')
    self.label_items.text = items[:50] + "..." if len(items) > 50 else items

    self.label_cost.text = f"${self.item.get('total_cost', 0):.2f}"
    self.label_category.text = self.item.get('category', '')

    # Status checkbox
    status = self.item.get('status', 'Pending')
    self.check_filled.checked = (status == 'Filled')

    # Visual styling
    if status == 'Filled':
      self.card_row.background = '#e8f5e9'  # Light green
    elif status == 'Cancelled':
      self.card_row.background = '#ffebee'  # Light red

  def check_filled_change(self, **event_args):
    """Toggle filled status"""
    try:
      new_status = 'Filled' if self.check_filled.checked else 'Pending'

      # Update server
      result = anvil.server.call(
        'update_order_status',
        self.item.get('order_id'),
        new_status
      )

      if result:
        self.item['status'] = new_status

        # Update visual
        if new_status == 'Filled':
          self.card_row.background = '#e8f5e9'
          Notification("✅ Marked as filled", style="success", timeout=2).show()
        else:
          self.card_row.background = 'white'
          Notification("Order marked as pending", style="info", timeout=2).show()

        # Refresh parent
        parent_form = self.parent.parent.parent
        if hasattr(parent_form, 'refresh_orders'):
          parent_form.refresh_orders()

    except Exception as e:
      print(f"Status update error: {e}")
      # Revert checkbox
      self.check_filled.checked = not self.check_filled.checked