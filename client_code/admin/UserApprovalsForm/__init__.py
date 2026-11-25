from ._anvil_designer import UserApprovalsFormTemplate
from anvil import Button, DropDown, FlowPanel, Label, LinearPanel, Notification, confirm
import anvil.server


class UserApprovalsForm(UserApprovalsFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.page = 0
    controls = FlowPanel(align='left', role='shopping-list-toolbar')
    self.view = DropDown(items=[('Pending', 'pending'), ('Declined', 'declined')],
                         selected_value='pending')
    self.view.set_event_handler('change', self.change_view)
    controls.add_component(self.view)
    refresh = Button(text='Refresh', icon='fa:refresh', role='workspace-button')
    refresh.set_event_handler('click', self.load_requests)
    controls.add_component(refresh)
    self.add_component(controls)
    self.requests = LinearPanel()
    self.add_component(self.requests)
    self.load_requests()

  def change_view(self, **event_args):
    self.page = 0
    self.load_requests()

  def load_requests(self, **event_args):
    view = self.view.selected_value
    try:
      data = anvil.server.call('list_signup_requests', view, self.page)
    except Exception as error:
      Notification(f"Could not load sign-ups: {error}", style='danger').show()
      return
    self.page = data['page']
    self.requests.clear()
    for request in data['requests']:
      self.add_request(request, view)

    if not data['requests']:
      self.requests.add_component(Label(text=f"No {view} sign-ups."))
    elif data['total'] > data['page_size']:
      page_size = data['page_size']
      start = self.page * page_size
      pager = FlowPanel(align='left')
      previous = Button(text="Previous", enabled=self.page > 0, role='workspace-button')
      previous.set_event_handler('click', self.previous_page)
      pager.add_component(previous)
      pager.add_component(Label(text=f"{start + 1}–{min(start + page_size, data['total'])} of {data['total']}"))
      next_page = Button(text="Next", enabled=start + page_size < data['total'], role='workspace-button')
      next_page.set_event_handler('click', self.next_page)
      pager.add_component(next_page)
      self.requests.add_component(pager)

  def previous_page(self, **event_args):
    self.page -= 1
    self.load_requests()

  def next_page(self, **event_args):
    self.page += 1
    self.load_requests()

  def add_request(self, request, view):
    card = LinearPanel(role='workspace-surface')
    card.add_component(Label(text=request['email'], bold=True))
    confirmed = 'Yes' if request['confirmed_email'] else 'No'
    signed_up = request['signed_up']
    date = signed_up.date().isoformat() if signed_up else 'Unknown'
    card.add_component(Label(text=f"Signed up {date} · Email confirmed: {confirmed}"))
    controls = FlowPanel(align='left')
    role = DropDown(items=[('Staff', 'staff'), ('Admin', 'admin')], selected_value='staff',
                    tooltip='Role to assign if approved')
    controls.add_component(role)
    approve = Button(text="Approve", role='workspace-primary')
    decline = Button(text="Decline", role='workspace-danger')

    def review(approved):
      if approved:
        message = f"Enable {request['email']} as {role.selected_value.title()}?"
        if not request['confirmed_email']:
          message += " They will still need to confirm their email before signing in."
      else:
        message = f"Decline access for {request['email']}?"
      if not confirm(message):
        return
      approve.enabled = decline.enabled = False
      try:
        anvil.server.call('review_signup_request', request['id'], approved, role.selected_value, view)
      except Exception as error:
        Notification(f"Could not update the request: {error}", style='danger').show()
        return
      finally:
        approve.enabled = decline.enabled = True
      Notification("User approved." if approved else "Request declined.", style='success').show()
      self.load_requests()

    approve.set_event_handler('click', lambda **event_args: review(True))
    decline.set_event_handler('click', lambda **event_args: review(False))
    controls.add_component(approve)
    if view == 'pending':
      controls.add_component(decline)
    card.add_component(controls)
    self.requests.add_component(card)
