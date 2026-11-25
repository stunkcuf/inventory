from ._anvil_designer import RowTemplate3Template
from anvil import *
import anvil.users
import anvil.server

class RowTemplate3(RowTemplate3Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Calculate quantity to buy
    on_hand = self.item.get('On_Hand', 0)
    minimum = self.item.get('Minimum_Amt', 0)
    qty_to_buy = max(0, minimum - on_hand)

    self.lbl_dept.text = self.item['Category']
    self.link_item.text = self.item['Item']
    self.link_item.url = self.item['Item_Link']
    self.add_purchase_link.visible = not self.item['Item_Link']
    if not self.item['Item_Link']:
      self.link_item.role = 'shopping-item-no-link'
    self.lbl_price.text = f"${self.item['Price']:.2f}"
    self.lbl_qty.text = str(qty_to_buy)
    self.check_ordered.checked = self.item['Ordered']
    self.update_row_status()

  def update_row_status(self):
    ordered = self.check_ordered.checked
    self.role = 'shopping-row-ordered' if ordered else 'shopping-row'
    po_number = self.item.get('PO_Number')
    self.check_ordered.text = (f"Ordered · PO {po_number}" if ordered and po_number
                               else 'Ordered' if ordered else 'Mark ordered')
    self.check_ordered.tooltip = f"Order status for {self.item['Item']}"

  def check_ordered_change(self, **event_args):
    """This method is called when the checkbox is toggled"""
    previous_status = self.item['Ordered']
    new_status = self.check_ordered.checked
    if new_status == previous_status:
      return

    self.check_ordered.enabled = False
    po_number = None
    ordered_quantity = None
    try:
      if new_status:
        po_input = TextBox(placeholder="PO number")
        quantity_input = TextBox(type='number', text=max(
          1, self.item['Minimum_Amt'] - self.item['On_Hand']
        ))
        details = LinearPanel()
        details.add_component(Label(text="PO number"))
        details.add_component(po_input)
        details.add_component(Label(text="Quantity ordered"))
        details.add_component(quantity_input)
        confirmed = alert(details, title=f"Mark {self.item['Item']} ordered",
                          buttons=[('Save', True), ('Cancel', False)])
        if not confirmed:
          self.check_ordered.checked = previous_status
          return
        po_number = (po_input.text or '').strip()
        ordered_quantity = quantity_input.text
        if ordered_quantity is None:
          self.check_ordered.checked = previous_status
          Notification("Enter the quantity ordered.", style="warning").show()
          return
        if not po_number or len(po_number) > 100:
          self.check_ordered.checked = previous_status
          Notification("Enter a PO number of 1 to 100 characters.", style="warning").show()
          return
      result = anvil.server.call(
        'check_ordered', self.item['Item'], self.item['Category'], new_status, po_number,
        ordered_quantity, self.item.get('Inventory_ID')
      )
    except Exception as e:
      self.check_ordered.checked = previous_status
      alert(f"Could not save order status: {e}")
      return
    finally:
      self.check_ordered.enabled = True

    if not result:
      self.check_ordered.checked = previous_status
      alert(f"Could not find '{self.item['Item']}' in the ordering table.")
      return

    self.item['Ordered'] = new_status
    self.item['PO_Number'] = po_number
    self.update_row_status()
    main_form = get_open_form()
    for component in main_form.content_panel.get_components():
      if hasattr(component, 'order_status_changed'):
        component.order_status_changed(self.item)
        break
    main_form.refresh_task_counts()


  def add_purchase_link_click(self, **event_args):
    link = TextBox(placeholder="https://")
    if not alert(link, title=f"Purchase link for {self.item['Item']}",
                 buttons=[('Save', True), ('Cancel', False)]):
      return
    try:
      anvil.server.call('add_missing_purchase_link', self.item['Item'], self.item['Category'], link.text)
    except Exception as error:
      alert(f"Could not save the purchase link: {error}")
      return
    for component in get_open_form().content_panel.get_components():
      if hasattr(component, 'refresh_list'):
        component.refresh_list()
        break
