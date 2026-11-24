from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server
import anvil.js
from datetime import datetime
from .RowTemplate3 import RowTemplate3


def escape_print_text(value):
  return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

SHOPPING_COLUMNS = [
  {'id': 'RTETBL', 'title': 'Status', 'data_key': 'ordered', 'width': 180, 'expand': False},
  {'id': 'VJQQOR', 'title': 'Item', 'data_key': 'item'},
  {'id': 'JKSDUP', 'title': 'Department', 'data_key': 'category', 'width': 114, 'expand': False},
  {'id': 'LBWNFU', 'title': 'Qty to buy', 'data_key': 'to_order', 'width': 96, 'expand': False},
  {'id': 'OJLQEN', 'title': 'Unit price', 'data_key': 'price', 'width': 96, 'expand': False},
]
NO_ORDERING_LINK = 'No ordering link'


class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.items = []
    self.status_filter.items = [('To buy', 'pending'), ('Ordered', 'ordered'), ('All', 'all')]
    self.status_filter.selected_value = 'pending'
    self.refresh_list()

  def supplier_groups(self):
    groups = {}
    status = self.status_filter.selected_value
    for item in self.items:
      ordered = bool(item.get('Ordered'))
      if (status == 'pending' and ordered) or (status == 'ordered' and not ordered):
        continue
      groups.setdefault(item.get('Supplier') or NO_ORDERING_LINK, []).append(item)
    return sorted(groups.items(), key=lambda group: (group[0] == NO_ORDERING_LINK, group[0].lower()))

  def refresh_list(self):
    try:
      self.items = anvil.server.call('get_shopping_list')
    except Exception as e:
      Notification(f"Could not load shopping list: {e}", style="danger").show()
      return False

    self.render_suppliers()
    return True

  def render_suppliers(self):
    self.supplier_sections.clear()
    groups = self.supplier_groups()
    for supplier, items in groups:
      pending = [item for item in items if not item.get('Ordered')]
      actions = FlowPanel(align='left', role='shopping-list-toolbar')
      actions.add_component(Label(text=f"{supplier} · {len(items)} shown · "
                                       f"${self.estimated_cost(pending):,.2f} to buy",
                                  role='shopping-supplier-heading'))
      if pending:
        print_button = Button(text="Print to buy", icon="fa:print", role='workspace-button')
        print_button.set_event_handler('click', self.print_supplier_handler(supplier))
        actions.add_component(print_button)
      self.supplier_sections.add_component(actions)
      grid = DataGrid(columns=SHOPPING_COLUMNS, role='inventory-table', rows_per_page=25)
      grid.add_component(RepeatingPanel(item_template=RowTemplate3, items=items))
      self.supplier_sections.add_component(grid)

    if not groups:
      message = "No items are below minimum stock." if not self.items else "No items match this status."
      self.supplier_sections.add_component(Label(text=message))
    self.update_summary()

  def status_filter_change(self, **event_args):
    self.render_suppliers()

  def order_status_changed(self, updated):
    for item in self.items:
      if (item['Item'], item['Category']) == (updated['Item'], updated['Category']):
        item.update(Ordered=updated['Ordered'], PO_Number=updated.get('PO_Number'))
    self.render_suppliers()

  def estimated_cost(self, items):
    return sum((item.get('Price') or 0) * max(0, item['Minimum_Amt'] - item['On_Hand'])
               for item in items)

  def update_summary(self):
    ordered_count = sum(bool(item.get('Ordered')) for item in self.items)
    pending_cost = self.estimated_cost(item for item in self.items if not item.get('Ordered'))
    self.label_summary.text = (
      f"{len(self.items)} items · {ordered_count} ordered · ${pending_cost:,.2f} estimated remaining"
    )

  def print_button_click(self, **event_args):
    self.print_groups(self.supplier_groups())

  def print_supplier_handler(self, supplier):
    def print_supplier(**event_args):
      items = [item for item in self.items
               if (item.get('Supplier') or NO_ORDERING_LINK) == supplier and not item.get('Ordered')]
      self.print_groups([(supplier, items)] if items else [])
    return print_supplier

  def print_groups(self, groups):
    if not groups:
      alert("No items to print.")
      return

    date_str = datetime.now().strftime('%B %d, %Y')
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Shopping List</title>
      <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h1, h2 {{ color: #124b55; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
        th {{ background: #edf5f6; padding: 10px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        tr {{ break-inside: avoid; }}
        h2 {{ break-after: avoid; }}
        @media print {{ .no-print {{ display: none; }} }}
      </style>
    </head>
    <body>
      <h1>Shopping List · {date_str}</h1>
      <button class="no-print" onclick="window.print()">Print</button>
    """

    for supplier, items in groups:
      html += f"""<h2>{escape_print_text(supplier)}</h2>
        <table><thead><tr><th>Status</th><th>Item</th><th>Department</th>
        <th>Qty to buy</th><th>Unit price</th><th>Total</th><th>PO number</th></tr></thead><tbody>"""
      for item in items:
        qty = max(0, item['Minimum_Amt'] - item['On_Hand'])
        price = item.get('Price') or 0
        status = 'Ordered' if item.get('Ordered') else 'To order'
        html += f"""
          <tr><td>{status}</td><td>{escape_print_text(item['Item'])}</td>
          <td>{escape_print_text(item['Category'])}</td><td>{qty}</td>
          <td>${price:.2f}</td><td>${price * qty:.2f}</td>
          <td>{escape_print_text(item.get('PO_Number') or '')}</td></tr>"""
      html += "</tbody></table>"

    html += "</body></html>"
    win = anvil.js.window.open('', '_blank')
    win.document.write(html)
    win.document.close()

  def refresh_button_click(self, **event_args):
    if self.refresh_list():
      Notification("Shopping list refreshed", style="info", timeout=2).show()
