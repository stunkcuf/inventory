from ._anvil_designer import MainFormTemplate
from anvil import *
import anvil.users
import anvil.server
from .InventoryForm import InventoryForm
from .StockCountsForm import StockCountsForm
from .ReceivingForm import ReceivingForm
from .MachFormInbox import MachFormInbox
from ..admin.AdminForm import AdminForm
from ..admin.AuditViewer import AuditViewer
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

    try:
      self.user_role = anvil.server.call('get_current_user_role')
    except Exception:
      self.user_role = self.user.get('role', 'staff')

    self.admin_links = (self.link_shopping_list, self.link_order_history,
                        self.link_summaries, self.link_admin)
    for link in self.admin_links:
      link.visible = self.user_role == 'admin'
    self.link_receiving.visible = (self.user_role or 'staff') in ('admin', 'staff')
    self.navbar_links.visible = True
    self.link_logout.visible = True
    self.go_to_inventory()

  def show_page(self, form_type, link, heading=None):
    form = form_type()
    self.content_panel.clear()
    self.content_panel.add_component(form)
    self.page_heading.text = heading or ''
    self.page_heading.visible = bool(heading)
    for candidate in (self.link_inventory, self.link_stock_counts, self.order_filling,
                      self.link_receiving, *self.admin_links):
      candidate.role = 'selected' if candidate is link else None

  def show_admin_page(self, form_type, link, heading=None):
    if self.user_role == 'admin':
      self.show_page(form_type, link, heading)
    else:
      alert("Admin access required")

  def go_to_inventory(self):
    self.show_page(InventoryForm, self.link_inventory, "Inventory")

  @handle("link_inventory", "click")
  def link_inventory_click(self, **event_args):
    self.go_to_inventory()

  @handle("link_stock_counts", "click")
  def link_stock_counts_click(self, **event_args):
    self.show_page(StockCountsForm, self.link_stock_counts, "Stock Counts")

  @handle("order_filling", "click")
  def order_filling_click(self, **event_args):
    self.show_page(OrderFillForm, self.order_filling, "Orders")

  @handle("link_shopping_list", "click")
  def link_shopping_list_click(self, **event_args):
    self.show_admin_page(ShoppingListForm, self.link_shopping_list)

  @handle("link_receiving", "click")
  def link_receiving_click(self, **event_args):
    self.show_page(ReceivingForm, self.link_receiving, "Receiving")

  def show_machform_inbox(self):
    self.show_admin_page(MachFormInbox, self.link_admin, "MachForm Inbox")

  @handle("link_order_history", "click")
  def link_order_history_click(self, **event_args):
    self.show_admin_page(OrderHistoryForm, self.link_order_history)

  @handle("link_summaries", "click")
  def link_summaries_click(self, **event_args):
    self.show_admin_page(SummaryForm, self.link_summaries, "Spending summaries")

  @handle("link_admin", "click")
  def link_admin_click(self, **event_args):
    self.show_admin_page(AdminForm, self.link_admin, "Admin")

  def show_audit_logs(self):
    self.show_admin_page(AuditViewer, self.link_admin)

  @handle("link_logout", "click")
  def link_logout_click(self, **event_args):
    if confirm("Log out of Inventory Management?"):
      anvil.users.logout()
      anvil.open_form('MainForm')
