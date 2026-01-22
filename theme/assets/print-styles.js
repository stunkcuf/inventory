// Print styling for shopping list
function addPrintStyles() {
  // Only add once
  if (document.getElementById('print-styles')) return;

  const style = document.createElement('style');
  style.id = 'print-styles';
  style.textContent = `
    @media print {
      /* Hide navigation and buttons when printing */
      .anvil-role-navigation,
      button,
      .anvil-drop-down,
      .anvil-check-box,
      .anvil-link {
        display: none !important;
      }
      
      /* Show URLs in print */
      a[href]:after {
        content: " (" attr(href) ")";
        font-size: 0.8em;
        color: #666;
      }
      
      /* Better table formatting */
      table {
        width: 100%;
        border-collapse: collapse;
      }
      
      th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
      }
      
      /* Prevent page breaks in middle of rows */
      tr {
        page-break-inside: avoid;
      }
      
      /* Repeat table header on each page */
      thead {
        display: table-header-group;
      }
      
      /* Page margins */
      @page {
        margin: 0.75in;
      }
      
      body {
        font-size: 11pt;
      }
      
      /* Add print header */
      body:before {
        content: "Shopping List - Printed: " attr(data-print-date);
        display: block;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        font-size: 14pt;
      }
    }
  `;
  document.head.appendChild(style);

  // Add current date for print header
  document.body.setAttribute('data-print-date', new Date().toLocaleDateString());
}