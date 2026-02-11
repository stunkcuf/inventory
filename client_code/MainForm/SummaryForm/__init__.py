from ._anvil_designer import SummaryFormTemplate
from anvil import *
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
        # Sort alphabetically + show friendly names
        self.dd_summary_selector.items = options
        # Prefer 2025 if available
        defaults = ['summary_2025', '2025 Summary']
        for friendly, value in options:
          if value in defaults or friendly.lower().startswith('2025'):
            self.dd_summary_selector.selected_value = value
            break
        else:
          if options:
            self.dd_summary_selector.selected_value = options[0][1]
    except Exception as e:
      print(f"Error loading summary options: {e}")
      Notification("Failed to load summary options", style="error", timeout=4).show()

  def dd_summary_selector_change(self, **event_args):
    self.refresh_summary()

  def refresh_summary(self):
    try:
      selected_table = 'summary_2025'
      if hasattr(self, 'dd_summary_selector') and self.dd_summary_selector.selected_value:
        # If items are tuples → take the value part
        if isinstance(self.dd_summary_selector.selected_value, tuple):
          selected_table = self.dd_summary_selector.selected_value[1]
        else:
          selected_table = self.dd_summary_selector.selected_value

          # Fetch data — expecting list of [location, gl, po, other]
      raw_data = anvil.server.call('get_spending_summary_by_table', selected_table)

      if not raw_data or len(raw_data) == 0 or raw_data[0][0] in ("No Data", "Error", "Invalid table"):
        self._show_no_data()
        return

        # ────────────────────────────────────────────────
        # Normalize data format
      locations = []
      gls        = []
      pos        = []
      others     = []

      for row in raw_data:
        if isinstance(row, (list, tuple)) and len(row) >= 4:
          loc, gl, po, oth = row[:4]
        elif isinstance(row, dict):
          loc  = row.get('location') or row.get('Location') or "Unknown"
          gl   = row.get('gl') or row.get('GL') or row.get('gl_amt') or 0
          po   = row.get('po') or row.get('PO') or row.get('po_orders') or 0
          oth  = row.get('other') or row.get('Other') or row.get('other_amt') or 0
        else:
          continue  # skip bad rows

        if not loc or loc.strip() == "":
          continue

        locations.append(str(loc).strip())
        gls.append(float(gl or 0))
        pos.append(float(po or 0))
        others.append(float(oth or 0))

      if not locations:
        self._show_no_data()
        return

        # Calculate totals for display
      row_totals    = [g + p + o for g, p, o in zip(gls, pos, others)]
      grand_total   = sum(row_totals)
      formatted_total = f"${grand_total:,.2f}"

      # Title logic
      title_map = {
        'summary_2025': '2025 Spending Breakdown',
        'inventory_summary_total': 'Total Inventory',
        'inventory_summary_office': 'Office Inventory',
        'inventory_summary_internal': 'Internal Inventory',
        'inventory_summary_center': 'Center Inventory'
      }
      title_prefix = title_map.get(selected_table, selected_table.replace('_', ' ').title())

      # ────────────────────────────────────────────────
      # Build stacked bar chart
      fig = go.Figure()

      # GL Amt
      fig.add_trace(go.Bar(
        x=locations,
        y=gls,
        name='GL Amt',
        marker_color='#1976D2',  # strong blue
        text=[f"${v:,.0f}" if v >= 500 else "" for v in gls],  # show text only on bigger bars
        textposition='auto',
        hovertemplate='%{x}<br>GL Amt: $%{y:,.2f}<extra></extra>'
      ))

      # PO Orders
      fig.add_trace(go.Bar(
        x=locations,
        y=pos,
        name='PO Orders',
        marker_color='#388E3C',  # green
        text=[f"${v:,.0f}" if v >= 500 else "" for v in pos],
        textposition='auto',
        hovertemplate='%{x}<br>PO Orders: $%{y:,.2f}<extra></extra>'
      ))

      # Other
      fig.add_trace(go.Bar(
        x=locations,
        y=others,
        name='Other',
        marker_color='#F57C00',  # orange
        text=[f"${v:,.0f}" if v >= 500 else "" for v in others],
        textposition='auto',
        hovertemplate='%{x}<br>Other: $%{y:,.2f}<extra></extra>'
      ))

      fig.update_layout(
        barmode='stack',
        title={
          'text': f"{title_prefix}<br><sup>Total: {formatted_total}</sup>",
          'x': 0.5,
          'xanchor': 'center',
          'font': {'size': 20}
        },
        xaxis={
          'title': 'Location',
          'tickangle': -45,
          'tickfont': {'size': 11},
          'automargin': True
        },
        yaxis={
          'title': 'Amount ($)',
          'tickformat': '$,.0f',
          'gridcolor': '#e0e0e0'
        },
        legend={
          'orientation': 'h',
          'yanchor': 'bottom',
          'y': 1.02,
          'xanchor': 'center',
          'x': 0.5
        },
        hovermode='x unified',           # shows all three values on hover
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='white',
        margin={'t': 110, 'b': 80, 'l': 70, 'r': 30},
        bargap=0.18,
        autosize=True,
        responsive=True
      )

      self.plot_spending.figure = fig

      print(f"Displayed {len(locations)} locations – Total: {formatted_total}")

    except Exception as e:
      print(f"Error refreshing summary chart: {e}")
      import traceback
      traceback.print_exc()
      self._show_error(str(e))

  def _show_no_data(self):
    fig = go.Figure()
    fig.update_layout(
      title="No data available",
      annotations=[{
        'text': 'No breakdown data<br><sub>Check import or table contents</sub>',
        'xref': 'paper', 'yref': 'paper',
        'x': 0.5, 'y': 0.5,
        'showarrow': False,
        'font': {'size': 16, 'color': '#757575'}
      }],
      xaxis={'visible': False},
      yaxis={'visible': False},
      autosize=True
    )
    self.plot_spending.figure = fig

  def _show_error(self, msg):
    fig = go.Figure()
    fig.update_layout(
      title="Error loading data",
      annotations=[{
        'text': f'Error: {msg[:120]}…',
        'xref': 'paper', 'yref': 'paper',
        'x': 0.5, 'y': 0.5,
        'showarrow': False,
        'font': {'size': 14, 'color': '#d32f2f'}
      }],
      xaxis={'visible': False},
      yaxis={'visible': False},
      autosize=True
    )
    self.plot_spending.figure = fig

  def btn_refresh_click(self, **event_args):
    self.refresh_summary()
    Notification("Summary refreshed", style="success", timeout=2).show()