from ._anvil_designer import StockCountsFormTemplate
from anvil import Button, DropDown, FlowPanel, Label, LinearPanel, Notification, TextBox, alert, confirm
import anvil.server


class StockCountsForm(StockCountsFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.data = {'items': [], 'counts': [], 'can_review': False}
    self.page = 0
    self.description = Label(role='workspace-status')
    self.add_component(self.description)
    toolbar = FlowPanel(align='left', role='shopping-list-toolbar')
    self.view = DropDown(items=[
      ('Due for count', 'due'), ('All items', 'all'),
      ('Awaiting review', 'review'), ('Recent counts', 'history'),
    ], selected_value='due')
    self.view.set_event_handler('change', self.reset_view)
    toolbar.add_component(self.view)
    self.search = TextBox(placeholder="Search items or departments")
    self.search.set_event_handler('pressed_enter', self.reset_view)
    toolbar.add_component(self.search)
    search_button = Button(text="Search", icon="fa:search", role='workspace-button')
    search_button.set_event_handler('click', self.reset_view)
    toolbar.add_component(search_button)
    refresh = Button(text="Refresh", icon="fa:refresh", role='workspace-button')
    refresh.set_event_handler('click', self.load_counts)
    toolbar.add_component(refresh)
    self.add_component(toolbar)
    self.results = LinearPanel()
    self.add_component(self.results)
    self.load_counts()

  def load_counts(self, **event_args):
    try:
      self.data = anvil.server.call('get_stock_counts')
    except Exception as error:
      alert(f"Could not load stock counts: {error}")
      return
    interval = self.data['interval_days']
    self.description.text = f"Items are due every {interval} days. Discrepancies go to an admin for review."
    self.render()

  def reset_view(self, **event_args):
    self.page = 0
    self.render()

  def render(self):
    self.results.clear()
    view = self.view.selected_value
    search = (self.search.text or '').strip().lower()
    if view in ('due', 'all'):
      rows = [row for row in self.data['items']
              if view == 'all' or (row['due'] and not row['pending'])]
    else:
      rows = [row for row in self.data['counts']
              if row['review'] == (view == 'review')]
    rows = [row for row in rows if search in f"{row['item']} {row['category'] or ''}".lower()]
    if not rows:
      self.page = 0
      self.results.add_component(Label(text="No items match this view."))
      return

    self.page = min(self.page, (len(rows) - 1) // 20)
    start = self.page * 20
    for row in rows[start:start + 20]:
      card = LinearPanel(role='workspace-surface')
      name = f"{row['item']} · {row['category']}" if row['category'] else row['item']
      card.add_component(Label(text=name, bold=True))
      if view in ('due', 'all'):
        self.add_item_status(card, row)
      else:
        self.add_count_status(card, row)
      self.results.add_component(card)
    if len(rows) > 20:
      pager = FlowPanel(align='left')
      previous = Button(text="Previous", enabled=self.page > 0, role='workspace-button')
      previous.set_event_handler('click', self.previous_page)
      pager.add_component(previous)
      pager.add_component(Label(text=f"{start + 1}–{min(start + 20, len(rows))} of {len(rows)}"))
      next_page = Button(text="Next", enabled=start + 20 < len(rows), role='workspace-button')
      next_page.set_event_handler('click', self.next_page)
      pager.add_component(next_page)
      self.results.add_component(pager)

  def previous_page(self, **event_args):
    self.page -= 1
    self.render()

  def next_page(self, **event_args):
    self.page += 1
    self.render()

  def add_item_status(self, card, row):
    last = row['last_count'] or 'Never counted'
    card.add_component(Label(text=f"On hand: {row['on_hand']} · Last count: {last}"))
    if row['pending']:
      card.add_component(Label(text="Awaiting review"))
      return
    button = Button(text="Record count", role='workspace-primary')
    button.set_event_handler('click', self.count_handler(row))
    card.add_component(button)

  def add_count_status(self, card, row):
    difference = row['counted'] - row['expected']
    card.add_component(Label(text=f"{row['date']} · {row['status']} · Expected {row['expected']} · "
                                  f"Counted {row['counted']} · Difference {difference:+g}"))
    if row['review'] and self.data['can_review']:
      actions = FlowPanel(align='left')
      for label, apply in [('Apply adjustment', True), ('Dismiss for recount', False)]:
        button = Button(text=label, role='workspace-button')
        button.set_event_handler('click', self.review_handler(row, apply))
        actions.add_component(button)
      card.add_component(actions)

  def count_handler(self, row):
    def record_count(sender, **event_args):
      quantity = TextBox(type='number', placeholder="Physical quantity")
      if not alert(quantity, title=f"Count {row['item']}",
                   buttons=[('Save count', True), ('Cancel', False)]):
        return
      sender.enabled = False
      try:
        status = anvil.server.call('submit_stock_count', row['id'], row['on_hand'], quantity.text)
      except Exception as error:
        alert(f"Could not save the count: {error}")
        self.load_counts()
        return
      finally:
        sender.enabled = True
      message = "Count matched and was saved." if status == 'Matched' else "Count saved for admin review."
      Notification(message, style='success').show()
      self.load_counts()
    return record_count

  def review_handler(self, row, apply):
    def review(sender, **event_args):
      message = (f"Set stock for {row['item']} to {row['counted']}?"
                 if apply else f"Dismiss the count for {row['item']} so it can be counted again?")
      if not confirm(message):
        return
      sender.enabled = False
      try:
        anvil.server.call('review_stock_count', row['id'], apply)
      except Exception as error:
        alert(f"Could not review the count: {error}")
        return
      finally:
        sender.enabled = True
      Notification("Stock adjusted." if apply else "Count dismissed.", style='success').show()
      self.load_counts()
    return review
