from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js
from datetime import datetime

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Hide category dropdown if it exists on your form
    if hasattr(self, 'drop_down_category'):
      self.drop_down_category.visible = False

    self.refresh_list()

  def refresh_list(self):
    """Refresh the shopping list from server"""
    print("Refreshing shopping list...")
    try:
      # Syncing inventory status and getting the list
      # These functions must be @anvil.server.callable in your ServerModule
      anvil.server.call('sync_inventory_status')
      items = anvil.server.call('get_shopping_list')
      self.repeating_panel_1.items = items

      if hasattr(self, 'label_empty'):
        self.label_empty.visible = len(items) == 0

      self.update_summary()
      print(f"Loaded {len(items)} items")
    except Exception as e:
      print(f"Error refreshing list: {e}")

  def update_summary(self):
    """Update summary from current items"""
    if hasattr(self, 'label_summary'):
      items = self.repeating_panel_1.items or []

      total_items = len(items)
      ordered_count = sum(1 for item in items if item.get('Ordered', False))
      pending_count = total_items - ordered_count

      pending_cost = 0
      for item in items:
        if not item.get('Ordered', False):
          price = item.get('Price', 0)
          on_hand = item.get('On_Hand', 0)
          min_amt = item.get('Minimum_Amt', 0)
          qty_needed = max(0, min_amt - on_hand)
          pending_cost += (price * qty_needed)

      self.label_summary.text = (
        f"Total: {total_items} items | "
        f"Est. Cost: ${pending_cost:,.2f} | "
        f"Ordered: {ordered_count} | "
        f"Pending: {pending_count}"
      )

  def print_button_click(self, **event_args):
    """Print ALL shopping list items - Fixed for blank page issues"""
    print("Print button clicked")

    try:
      items = self.repeating_panel_1.items
      if not items or len(items) == 0:
        alert("No items to print!")
        return

      # Prepare data summary
      total_items = len(items)
      total_cost = sum(item.get('Price', 0) * max(0, item.get('Minimum_Amt', 0) - item.get('On_Hand', 0)) for item in items)
      pending = sum(1 for item in items if not item.get('Ordered', False))
      current_date = datetime.now().strftime('%B %d, %Y')

      # Build HTML
      html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Shopping List - {current_date}</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
    h1 {{ color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }}
    .info {{ background: #f0f0f0; padding: 10px; margin: 15px 0; border-radius: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th {{ background: #2196F3; color: white; padding: 12px 8px; text-align: left; }}
    td {{ padding: 10px 8px; border-bottom: 1px solid #ddd; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    .ordered {{ text-decoration: line-through; color: #999; }}
    @media print {{ .no-print {{ display: none; }} body {{ padding: 0; }} }}
  </style>
</head>
<body>
  <h1>Shopping List</h1>
  <div class="info">
    <strong>Date:</strong> {current_date} | 
    <strong>Total Items:</strong> {total_items} | 
    <strong>Est. Cost:</strong> ${total_cost:,.2f} | 
    <strong>Pending:</strong> {pending}
  </div>
  <button class="no-print" onclick="window.print()" style="padding: 10px 20px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-bottom: 20px;">
    🖨️ Click to Print
  </button>
  <table>
    <thead>
      <tr>
        <th>Status</th>
        <th>Item</th>
        <th>Category</th>
        <th>Qty Needed</th>
        <th>Price</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
"""
      for item in items:
        qty = max(0, item.get('Minimum_Amt', 0) - item.get('On_Hand', 0))
        price = item.get('Price', 0)
        ordered = item.get('Ordered', False)
        row_class = 'ordered' if ordered else ''
        check = '☑' if ordered else '☐'

        html += f"""
      <tr class="{row_class}">
        <td style="text-align: center;">{check}</td>
        <td><strong>{item.get('Item', '')}</strong></td>
        <td>{item.get('Category', '')}</td>
        <td>{qty}</td>
        <td>${price:.2f}</td>
        <td>${price * qty:.2f}</td>
      </tr>"""

      html += """
    </tbody>
  </table>
</body>
</html>
"""

      # Opening and writing to the window
      win = anvil.js.window.open('', '_blank')
      if win:
        win.document.open() # Explicitly open the stream
        win.document.write(html)
        win.document.close() # Explicitly close the stream
        win.focus() # Bring to front
      else:
        alert("Pop-up blocked! Please check your browser's address bar and 'Always Allow' popups for this app.")

    except Exception as e:
      print(f"❌ Print error: {e}")
      alert(f"Error generating print view: {str(e)}")

  def refresh_button_click(self, **event_args):
    """Manual refresh button handler"""
    print("Refresh button clicked!")
    self.refresh_list()
    Notification("Shopping list refreshed", style="info", timeout=2).show()