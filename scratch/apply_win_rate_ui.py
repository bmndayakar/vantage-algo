import sys

with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. HTML Matrix
html_matrix = '''      <!-- WIN RATE & PERFORMANCE MATRIX (4 KEY HORIZONS) -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-3.5 mb-3.5 sm:mb-4">

        <!-- HORIZON 1: TODAY -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 sm:p-3.5 shadow-sm relative transition-all duration-200 flex flex-col justify-between">
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span class="flex items-center space-x-1.5 font-bold text-slate-800 dark:text-slate-200">
              <span class="text-amber-500">📅</span>
              <span>Today</span>
            </span>
            <span id="txt-stat-today-total" class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">0 Trades</span>
          </div>
          <div class="flex items-baseline justify-between my-1">
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-today-win-pct" class="text-xl sm:text-2xl font-black font-mono tracking-tight text-emerald-600 dark:text-emerald-400">0.0%</span>
              <span class="text-[10px] font-bold text-emerald-600/80 uppercase">Win</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-today-loss-pct" class="text-xs sm:text-sm font-bold font-mono text-rose-500 dark:text-rose-400">0.0%</span>
              <span class="text-[9px] font-semibold text-rose-500/80 uppercase">Loss</span>
            </div>
          </div>
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden flex my-1 border border-slate-200/50 dark:border-slate-700/50">
            <div id="bar-stat-today-win" class="bg-emerald-500 h-full transition-all duration-500" style="width: 0%"></div>
            <div id="bar-stat-today-loss" class="bg-rose-500 h-full transition-all duration-500" style="width: 0%"></div>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between mt-1 pt-1 border-t border-slate-100 dark:border-slate-800">
            <span class="font-bold"><span id="txt-stat-today-wins" class="text-emerald-600 dark:text-emerald-400">0</span>W <span class="text-slate-400 font-normal">/</span> <span id="txt-stat-today-losses" class="text-rose-500">0</span>L</span>
            <span id="txt-stat-today-pnl" class="font-bold text-slate-700 dark:text-slate-300">$0.00</span>
          </div>
        </div>

        <!-- HORIZON 2: YESTERDAY -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 sm:p-3.5 shadow-sm relative transition-all duration-200 flex flex-col justify-between">
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span class="flex items-center space-x-1.5 font-bold text-slate-800 dark:text-slate-200">
              <span class="text-blue-500">⏳</span>
              <span>Yesterday</span>
            </span>
            <span id="txt-stat-yesterday-total" class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">0 Trades</span>
          </div>
          <div class="flex items-baseline justify-between my-1">
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-yesterday-win-pct" class="text-xl sm:text-2xl font-black font-mono tracking-tight text-emerald-600 dark:text-emerald-400">0.0%</span>
              <span class="text-[10px] font-bold text-emerald-600/80 uppercase">Win</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-yesterday-loss-pct" class="text-xs sm:text-sm font-bold font-mono text-rose-500 dark:text-rose-400">0.0%</span>
              <span class="text-[9px] font-semibold text-rose-500/80 uppercase">Loss</span>
            </div>
          </div>
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden flex my-1 border border-slate-200/50 dark:border-slate-700/50">
            <div id="bar-stat-yesterday-win" class="bg-emerald-500 h-full transition-all duration-500" style="width: 0%"></div>
            <div id="bar-stat-yesterday-loss" class="bg-rose-500 h-full transition-all duration-500" style="width: 0%"></div>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between mt-1 pt-1 border-t border-slate-100 dark:border-slate-800">
            <span class="font-bold"><span id="txt-stat-yesterday-wins" class="text-emerald-600 dark:text-emerald-400">0</span>W <span class="text-slate-400 font-normal">/</span> <span id="txt-stat-yesterday-losses" class="text-rose-500">0</span>L</span>
            <span id="txt-stat-yesterday-pnl" class="font-bold text-slate-700 dark:text-slate-300">$0.00</span>
          </div>
        </div>

        <!-- HORIZON 3: THIS WEEK -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 sm:p-3.5 shadow-sm relative transition-all duration-200 flex flex-col justify-between">
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span class="flex items-center space-x-1.5 font-bold text-slate-800 dark:text-slate-200">
              <span class="text-indigo-500">📈</span>
              <span>This Week</span>
            </span>
            <span id="txt-stat-this_week-total" class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">0 Trades</span>
          </div>
          <div class="flex items-baseline justify-between my-1">
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-this_week-win-pct" class="text-xl sm:text-2xl font-black font-mono tracking-tight text-emerald-600 dark:text-emerald-400">0.0%</span>
              <span class="text-[10px] font-bold text-emerald-600/80 uppercase">Win</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-this_week-loss-pct" class="text-xs sm:text-sm font-bold font-mono text-rose-500 dark:text-rose-400">0.0%</span>
              <span class="text-[9px] font-semibold text-rose-500/80 uppercase">Loss</span>
            </div>
          </div>
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden flex my-1 border border-slate-200/50 dark:border-slate-700/50">
            <div id="bar-stat-this_week-win" class="bg-emerald-500 h-full transition-all duration-500" style="width: 0%"></div>
            <div id="bar-stat-this_week-loss" class="bg-rose-500 h-full transition-all duration-500" style="width: 0%"></div>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between mt-1 pt-1 border-t border-slate-100 dark:border-slate-800">
            <span class="font-bold"><span id="txt-stat-this_week-wins" class="text-emerald-600 dark:text-emerald-400">0</span>W <span class="text-slate-400 font-normal">/</span> <span id="txt-stat-this_week-losses" class="text-rose-500">0</span>L</span>
            <span id="txt-stat-this_week-pnl" class="font-bold text-slate-700 dark:text-slate-300">$0.00</span>
          </div>
        </div>

        <!-- HORIZON 4: THIS MONTH -->
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3 sm:p-3.5 shadow-sm relative transition-all duration-200 flex flex-col justify-between">
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span class="flex items-center space-x-1.5 font-bold text-slate-800 dark:text-slate-200">
              <span class="text-purple-500">🗓️</span>
              <span>This Month</span>
            </span>
            <span id="txt-stat-this_month-total" class="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">0 Trades</span>
          </div>
          <div class="flex items-baseline justify-between my-1">
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-this_month-win-pct" class="text-xl sm:text-2xl font-black font-mono tracking-tight text-emerald-600 dark:text-emerald-400">0.0%</span>
              <span class="text-[10px] font-bold text-emerald-600/80 uppercase">Win</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span id="txt-stat-this_month-loss-pct" class="text-xs sm:text-sm font-bold font-mono text-rose-500 dark:text-rose-400">0.0%</span>
              <span class="text-[9px] font-semibold text-rose-500/80 uppercase">Loss</span>
            </div>
          </div>
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden flex my-1 border border-slate-200/50 dark:border-slate-700/50">
            <div id="bar-stat-this_month-win" class="bg-emerald-500 h-full transition-all duration-500" style="width: 0%"></div>
            <div id="bar-stat-this_month-loss" class="bg-rose-500 h-full transition-all duration-500" style="width: 0%"></div>
          </div>
          <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between mt-1 pt-1 border-t border-slate-100 dark:border-slate-800">
            <span class="font-bold"><span id="txt-stat-this_month-wins" class="text-emerald-600 dark:text-emerald-400">0</span>W <span class="text-slate-400 font-normal">/</span> <span id="txt-stat-this_month-losses" class="text-rose-500">0</span>L</span>
            <span id="txt-stat-this_month-pnl" class="font-bold text-slate-700 dark:text-slate-300">$0.00</span>
          </div>
        </div>

      </div>\n'''

