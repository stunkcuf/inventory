from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js
from datetime import datetime
from .helpers import (
calculate_list_totals, 
calculate_quantity_needed,
format_currency,
show_info,
log_error
)

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    if hasattr(self, 'drop_down_category'):
      self.drop_down_category.visible = False

    self.refresh_list()

  def refresh_list(self):
    """Refresh the shopping list from server"""
    print("Refreshing shopping list...")

    resets = anvil.server.call('sync_inventory_status')
    items = anvil.server.call('get_shopping_list')
    self.repeating_panel_1.items = items

    print(f"Loaded {len(items)} items")

    if hasattr(self, 'label_empty'):
      self.label_empty.visible = len(items) == 0

    self.update_summary()

  def update_summary(self):
    """Update summary using helper calculations"""
    if hasattr(self, 'label_summary'):
      items = self.repeating_panel_1.items
      stats = calculate_list_totals(items)

      self.label_summary.text = (
        f"Total: {stats['total_items']} items | "
        f"Est. Cost: {format_currency(stats['pending_cost'])} | "
        f"Ordered: {stats['ordered_count']} | "
        f"Pending: {stats['pending_count']}"
      )

  def print_button_click(self, **event_args):
    """Print ALL shopping list items"""
    print("Print button clicked")

    try:
      items = self.repeating_panel_1.items

      if not items or len(items) == 0:
        alert("No items to print!")
        return

      stats = calculate_list_totals(items)

      html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Shopping List</title>
  <style>
    body {{ 
      font-family: Arial, sans-serif; 
      padding: 20px;
      max-width: 100%;
    }}
    h1 {{ 
      color: #2196F3; 
      border-bottom: 2px solid #2196F3;
      padding-bottom: 10px;
    }}
    .info {{ 
      background: #f0f0f0; 
      padding: 10px; 
      margin: 15px 0;
    }}
    table {{ 
      width: 100%; 
      border-collapse: collapse; 
      margin-top: 20px;
    }}
    th {{ 
      background: #2196F3; 
      color: white; 
      padding: 10px; 
      text-align: left;
    }}
    td {{ 
      padding: 8px; 
      border-bottom: 1px solid #ddd;
    }}
    tr:hover {{ background: #f5f5f5; }}
    .ordered {{ 
      text-decoration: line-through; 
      color: #999; 
    }}
    @media print {{
      body {{ padding: 10px; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <h1>Shopping List - {datetime.now().strftime('%B %d, %Y')}</h1>
  
  <div class="info">
    <strong>Total Items:</strong> {stats['total_items']} | 
    <strong>Est. Cost:</strong> {format_currency(stats['total_cost'])} | 
    <strong>Pending:</strong> {stats['pending_count']}
  </div>
  
  <button class="no-print" onclick="window.print()" style="padding: 10px 20px; font-size: 16px; margin-bottom: 10px;">
    🖨️ Print
  </button>
  
  <table>
    <tr>
      <th style="width: 5%;">☐</th>
      <th style="width: 35%;">Item</th>
      <th style="width: 15%;">Category</th>
      <th style="width: 10%;">Qty</th>
      <th style="width: 10%;">Unit Price</th>
      <th style="width: 15%;">Total</th>
      <th style="width: 10%;">Status</th>
    </tr>
"""

      for item in items:
        on_hand = item.get('On_Hand', 0)
        min_amt = item.get('Minimum_Amt', 0)
        qty = calculate_quantity_needed(on_hand, min_amt)
        price = item.get('Price', 0)
        item_total = price * qty
        ordered = item.get('Ordered', False)

        check = '☑' if ordered else '☐'
        status = 'Ordered' if ordered else 'Pending'
        row_class = 'ordered' if ordered else ''

        html += f"""
    <tr class="{row_class}">
      <td style="text-align: center; font-size: 16px;">{check}</td>
      <td><strong>{item.get('Item', '')}</strong></td>
      <td>{item.get('Category', '')}</td>
      <td style="text-align: center;"><strong>{qty}</strong></td>
      <td>${price:.2f}</td>
      <td><strong>${item_total:.2f}</strong></td>
      <td>{status}</td>
    </tr>
"""

      html += """
  </table>
</body>
</html>
"""

      win = anvil.js.window.open('', '_blank')
      win.document.write(html)
      win.document.close()

    except Exception as e:
      log_error("print_button_click", e)
      alert(f"Error: {str(e)}")

  def refresh_button_click(self, **event_args):
    """Manual refresh button"""
    print("Refresh button clicked!")
    self.refresh_list()
    show_info("Shopping list refreshed")