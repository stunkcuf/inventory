from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.refresh_summary()

  def refresh_summary(self):
    try:
      data = anvil.server.call('get_spending_summary')
      if data and len(data) > 0:
        # Unpacking tuples into two lists for the graph
        locations = [row[0] for row in data]
        costs = [row[1] for row in data]

        # Calculate total spending
        total_spending = sum(costs)

        # Update plot
        self.plot_spending.data = [
          go.Bar(
            x=locations, 
            y=costs,
            marker_color='#2196F3',  # Professional blue
            text=[f'${cost:,.2f}' for cost in costs],  # Show $ amounts on bars
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Total: $%{y:,.2f}<extra></extra>'
          )
        ]

        # Enhanced layout
        self.plot_spending.layout = go.Layout(
          title={
            'text': f"Spending by Location (Total: ${total_spending:,.2f})",
            'x': 0.5,
            'xanchor': 'center'
          },
          xaxis={
            'title': 'Location',
            'tickangle': -45  # Angle labels for better readability
          },
          yaxis={
            'title': 'Total Cost ($)',
            'tickformat': '$,.0f'  # Format as currency
          },
          plot_bgcolor='#f5f5f5',
          margin={'t': 80, 'b': 120, 'l': 80, 'r': 40},
          height=500
        )

        print(f"Summary refreshed: {len(locations)} locations, ${total_spending:,.2f} total")
      else:
        # Show empty state
        self.plot_spending.data = []
        self.plot_spending.layout = go.Layout(
          title="No spending data available",
          annotations=[{
            'text': 'No data to display',
            'xref': 'paper',
            'yref': 'paper',
            'showarrow': False,
            'font': {'size': 20, 'color': '#999'}
          }]
        )
        print("No summary data found.")

    except Exception as e:
      print(f"Error refreshing summary: {e}")
      # Show error state
      self.plot_spending.data = []
      self.plot_spending.layout = go.Layout(
        title="Error loading data",
        annotations=[{
          'text': f'Error: {str(e)}',
          'xref': 'paper',
          'yref': 'paper',
          'showarrow': False,
          'font': {'size': 16, 'color': '#f44336'}
        }]
      )