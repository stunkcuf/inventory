from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_summary()

  def refresh_summary(self):
    # The 'try' statement MUST be here for the 'except' at the bottom to work
    try:
      data = anvil.server.call('get_spending_summary')

      if data:
        # Unpacking tuples into two lists for the graph
        locations = [row[0] for row in data]
        costs = [row[1] for row in data]

        self.plot_spending.data = [
          go.Bar(
            x=locations, 
            y=costs,
            marker_color='#2196F3' # Gives it a nice professional blue
          )
        ]

        # Optional: update layout
        self.plot_spending.layout.title = "Spending by Location"

        print("Summary data refreshed successfully")
      else:
        print("No summary data found.")

    except Exception as e:
      print(f"Error refreshing summary: {e}")