from ._anvil_designer import AuditLogRowTemplateTemplate
from anvil import *

class AuditLogRowTemplate(AuditLogRowTemplateTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    self.label_timestamp.text = str(self.item.get('timestamp', ''))
    self.label_user.text = self.item.get('user_email', '')
    self.label_action.text = self.item.get('action', '')
    self.label_table.text = self.item.get('table_name', '')
    self.label_item.text = self.item.get('item_name', '')
    self.label_details.text = self.item.get('details', '')

    # Color code by action
    action = self.item.get('action', '')
    if action == 'CREATE':
      self.card_row.background = '#e8f5e9'  # Green
    elif action == 'UPDATE':
      self.card_row.background = '#fff3e0'  # Orange
    elif action == 'DELETE':
      self.card_row.background = '#ffebee'  # Red
    elif action == 'IMPORT':
      self.card_row.background = '#e3f2fd'  # Blue
```


