from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_charts()

  def refresh_charts(self):
    categories, amounts = anvil.server.call('get_spending_summary')
    self.plot_spending.data = go.Pie(labels=categories, values=amounts, hole=0.4)
    self.plot_spending.layout.title = "2025 Spending Overview"