from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js
from datetime import datetime

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    if hasattr(self, 'drop_down_category'):
      self.drop_down_category.visible = False
    self.refresh_list()

  def refresh_list(self):
    """Refresh the shopping list from server"""
    print("Refreshing shopping list...")
    try:
      anvil.server.call('sync_inventory_status')
      items = anvil.server.call('get_shopping_list')
      self.repeating_panel_1.items = items
      if hasattr(self, 'label_empty'):
        self.label_empty.visible = len(items) == 0
      self.update_summary()
    except Exception as e:
      print(f"Error refreshing list: {e}")

  def update_summary(self):
    """Update summary logic"""
    if hasattr(self, 'label_summary'):
      items = self.repeating_panel_1.items or []
      total_items = len(items)
      ordered_count = sum(1 for item in items if item.get('Ordered', False))
      pending_cost = 0
      for item in items:
        if not item.get('Ordered', False):
          qty = max(0, item.get('Minimum_Amt', 0) - item.get('On_Hand', 0))
          pending_cost += (item.get('Price', 0) * qty)

      self.label_summary.text = f"Total: {total_items} | Est. Cost: ${pending_cost:,.2f} | Ordered: {ordered_count}"

  def print_button_click(self, **event_args):
    """The Professional Look - Indented to fix the Warning"""
    print("Printing professional list...")
    items = self.repeating_panel_1.items
    if not items:
      alert("No items to print!")
      return

    date_str = datetime.now().strftime('%B %d, %Y')

    # This is the professional CSS you liked
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h1 {{ color: #2196F3; border-bottom: 2px solid #2196F3; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #2196F3; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .ordered {{ text-decoration: line-through; color: #999; }}
        @media print {{ .no-print {{ display: none; }} }}
      </style>
    </head>
    <body>
      <h1>Shopping List - {date_str}</h1>
      <button class="no-print" onclick="window.print()" style="padding:10px; cursor:pointer; background:#2196F3; color:white; border:none; border-radius:4px;">🖨️ Print</button>
      <table>
        <tr><th>Item</th><th>Category</th><th>Qty</th><th>Price</th><th>Total</th></tr>
    """

    for item in items:
      qty = max(0, item.get('Minimum_Amt', 0) - item.get('On_Hand', 0))
      price = item.get('Price', 0)
      row_class = 'class="ordered"' if item.get('Ordered', False) else ''
      html += f"""
        <tr {row_class}>
          <td><strong>{item.get('Item', '')}</strong></td>
          <td>{item.get('Category', '')}</td>
          <td>{qty}</td>
          <td>${price:.2f}</td>
          <td>${price * qty:.2f}</td>
        </tr>"""

    html += "</table></body></html>"

    win = anvil.js.window.open('', '_blank')
    win.document.write(html)
    win.document.close()

  def refresh_button_click(self, **event_args):
    """The Refresh Logic - Indented to fix the Warning"""
    print("Refresh button clicked!")
    self.refresh_list()
    Notification("Shopping list refreshed", style="info", timeout=2).show()
