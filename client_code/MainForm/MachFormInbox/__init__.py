from ._anvil_designer import MachFormInboxTemplate
from anvil import Button, Label, LinearPanel, Notification, TextArea, alert
import anvil.server
import json


class MachFormInbox(MachFormInboxTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_component(Label(text="Latest 25 submissions from both MachForm forms."))
    refresh = Button(text="Refresh", icon="fa:refresh", role='workspace-button')
    refresh.set_event_handler('click', self.load_submissions)
    self.add_component(refresh)
    self.entries = LinearPanel()
    self.add_component(self.entries)
    self.load_submissions()

  def load_submissions(self, **event_args):
    try:
      submissions = anvil.server.call('get_machform_inbox')
    except Exception as error:
      Notification(f"Could not load the MachForm inbox: {error}", style='danger').show()
      return
    self.entries.clear()
    if not submissions:
      self.entries.add_component(Label(text="No submissions received yet."))
    for submission in submissions:
      card = LinearPanel(role='workspace-surface')
      entry = f" · Entry {submission['entry_id']}" if submission['entry_id'] else ''
      card.add_component(Label(text=f"Form {submission['form_id']}{entry}", bold=True))
      card.add_component(Label(text=f"Received {submission['received_at']}"))
      view = Button(text="View submission", role='workspace-button')
      view.set_event_handler('click', self.details_handler(submission))
      card.add_component(view)
      self.entries.add_component(card)

  def details_handler(self, submission):
    def view_details(**event_args):
      text = submission['payload']
      try:
        text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
      except (ValueError, TypeError):
        pass
      alert(TextArea(text=text, enabled=False, height=320), title="MachForm submission", large=True)
    return view_details
