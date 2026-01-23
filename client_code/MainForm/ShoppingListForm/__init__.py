from ._anvil_designer import ShoppingListFormTemplate
from anvil import *
import anvil.server
import anvil.js
from datetime import datetime

class ShoppingListForm(ShoppingListFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Hide the dropdown if you're not using it
    if hasattr(self, 'drop_down_category'):
      self.drop_down_category.visible = False

    self.refresh_list()

  def refresh_list(self):
    """Refresh the shopping list from server"""
    print("Refreshing shopping list...")  # DEBUG

    # Sync inventory status and get fresh list
    resets = anvil.server.call('sync_inventory_status')
    items = anvil.server.call('get_shopping_list')
    self.repeating_panel_1.items = items

    print(f"Loaded {len(items)} items")  # DEBUG

    # Show/hide empty message if it exists
    if hasattr(self, 'label_empty'):
      self.label_empty.visible = len(items) == 0

    # Update summary if it exists
    if hasattr(self, 'label_summary'):
      total_items = len(items)
      total_cost = sum(item.get('Price', 0) for item in items)
      ordered_count = sum(1 for item in items if item.get('Ordered', False))

      self.label_summary.text = (
        f"Total: {total_items} items | "
        f"Est. Cost: ${total_cost:,.2f} | "
        f"Ordered: {ordered_count}"
      )

  def print_button_click(self, **event_args):
    """Print the shopping list"""
    print("Print button clicked")  # DEBUG
    try:
      anvil.js.call_js('addPrintStyles')
    except:
      pass
    anvil.js.window.print()

  def refresh_button_click(self, **event_args):
    """Manual refresh button"""
    print("Refresh button clicked!")  # DEBUG
    self.refresh_list()
    Notification("Shopping list refreshed", style="info", timeout=2).show()