target_sec3_grid = '      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5">\n        \n        <!-- POSITIONS & TRADES CARD'
if target_sec3_grid not in content:
    print("Could not find target_sec3_grid")
    sys.exit(1)

content = content.replace(target_sec3_grid, html_matrix + target_sec3_grid)

# 2. Update subtitle of Section 3
old_subtitle = '<span class="text-[11px] text-slate-400 dark:text-slate-500 font-mono">Session Trajectory &bull; Open &amp; Closed Leg Audit</span>'
new_subtitle = '<span class="text-[11px] text-slate-400 dark:text-slate-500 font-mono">Win/Loss Matrix &bull; Session Trajectory &bull; Leg Audit</span>'
if old_subtitle in content:
    content = content.replace(old_subtitle, new_subtitle)

# 3. Hook updateWinRateMatrix in updateDashboard
hook_target = '      if (s.history_period) {\n        updateHistoryPeriodButtons(s.history_period);\n      }'
hook_replacement = '''      if (s.history_period) {
        updateHistoryPeriodButtons(s.history_period);
      }

      // Win Rate & Performance Matrix
      if (s.win_rate_stats) {
        updateWinRateMatrix(s.win_rate_stats);
      }'''

if hook_target not in content:
    print("Could not find hook_target")
    sys.exit(1)

content = content.replace(hook_target, hook_replacement)

# 4. Add updateWinRateMatrix JS function
js_function = '''
    function updateWinRateMatrix(stats) {
      if (!stats) return;
      const periods = ['today', 'yesterday', 'this_week', 'this_month'];
      periods.forEach(p => {
        const item = stats[p];
        if (!item) return;
        const total = item.total || 0;
        const wins = item.wins || 0;
        const losses = item.losses || 0;
        const winPct = (item.win_pct !== undefined ? item.win_pct : 0.0).toFixed(1);
        const lossPct = (item.loss_pct !== undefined ? item.loss_pct : 0.0).toFixed(1);
        const pnl = item.pnl || 0.0;

        const totalEl = document.getElementById(`txt-stat-${p}-total`);
        const winPctEl = document.getElementById(`txt-stat-${p}-win-pct`);
        const lossPctEl = document.getElementById(`txt-stat-${p}-loss-pct`);
        const winsEl = document.getElementById(`txt-stat-${p}-wins`);
        const lossesEl = document.getElementById(`txt-stat-${p}-losses`);
        const barWinEl = document.getElementById(`bar-stat-${p}-win`);
        const barLossEl = document.getElementById(`bar-stat-${p}-loss`);
        const pnlEl = document.getElementById(`txt-stat-${p}-pnl`);

        if (totalEl) totalEl.innerText = `${total} Trades`;
        if (winPctEl) winPctEl.innerText = `${winPct}%`;
        if (lossPctEl) lossPctEl.innerText = `${lossPct}%`;
        if (winsEl) winsEl.innerText = wins;
        if (lossesEl) lossesEl.innerText = losses;
        if (barWinEl) barWinEl.style.width = `${winPct}%`;
        if (barLossEl) barLossEl.style.width = `${lossPct}%`;
        if (pnlEl) {
          pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
          pnlEl.className = pnl >= 0 ? 'font-bold text-emerald-600 dark:text-emerald-400' : 'font-bold text-rose-600 dark:text-rose-400';
        }
      });
    }
'''

target_btn_func = '    function updateHistoryPeriodButtons(activePeriod) {'
if target_btn_func not in content:
    print("Could not find target_btn_func")
    sys.exit(1)

content = content.replace(target_btn_func, js_function + '\n' + target_btn_func)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("templates/index.html updated successfully!")

