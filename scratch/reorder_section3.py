import os

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Locate Chart Card
chart_start = text.find('<!-- P&L / EQUITY CURVE CHART (2 Cols) -->')
pos_start = text.find('<!-- POSITIONS & TRADES CARD (1 Col, Tabs: Open & Closed) -->')
sec4_start = text.find('<!-- SECTION 4: DECISION LOG & STRATEGY EVENT STREAM -->')

assert chart_start != -1 and pos_start != -1 and sec4_start != -1

chart_raw = text[chart_start:pos_start].strip()
# Find the end of positions card before the grid closing </div>
pos_and_grid = text[pos_start:sec4_start]
# The last </div></div>\n\n    before sec4 closes the grid and section
grid_end_pos = pos_and_grid.rfind('</div>\n    </div>')
pos_raw = pos_and_grid[:grid_end_pos].strip()

# Adjust Chart Card: make it 1 column, compact height, sleek header
new_chart = """<!-- P&L / EQUITY CURVE CHART (1 Col, Compact Companion) -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm lg:col-span-1 flex flex-col justify-between transition-colors">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center space-x-2">
              <span class="has-tooltip inline-flex items-center">
                <span class="text-sm font-bold text-slate-900 dark:text-white">Session Trajectory</span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-left">
                  <strong class="block text-amber-400 font-semibold mb-0.5">Session Performance Curve</strong>
                  Real-time equity and floating basket profit/loss tracked at 1-minute intervals over the last 2 hours.
                </span>
              </span>
              <span id="badge-chart-status" class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">PAUSED</span>
            </div>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-800">
            <span>Equity: <strong id="txt-equity" class="text-emerald-600 dark:text-emerald-400">$0.00</strong></span>
            <span>Free: <strong id="txt-free-margin" class="text-amber-600 dark:text-amber-400">$0.00</strong></span>
          </div>
          <div class="relative flex-1 h-[160px] sm:h-[175px] w-full">
            <canvas id="pnlChart"></canvas>
          </div>
        </div>"""

# Adjust Positions Card: make it 2 columns (wide), expand max-h for tables, ensure type="button" on buttons
new_pos = pos_raw.replace(
    '<!-- POSITIONS & TRADES CARD (1 Col, Tabs: Open & Closed) -->\n        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col transition-colors">',
    '<!-- POSITIONS & TRADES CARD (2 Cols - Wide, Spacious Ledger) -->\n        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm lg:col-span-2 flex flex-col transition-colors">'
)

new_pos = new_pos.replace('max-h-[250px]', 'max-h-[285px]')
new_pos = new_pos.replace('max-h-[220px]', 'max-h-[250px]')

# Add type="button" to history buttons if missing
for p in ['today', '3d', '7d', '30d', 'all']:
    old_btn = f'onclick="setHistoryPeriod(\'{p}\')"'
    new_btn = f'type="button" onclick="setHistoryPeriod(\'{p}\')"'
    new_pos = new_pos.replace(old_btn, new_btn)

new_section3 = new_pos + "\n\n        " + new_chart + "\n\n      </div>\n    </div>\n\n    "

updated_text = text[:chart_start] + new_section3 + text[sec4_start:]

with open('templates/index.html', 'w', encoding='utf-8') as fw:
    fw.write(updated_text)

print("Reordered Section 3 successfully!")

