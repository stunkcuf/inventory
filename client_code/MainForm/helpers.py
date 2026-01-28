from anvil import Notification

CATEGORIES = ["Office", "Center"]

CATEGORY_DROPDOWN_ITEMS = [
  ("All Inventory", "All"), 
  ("Center", "Center"), 
  ("Office", "Office")
]

def show_info(message, timeout=2):
  Notification(message, style="info", timeout=timeout).show()

def show_success(message, timeout=2):
  Notification(message, style="success", timeout=timeout).show()

def show_error(message, timeout=5):
  Notification(message, style="danger", timeout=timeout).show()

def show_warning(message, timeout=3):
  Notification(message, style="warning", timeout=timeout).show()

def setup_category_dropdown(dropdown, include_all=True):
  if include_all:
    dropdown.items = CATEGORY_DROPDOWN_ITEMS
  else:
    dropdown.items = [(cat, cat) for cat in CATEGORIES]

def log_error(context, exception):
  print(f"Error in {context}: {exception}")

def format_currency(amount):
  if amount is None or amount == 0:
    return "$0.00"
  return f"${amount:,.2f}"

def calculate_quantity_needed(on_hand, min_amt):
  return max(0, min_amt - on_hand)

def calculate_item_cost(item):
  price = item.get('Price', 0)
  on_hand = item.get('On_Hand', 0)
  min_amt = item.get('Minimum_Amt', 0)
  qty_needed = calculate_quantity_needed(on_hand, min_amt)
  return price * qty_needed

def calculate_list_totals(items):
  total_items = len(items)
  ordered_count = sum(1 for item in items if item.get('Ordered', False))
  pending_count = total_items - ordered_count

  total_cost = sum(calculate_item_cost(item) for item in items)
  pending_cost = sum(
    calculate_item_cost(item) 
    for item in items 
    if not item.get('Ordered', False)
  )

  return {
    'total_items': total_items,
    'ordered_count': ordered_count,
    'pending_count': pending_count,
    'total_cost': total_cost,
    'pending_cost': pending_cost
  }