from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.users
import anvil.server
import plotly.graph_objects as go

class SummaryForm(SummaryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.load_summary_options()
    self.refresh_summary()

  def load_summary_options(self):
    try:
      options = anvil.server.call('get_available_summary_tables')
      if hasattr(self, 'dd_summary_selector'):
        self.dd_summary_selector.items = options
        self.dd_summary_selector.selected_value = 'summary_2025'
    except Exception as e:
      print(f"❌ Error loading summary options: {e}")
      import traceback
      traceback.print_exc()

  def dd_summary_selector_change(self, **event_args):
    self.refresh_summary()

  def refresh_summary(self):
    try:
      selected_table = 'summary_2025'
      if hasattr(self, 'dd_summary_selector') and self.dd_summary_selector.selected_value:
        selected_table = self.dd_summary_selector.selected_value

      data = anvil.server.call('get_spending_summary_by_table', selected_table)

      if data and len(data) > 0 and data[0][0] != "No Data":
        locations = [row[0] for row in data]
        costs = [row[1] for row in data]
        total_spending = sum(costs)

        title_map = {
          'summary_2025': '2025',
          'inventory_summary_total': 'Total',
          'inventory_summary_office': 'Office',
          'inventory_summary_internal': 'Internal',
          'inventory_summary_center': 'Center'
        }
        title_prefix = title_map.get(selected_table, selected_table)

        # Format currency inline
        formatted_costs = [f"${c:,.2f}" for c in costs]
        formatted_total = f"${total_spending:,.2f}"

        self.plot_spending.data = go.Bar(
          x=locations, 
          y=costs,
          marker_color='#2196F3',
          text=formatted_costs,
          textposition='auto',
          hovertemplate='<b>%{x}</b><br>Total: $%{y:,.2f}<extra></extra>'
        )

        self.plot_spending.layout = {
          'title': {
            'text': f"{title_prefix} Spending<br><sup>Total: {formatted_total}</sup>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
          },
          'xaxis': {
            'title': 'Location',
            'tickangle': -45,
            'tickfont': {'size': 11},
            'automargin': True
          },
          'yaxis': {
            'title': 'Cost ($)',
            'tickformat': '$,.0f',
            'tickfont': {'size': 11}
          },
          'plot_bgcolor': '#f5f5f5',
          'paper_bgcolor': 'white',
          'margin': {'t': 100, 'b': 80, 'l': 60, 'r': 20},
          'height': None,
          'showlegend': False,
          'autosize': True,
          'responsive': True
        }

        print(f"Summary refreshed: {len(locations)} locations, {formatted_total} total")

      else:
        self.plot_spending.data = []
        self.plot_spending.layout = {
          'title': "No data available",
          'xaxis': {'visible': False},
          'yaxis': {'visible': False},
          'annotations': [{
            'text': 'No data to display<br><sub>Import an Excel file</sub>',
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'xanchor': 'center',
            'yanchor': 'middle',
            'showarrow': False,
            'font': {'size': 16, 'color': '#999'}
          }],
          'autosize': True,
          'responsive': True
        }

    except Exception as e:
      print(f"❌ Error refreshing summary: {e}")
      import traceback
      traceback.print_exc()

      self.plot_spending.data = []
      self.plot_spending.layout = {
        'title': "Error loading data",
        'xaxis': {'visible': False},
        'yaxis': {'visible': False},
        'annotations': [{
          'text': f'Error: {str(e)}',
          'xref': 'paper',
          'yref': 'paper',
          'x': 0.5,
          'y': 0.5,
          'xanchor': 'center',
          'yanchor': 'middle',
          'showarrow': False,
          'font': {'size': 14, 'color': '#f44336'}
        }],
        'autosize': True,
        'responsive': True
      }

  def btn_refresh_click(self, **event_args):
    """Manual refresh button"""
    self.refresh_summary()
    Notification("Summary refreshed", style="info", timeout=2).show()