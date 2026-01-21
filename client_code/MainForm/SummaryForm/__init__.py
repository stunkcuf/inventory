from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Load the data when the form opens
    self.refresh_summary()

  def refresh_summary(self):
    """This is the function MainForm is looking for"""
    try:
      # Get the list of (Location, Cost) tuples from the server
      summary_data = anvil.server.call('get_spending_summary')

      # If you have a Data Grid/Repeating Panel named 'repeating_panel_summary'
      # self.repeating_panel_summary.items = [{'Location': x[0], 'Total_Cost': x[1]} for x in summary_data]

      # If you are using a Chart (Plotly), you can map the data like this:
      # self.plot_1.data = [
      #   go.Bar(x=[row[0] for row in summary_data], y=[row[1] for row in summary_data])
      # ]

      print("Summary data refreshed successfully")

    except Exception as e:
      print(f"Error refreshing summary: {e}")