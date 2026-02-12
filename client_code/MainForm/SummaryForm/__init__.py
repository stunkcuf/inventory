from ._anvil_designer import SummaryFormTemplate
from anvil import *
import anvil.server

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
        # Prefer 2025 Summary
        for friendly, value in options:
          if '2025' in friendly or value == 'summary_2025':
            self.dd_summary_selector.selected_value = value
            break
        else:
          if options:
            self.dd_summary_selector.selected_value = options[0][1]
    except Exception:
      Notification("Failed to load summary options", style="error", timeout=4).show()

  def dd_summary_selector_change(self, **event_args):
    self.refresh_summary()

  def refresh_summary(self):
    try:
      selected_table = 'summary_2025'
      if hasattr(self, 'dd_summary_selector') and self.dd_summary_selector.selected_value:
        sel = self.dd_summary_selector.selected_value
        selected_table = sel[1] if isinstance(sel, tuple) else sel

      # Get the ready-to-render Plotly figure dict from the server
      fig_dict = anvil.server.call('get_spending_chart_figure', selected_table)

      if not fig_dict or 'data' not in fig_dict or len(fig_dict.get('data', [])) == 0:
        self._show_no_data()
        return

      # Set the figure directly
      self.plot_spending.figure = fig_dict
      print(f"Chart rendered successfully for table: {selected_table}")

    except Exception as e:
      print(f"Error in refresh_summary: {repr(e)}")
      self._show_error(f"Failed to load chart: {str(e)}")

  def _show_no_data(self):
    """Show message when no data is available"""
    empty_fig = {
      "data": [],
      "layout": {
        "title": "No data available",
        "annotations": [{
          "text": "No spending breakdown found<br>Try refreshing or check your import",
          "xref": "paper", "yref": "paper",
          "x": 0.5, "y": 0.5,
          "showarrow": False,
          "font": {"size": 18, "color": "#666"}
        }],
        "xaxis": {"visible": False},
        "yaxis": {"visible": False}
      }
    }
    self.plot_spending.figure = empty_fig

  def _show_error(self, msg="Unknown error"):
    """Show error message in chart"""
    error_fig = {
      "data": [],
      "layout": {
        "title": "Chart Error",
        "annotations": [{
          "text": f"Error: {msg}",
          "xref": "paper", "yref": "paper",
          "x": 0.5, "y": 0.5,
          "showarrow": False,
          "font": {"size": 16, "color": "red"}
        }]
      }
    }
    self.plot_spending.figure = error_fig

  def btn_refresh_click(self, **event_args):
    """Refresh button handler"""
    self.refresh_summary()
    Notification("Summary refreshed", style="success", timeout=2).show()