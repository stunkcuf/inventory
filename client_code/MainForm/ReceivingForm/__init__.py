from ._anvil_designer import ReceivingFormTemplate
from anvil import Button, DropDown, FlowPanel, Label, LinearPanel, Notification, TextBox, alert, get_open_form
import anvil.server


class ReceivingForm(ReceivingFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.orders = {}
    toolbar = FlowPanel(align='left', role='shopping-list-toolbar')
    self.po_selector = DropDown(placeholder="Select a purchase order")
    self.po_selector.set_event_handler('change', self.show_order)
    toolbar.add_component(self.po_selector)
    refresh = Button(text="Refresh", icon="fa:refresh", role='workspace-button')
    refresh.set_event_handler('click', self.load_orders)
    toolbar.add_component(refresh)
    self.add_component(toolbar)
    self.lines = LinearPanel()
    self.add_component(self.lines)
    self.load_orders()

  def load_orders(self, **event_args):
    try:
      orders = anvil.server.call('get_receiving_orders')
    except Exception as error:
      Notification(f"Could not load purchase orders: {error}", style='danger').show()
      return
    self.orders = orders
    selection = self.po_selector.selected_value
    self.po_selector.items = [
      (f"PO {number} · {'Open' if any(line['received'] < line['ordered'] for line in lines) else 'Received'}", number)
      for number, lines in orders.items()
    ]
    self.po_selector.selected_value = selection if selection in orders else next(iter(orders), None)
    self.show_order()

  def show_order(self, **event_args):
    self.lines.clear()
    lines = self.orders.get(self.po_selector.selected_value, [])
    if not lines:
      self.lines.add_component(Label(text="No POs with saved quantities yet. Add one from Shopping List."))
    for line in lines:
      card = LinearPanel(role='workspace-surface')
      card.add_component(Label(text=f"{line['item']} · {line['category']}", bold=True))
      due = line['ordered'] - line['received']
      card.add_component(Label(text=f"Ordered {line['ordered']} · Received {line['received']} · Due {due}"))
      if due:
        receive = Button(text="Record receipt", icon="fa:check", role='workspace-primary')
        receive.set_event_handler('click', self.receipt_handler(line))
        card.add_component(receive)
      self.lines.add_component(card)

  def receipt_handler(self, line):
    def record_receipt(sender, **event_args):
      fields = LinearPanel()
      fields.add_component(Label(text="Quantity physically received"))
      quantity = TextBox(type='number')
      fields.add_component(quantity)
      fields.add_component(Label(text="Packing slip or delivery reference"))
      reference = TextBox()
      fields.add_component(reference)
      if not alert(fields, title=f"Receive {line['item']}",
                   buttons=[('Confirm receipt', True), ('Cancel', False)]):
        return
      sender.enabled = False
      try:
        saved = anvil.server.call('record_po_receipt', line['id'], quantity.text, reference.text)
      except Exception as error:
        alert(f"Could not record the receipt: {error}")
        return
      finally:
        sender.enabled = True
      message = "Receipt recorded and stock updated." if saved else "That delivery was already recorded."
      Notification(message, style='success' if saved else 'info').show()
      self.load_orders()
      get_open_form().refresh_task_counts()
    return record_receipt
