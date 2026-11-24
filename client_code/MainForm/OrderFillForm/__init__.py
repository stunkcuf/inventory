from ._anvil_designer import OrderFillFormTemplate
from anvil import Label, LinearPanel, Notification
import anvil.server


class OrderFillForm(OrderFillFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.dd_filter_status.items = ["All", "Pending", "Partial", "Filled", "Cancelled"]
    self.dd_filter_status.selected_value = "All"
    self.refresh_orders()

  def refresh_orders(self, **event_args):
    try:
      result = anvil.server.call('get_machform_orders', self.dd_filter_status.selected_value)
    except Exception as e:
      self.order_list.clear()
      self.label_summary.text = "Orders could not be loaded."
      Notification(str(e), style="danger").show()
      return

    self.order_list.clear()
    orders = result['orders']
    if result['has_more']:
      self.label_summary.text = "Showing the first 100 matching orders. Filter by status to narrow the list."
    elif orders:
      self.label_summary.text = f"{len(orders)} matching orders"
    else:
      self.label_summary.text = "No matching orders."

    for order in orders:
      card = LinearPanel(role="outlined-card")
      card.add_component(Label(text=order['fulfillment_status'] or "Status unavailable", bold=True))
      if order['items_json']:
        card.add_component(Label(text=order['items_json']))
      if order['notes']:
        card.add_component(Label(text=order['notes']))
      fulfillment = [str(order[field]) for field in ('fulfilled_by', 'fulfilled_date') if order[field]]
      if fulfillment:
        card.add_component(Label(text=" · ".join(fulfillment)))
      self.order_list.add_component(card)
