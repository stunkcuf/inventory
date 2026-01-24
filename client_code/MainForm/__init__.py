from ._anvil_designer import MainFormTemplate
from anvil import *
import anvil.server
from .InventoryForm import InventoryForm
from .AdminForm import AdminForm
from .SummaryForm import SummaryForm
from .OrderHistoryForm import OrderHistoryForm
from .ShoppingListForm import ShoppingListForm
from .OrderFillForm import OrderFillForm

class MainForm(MainFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.go_to_inventory()

  def go_to_inventory(self):
    self.content_panel.clear()
    self.content_panel.add_component(InventoryForm())

  @handle("link_inventory", "click")
  def link_inventory_click(self, **event_args):
    self.go_to_inventory()

  @handle("link_admin", "click")
  def link_admin_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(AdminForm())

  @handle("link_summaries", "click")
  def link_summaries_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(SummaryForm())

  @handle("link_shopping_list", "click")
  def link_shopping_list_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(ShoppingListForm())

  @handle("link_order_history", "click")
  def link_order_history_click(self, **event_args):
    print("Order History clicked!")
    self.content_panel.clear()
    self.content_panel.add_component(OrderHistoryForm())

  @handle("order_filling", "click")
  def order_filling_click(self, **event_args):
    print("Order Filling clicked!")  # DEBUG
    self.content_panel.clear()
    self.content_panel.add_component(OrderFillForm())