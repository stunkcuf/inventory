from ._anvil_designer import RowTemplate2Template
from anvil import *
import anvil.users
import anvil.server

class RowTemplate2(RowTemplate2Template):
  def __init__(self, **properties):
    self.init_components(**properties)
    on_hand = self.item.get('On_Hand', 0)
    minimum = self.item.get('Minimum_Amt', 0)
    self.item['To_Order'] = max(0, minimum - on_hand)
    self.refresh_data_bindings()

  def btn_plus_click(self, **event_args):
    """Increment stock with PO# tracking"""
    po_number = anvil.js.window.prompt("Enter PO# for items received:")

    if po_number:
      old_stock = self.item['On_Hand']
      self.item['On_Hand'] += 1
      new_stock = self.item['On_Hand']
      ma = self.item['Minimum_Amt'] or 0
      self.item['To_Order'] = max(0, ma - self.item['On_Hand'])

      # Log to stock_transactions
      try:
        anvil.server.call('log_stock_transaction', 
                          self.item, 
                          change=+1, 
                          po_number=po_number,
                          transaction_type='received')
      except Exception as e:
        print(f"Stock transaction log failed: {e}")

      # Log to audit_logs
      try:
        anvil.server.call('log_audit',
                          action='UPDATE',
                          table_name='inventory',
                          item_name=self.item['Item'],
                          old_value=f"On_Hand: {old_stock}",
                          new_value=f"On_Hand: {new_stock}",
                          details=f"Stock received (PO# {po_number})")
      except Exception as e:
        print(f"Audit log failed: {e}")

      self.refresh_data_bindings()
      Notification(f"✅ Added 1 item (PO# {po_number})", style="success", timeout=2).show()

  def btn_minus_click(self, **event_args):
    """Decrement stock with Requisition# tracking"""
    if self.item['On_Hand'] > 0:
      req_number = anvil.js.window.prompt("Enter Requisition/Request # for items issued:")

      if req_number:
        old_stock = self.item['On_Hand']
        self.item['On_Hand'] -= 1
        new_stock = self.item['On_Hand']
        ma = self.item['Minimum_Amt'] or 0
        self.item['To_Order'] = max(0, ma - self.item['On_Hand'])

        # Log to stock_transactions
        try:
          anvil.server.call('log_stock_transaction', 
                            self.item, 
                            change=-1, 
                            req_number=req_number,
                            transaction_type='issued')
        except Exception as e:
          print(f"Stock transaction log failed: {e}")

        # Log to audit_logs
        try:
          anvil.server.call('log_audit',
                            action='UPDATE',
                            table_name='inventory',
                            item_name=self.item['Item'],
                            old_value=f"On_Hand: {old_stock}",
                            new_value=f"On_Hand: {new_stock}",
                            details=f"Stock issued (Req# {req_number})")
        except Exception as e:
          print(f"Audit log failed: {e}")

        self.refresh_data_bindings()
        Notification(f"✅ Removed 1 item (Req# {req_number})", style="success", timeout=2).show()
    else:
      Notification("⚠️ Cannot remove - stock is already 0", style="warning", timeout=2).show()

  def btn_delete_click(self, **event_args):
    """Delete this row from the database"""
    if confirm(f"Delete {self.item['Item']}?"):
      try:
        anvil.server.call('log_audit',
                          action='DELETE',
                          table_name='inventory',
                          item_name=self.item['Item'],
                          old_value=f"On_Hand: {self.item['On_Hand']}, Min: {self.item['Minimum_Amt']}",
                          new_value=None,
                          details="Item deleted from inventory")
      except Exception as e:
        print(f"Audit log failed: {e}")

      self.item.delete()
      self.parent.raise_event('x-refresh')