from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Load available summary tables
    self.load_summary_options()

    # Load default summary
    self.refresh_summary()

  def load_summary_options(self):
    """Populate the dropdown with available summary tables"""
    try:
      # Get list of available tables from server
      options = anvil.server.call('get_available_summary_tables')

      # Populate dropdown
      if hasattr(self, 'dd_summary_selector'):
        self.dd_summary_selector.items = options
        # Set default selection to 2025
        self.dd_summary_selector.selected_value = 'summary_2025'
    except Exception as e:
      print(f"Error loading summary options: {e}")

  def dd_summary_selector_change(self, **event_args):
    """Called when user changes the dropdown selection"""
    self.refresh_summary()

  def refresh_summary(self):
    """Load and display spending summary data"""
    try:
      # Get selected table (or default to 2025)
      selected_table = 'summary_2025'
      if hasattr(self, 'dd_summary_selector') and self.dd_summary_selector.selected_value:
        selected_table = self.dd_summary_selector.selected_value

      # Get data from server for the selected table
      data = anvil.server.call('get_spending_summary_by_table', selected_table)

      if data and len(data) > 0 and data[0][0] != "No Data":
        # Unpacking tuples into two lists for the graph
        locations = [row[0] for row in data]
        costs = [row[1] for row in data]

        # Calculate total spending
        total_spending = sum(costs)

        # Extract year/type from table name for title
        title_map = {
          'summary_2025': '2025',
          'inventory_summary_total': 'Total Inventory',
          'inventory_summary_office': 'Office Inventory',
          'inventory_summary_internal': 'Internal Inventory',
          'inventory_summary_center': 'Center Inventory'
        }
        title_prefix = title_map.get(selected_table, selected_table)

        # Update plot
        self.plot_spending.data = go.Bar(
          x=locations, 
          y=costs,
          marker_color='#2196F3',
          text=[f'${cost:,.2f}' for cost in costs],
          textposition='auto',
          hovertemplate='<b>%{x}</b><br>Total: $%{y:,.2f}<extra></extra>'
        )

        # Enhanced layout
        self.plot_spending.layout = {
          'title': {
            'text': f"{title_prefix} Spending by Location (Total: ${total_spending:,.2f})",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
          },
          'xaxis': {
            'title': 'Location',
            'tickangle': -45,
            'tickfont': {'size': 12}
          },
          'yaxis': {
            'title': 'Total Cost ($)',
            'tickformat': '$,.0f',
            'tickfont': {'size': 12}
          },
          'plot_bgcolor': '#f5f5f5',
          'paper_bgcolor': 'white',
          'margin': {'t': 100, 'b': 120, 'l': 80, 'r': 40},
          'height': 500,
          'showlegend': False
        }

        print(f"Summary refreshed: {len(locations)} locations, ${total_spending:,.2f} total ({title_prefix})")

      else:
        # Show empty state
        self.plot_spending.data = []
        self.plot_spending.layout = {
          'title': f"No data available",
          'xaxis': {'visible': False},
          'yaxis': {'visible': False},
          'annotations': [{
            'text': 'No data to display<br><sub>Import an Excel file to see spending data</sub>',
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'xanchor': 'center',
            'yanchor': 'middle',
            'showarrow': False,
            'font': {'size': 20, 'color': '#999'}
          }],
          'height': 500
        }
        print(f"No data found for {selected_table}")

    except Exception as e:
      print(f"Error refreshing summary: {e}")
      import traceback
      traceback.print_exc()

      # Show error state
      self.plot_spending.data = []
      self.plot_spending.layout = {
        'title': "Error loading data",
        'xaxis': {'visible': False},
        'yaxis': {'visible': False},
        'annotations': [{
          'text': f'Error: {str(e)}<br><sub>Check console for details</sub>',
          'xref': 'paper',
          'yref': 'paper',
          'x': 0.5,
          'y': 0.5,
          'xanchor': 'center',
          'yanchor': 'middle',
          'showarrow': False,
          'font': {'size': 16, 'color': '#f44336'}
        }],
        'height': 500
      }

  def btn_refresh_click(self, **event_args):
    """Manual refresh button"""
    self.refresh_summary()
    Notification("Summary refreshed", style="info", timeout=2).show()