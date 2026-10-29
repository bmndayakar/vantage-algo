with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add modal inputs right after cfg-max_spread
target_max_spread = '''              <input type="number" step="0.1" id="cfg-max_spread" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white" placeholder="e.g. 1.0 (0=Off)">
            </div>'''

lever2_modal_inputs = '''              <input type="number" step="0.1" id="cfg-max_spread" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white" placeholder="e.g. 0.50 (0=Off)">
            </div>
            <div>
              <label class="block text-slate-700 dark:text-slate-300 font-medium mb-1 has-tooltip">
                <span>Spread Spike Mult (&times; Baseline)</span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-left">
                  <strong class="block text-amber-400 font-semibold mb-0.5">Anti-News Spread Spike Gate</strong>
                  Blocks entry if the live spread expands beyond N times the rolling 30-tick baseline (e.g. 2.0&times; during sudden liquidity evaporation or news releases).
                </span>
              </label>
              <input type="number" step="0.5" id="cfg-spread_spike_mult" class="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-white" placeholder="default 2.0 (0=Off)">
            </div>

            <!-- Rollover Blackout Window (IST) -->
            <div class="sm:col-span-2 p-3 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="text-base">🌙</span>
                  <div>
                    <span class="text-xs font-bold text-slate-800 dark:text-slate-200">Midnight Rollover Blackout Window (IST)</span>
                    <span class="block text-[10px] text-slate-500 dark:text-slate-400">Strictly blocks new entries during broker rollover when spreads spike 10&times;&ndash;50&times;</span>
                  </div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" id="cfg-rollover_blackout" class="sr-only peer" checked>
                  <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Blackout Start (IST)</label>
                  <input type="text" id="cfg-rollover_start_ist" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="02:15">
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Blackout End (IST)</label>
                  <input type="text" id="cfg-rollover_end_ist" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="03:30">
                </div>
              </div>
            </div>

            <!-- Dynamic ATR Volatility Scaling & Max ATR Ceiling -->
            <div class="sm:col-span-2 p-3 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/40">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="text-base">⚡</span>
                  <div>
                    <span class="text-xs font-bold text-slate-800 dark:text-slate-200">Lever 2: Dynamic ATR Volatility Grid Adaptation</span>
                    <span class="block text-[10px] text-slate-500 dark:text-slate-400">Automatically widens grid spacing during elevated volatility; blocks entries on extreme ATR</span>
                  </div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" id="cfg-atr_grid_scaling" class="sr-only peer" checked>
                  <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-600"></div>
                </label>
              </div>
              <div class="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">ATR Grid Multiplier</label>
                  <input type="number" step="0.1" id="cfg-atr_grid_mult" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="default 1.5">
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Max ATR Climax Ceiling ($)</label>
                  <input type="number" step="0.5" id="cfg-max_atr" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="e.g. 8.0 (0=Off)">
                </div>
              </div>
            </div>'''

# normalize CRLF
h_norm = html.replace("\r\n", "\n")
t_norm = target_max_spread.replace("\r\n", "\n")
r_norm = lever2_modal_inputs.replace("\r\n", "\n")

if t_norm in h_norm:
    h_norm = h_norm.replace(t_norm, r_norm)
    print("Added Lever 2 modal inputs to index.html")
else:
    print("target_max_spread not found in index.html")

# 2. Add Lever 2 fields to saveConfig
target_save_cfg = "        max_spread: parseFloat(document.getElementById('cfg-max_spread').value) || 0.0,"
replacement_save_cfg = """        max_spread: parseFloat(document.getElementById('cfg-max_spread').value) || 0.0,
        rollover_blackout: document.getElementById('cfg-rollover_blackout') ? document.getElementById('cfg-rollover_blackout').checked : true,
        rollover_start_ist: document.getElementById('cfg-rollover_start_ist')?.value || '02:15',
        rollover_end_ist: document.getElementById('cfg-rollover_end_ist')?.value || '03:30',
        spread_spike_mult: parseFloat(document.getElementById('cfg-spread_spike_mult')?.value) || 2.0,
        atr_grid_scaling: document.getElementById('cfg-atr_grid_scaling') ? document.getElementById('cfg-atr_grid_scaling').checked : true,
        atr_grid_mult: parseFloat(document.getElementById('cfg-atr_grid_mult')?.value) || 1.5,
        max_atr: parseFloat(document.getElementById('cfg-max_atr')?.value) || 0.0,"""

t_save = target_save_cfg.replace("\r\n", "\n")
r_save = replacement_save_cfg.replace("\r\n", "\n")

if t_save in h_norm:
    h_norm = h_norm.replace(t_save, r_save)
    print("Added Lever 2 fields to saveConfig in index.html")
else:
    print("target_save_cfg not found in index.html")

# 3. In updateUI, handle spread wide styling in Card 1
target_spread_ui = "document.getElementById('txt-spread').innerText = `$${s.last_tick.spread.toFixed(2)}`;"
replacement_spread_ui = """const sprEl = document.getElementById('txt-spread');
        if (sprEl) {
          sprEl.innerText = `$${s.last_tick.spread.toFixed(2)}`;
          const maxSpr = (s.config && s.config.max_spread) ? s.config.max_spread : 0.50;
          if (maxSpr > 0 && s.last_tick.spread > maxSpr) {
            sprEl.className = 'text-rose-600 dark:text-rose-400 font-black animate-pulse';
            sprEl.title = `Spread $${s.last_tick.spread.toFixed(2)} exceeds Max $${maxSpr.toFixed(2)}! Entries blocked.`;
          } else {
            sprEl.className = 'text-amber-600 dark:text-amber-400 font-bold';
            sprEl.title = 'Normal spread';
          }
        }"""

t_spr = target_spread_ui.replace("\r\n", "\n")
r_spr = replacement_spread_ui.replace("\r\n", "\n")

if t_spr in h_norm:
    h_norm = h_norm.replace(t_spr, r_spr)
    print("Added dynamic spread alert styling to updateUI in index.html")
else:
    print("target_spread_ui not found in index.html")

with open("templates/index.html", "w", encoding="utf-8", newline="") as f:
    f.write(h_norm.replace("\n", "\r\n"))

print("index.html successfully updated!")

