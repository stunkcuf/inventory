from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server
import anvil.js
from datetime import datetime
from .RowTemplate3 import RowTemplate3


def escape_print_text(value):
  return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

SHOPPING_COLUMNS = [
  {'id': 'RTETBL', 'title': 'Status', 'data_key': 'ordered', 'width': 142, 'expand': False},
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
    self.refresh_list()

  def supplier_groups(self):
    groups = {}
    for item in self.items:
      groups.setdefault(item.get('Supplier') or NO_ORDERING_LINK, []).append(item)
    return sorted(groups.items(), key=lambda group: (group[0] == NO_ORDERING_LINK, group[0].lower()))

  def refresh_list(self):
    try:
      self.items = anvil.server.call('get_shopping_list')
    except Exception as e:
      Notification(f"Could not load shopping list: {e}", style="danger").show()
      return False

    self.supplier_sections.clear()
    for supplier, items in self.supplier_groups():
      self.supplier_sections.add_component(Label(
        text=f"{supplier} · {len(items)}", role='shopping-supplier-heading'
      ))
      grid = DataGrid(columns=SHOPPING_COLUMNS, role='inventory-table', rows_per_page=25)
      grid.add_component(RepeatingPanel(item_template=RowTemplate3, items=items))
      self.supplier_sections.add_component(grid)

    if not self.items:
      self.supplier_sections.add_component(Label(text="No items are below minimum stock."))
    self.update_summary()
    return True

  def update_summary(self):
    ordered_count = sum(bool(item.get('Ordered')) for item in self.items)
    pending_cost = sum(
      (item.get('Price') or 0) * max(0, item['Minimum_Amt'] - item['On_Hand'])
      for item in self.items if not item.get('Ordered')
    )
    self.label_summary.text = (
      f"{len(self.items)} items · {ordered_count} ordered · ${pending_cost:,.2f} estimated remaining"
    )

  def print_button_click(self, **event_args):
    if not self.items:
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

    for supplier, items in self.supplier_groups():
      html += f"""<h2>{escape_print_text(supplier)}</h2>
        <table><thead><tr><th>Status</th><th>Item</th><th>Department</th>
        <th>Qty to buy</th><th>Unit price</th><th>Total</th></tr></thead><tbody>"""
      for item in items:
        qty = max(0, item['Minimum_Amt'] - item['On_Hand'])
        price = item.get('Price') or 0
        status = 'Ordered' if item.get('Ordered') else 'To order'
        html += f"""
          <tr><td>{status}</td><td>{escape_print_text(item['Item'])}</td>
          <td>{escape_print_text(item['Category'])}</td><td>{qty}</td>
          <td>${price:.2f}</td><td>${price * qty:.2f}</td></tr>"""
      html += "</tbody></table>"

    html += "</body></html>"
    win = anvil.js.window.open('', '_blank')
    win.document.write(html)
    win.document.close()

  def refresh_button_click(self, **event_args):
    if self.refresh_list():
      Notification("Shopping list refreshed", style="info", timeout=2).show()
