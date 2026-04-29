from ._anvil_designer import MainFormTemplate
from anvil import *
import anvil.users
import anvil.server
from .InventoryForm import InventoryForm
from ..admin.AdminForm import AdminForm
from .SummaryForm import SummaryForm
from .OrderHistoryForm import OrderHistoryForm
from .ShoppingListForm import ShoppingListForm
from .OrderFillForm import OrderFillForm

class MainForm(MainFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Require login
    self.user = anvil.users.login_with_form()
    if not self.user:
      alert("You must log in to access the inventory system")
      return

    # Check user role with fallback
    try:
      self.user_role = anvil.server.call('get_current_user_role')
    except:
      self.user_role = self.user.get('role', 'staff')
      print(f"Using fallback role check: {self.user_role}")

    # STAFF: Only see Inventory and Order Filling
    if self.user_role != 'admin':
      if hasattr(self, 'link_admin'):
        self.link_admin.visible = False
      if hasattr(self, 'link_summaries'):
        self.link_summaries.visible = False
      if hasattr(self, 'link_shopping_list'):
        self.link_shopping_list.visible = False
      if hasattr(self, 'link_order_history'):
        self.link_order_history.visible = False

    # Welcome message with role
    role_display = self.user_role.title() if self.user_role else "Staff"
    Notification(f"Welcome, {self.user['email']} ({role_display})!", style="info", timeout=3).show()

    self.go_to_inventory()

  def go_to_inventory(self):
    self.content_panel.clear()
    self.content_panel.add_component(InventoryForm())

  @handle("link_inventory", "click")
  def link_inventory_click(self, **event_args):
    self.go_to_inventory()

  @handle("link_admin", "click")
  def link_admin_click(self, **event_args):
    if self.user_role == 'admin':
      self.content_panel.clear()
      self.content_panel.add_component(AdminForm())
    else:
      alert("Admin access required")

  @handle("link_summaries", "click")
  def link_summaries_click(self, **event_args):
    if self.user_role == 'admin':
      self.content_panel.clear()
      self.content_panel.add_component(SummaryForm())
    else:
      alert("Admin access required")

  @handle("link_shopping_list", "click")
  def link_shopping_list_click(self, **event_args):
    if self.user_role == 'admin':
      self.content_panel.clear()
      self.content_panel.add_component(ShoppingListForm())
    else:
      alert("Admin access required")

  @handle("link_order_history", "click")
  def link_order_history_click(self, **event_args):
    if self.user_role == 'admin':
      print("Order History clicked!")
      self.content_panel.clear()
      self.content_panel.add_component(OrderHistoryForm())
    else:
      alert("Admin access required")

  @handle("order_filling", "click")
  def order_filling_click(self, **event_args):
    print("Order Filling clicked!")
    self.content_panel.clear()
    self.content_panel.add_component(OrderFillForm())

  @handle("link_logout", "click")
  def link_logout_click(self, **event_args):
    if confirm("Are you sure you want to logout?"):
      anvil.users.logout()
      anvil.open_form('MainForm')