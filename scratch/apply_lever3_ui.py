import os

file_path = "templates/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add HTF badge in Card 1 Market Slate
old_card1_rsi = """              <span class="text-slate-500 dark:text-slate-400 has-tooltip inline-flex items-center">
                <span>RSI: <span id="txt-rsi" class="font-mono font-bold text-slate-900 dark:text-white">50.0</span></span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">RSI-14 Momentum Oscillator</strong>
                  Momentum filter. Blocks BUY when &ge; 70 (Overbought climax) and blocks SELL when &le; 30 (Oversold floor).
                </span>
              </span>"""

new_card1_rsi = """              <span class="text-slate-500 dark:text-slate-400 has-tooltip inline-flex items-center">
                <span>RSI: <span id="txt-rsi" class="font-mono font-bold text-slate-900 dark:text-white">50.0</span></span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">RSI-14 Momentum Oscillator</strong>
                  Momentum filter. Blocks BUY when &ge; 70 (Overbought climax) and blocks SELL when &le; 30 (Oversold floor).
                </span>
              </span>
              <span class="text-slate-300 dark:text-slate-700 mx-1">|</span>
              <span class="text-slate-500 dark:text-slate-400 has-tooltip inline-flex items-center">
                <span>HTF: <span id="txt-htf" class="font-mono font-bold text-slate-900 dark:text-white">NEUTRAL</span></span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">M5 HTF Macro Trend</strong>
                  M5 EMA(9) vs EMA(21) macro momentum alignment.
                </span>
              </span>"""

assert old_card1_rsi in content, "old_card1_rsi not found"
content = content.replace(old_card1_rsi, new_card1_rsi)

# 2. Add HTF badge in Radar card
old_radar_rsi = """            <div class="flex items-center space-x-1.5">
              <span class="has-tooltip inline-flex items-center">
                <span class="text-slate-400 dark:text-slate-500">RSI-14:</span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">RSI Status Filter</strong>
                  NORMAL (30-70 safe entry window). OVERBOUGHT (&ge; 70, Buy blocked). OVERSOLD (&le; 30, Sell blocked).
                </span>
              </span>
              <span id="radar-rsi-val" class="font-mono font-bold text-slate-800 dark:text-slate-200">50.0</span>
              <span id="radar-rsi-badge" class="px-1.5 py-0.2 rounded text-[10px] font-extrabold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">NORMAL</span>
            </div>"""

new_radar_rsi = """            <div class="flex items-center space-x-1.5">
              <span class="has-tooltip inline-flex items-center">
                <span class="text-slate-400 dark:text-slate-500">RSI-14:</span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">RSI Status Filter</strong>
                  NORMAL (30-70 safe entry window). OVERBOUGHT (&ge; 70, Buy blocked). OVERSOLD (&le; 30, Sell blocked).
                </span>
              </span>
              <span id="radar-rsi-val" class="font-mono font-bold text-slate-800 dark:text-slate-200">50.0</span>
              <span id="radar-rsi-badge" class="px-1.5 py-0.2 rounded text-[10px] font-extrabold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">NORMAL</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="has-tooltip inline-flex items-center">
                <span class="text-slate-400 dark:text-slate-500">HTF Trend:</span>
                <span class="tip-icon">i</span>
                <span class="tooltip-box tip-right">
                  <strong class="block text-amber-400 font-semibold mb-0.5">Lever 3: Higher-Timeframe Trend</strong>
                  M5 EMA(9) vs EMA(21) macro momentum alignment.
                </span>
              </span>
              <span id="radar-htf-badge" class="px-1.5 py-0.2 rounded text-[10px] font-extrabold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">NEUTRAL</span>
            </div>"""

assert old_radar_rsi in content, "old_radar_rsi not found"
content = content.replace(old_radar_rsi, new_radar_rsi)

# 3. Add Lever 3 Settings controls in modal
old_lever2_box = """            <!-- Dynamic ATR Volatility Scaling & Max ATR Ceiling -->
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
            </div>"""

new_lever2_and_3_box = old_lever2_box + """

            <!-- Lever 3: Higher-Timeframe (HTF) Macro Alignment & Grid Momentum Gate -->
            <div class="sm:col-span-2 p-3 rounded-xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="text-base">🧭</span>
                  <div>
                    <span class="text-xs font-bold text-slate-800 dark:text-slate-200">Lever 3: Higher-Timeframe (HTF) Macro Alignment &amp; Anti-Averaging Gate</span>
                    <span class="block text-[10px] text-slate-500 dark:text-slate-400">Enforces M5/M15 trend alignment (never sell green rocket, never buy falling knife) &amp; requires bounce before averaging</span>
                  </div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" id="cfg-htf_filter" class="sr-only peer" checked>
                  <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">HTF Timeframe</label>
                  <select id="cfg-htf_tf" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white">
                    <option value="M5" selected>M5 (5 Minutes)</option>
                    <option value="M15">M15 (15 Minutes)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Fast EMA Period</label>
                  <input type="number" step="1" id="cfg-htf_ema_fast" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="default 9">
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Slow EMA Period</label>
                  <input type="number" step="1" id="cfg-htf_ema_slow" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="default 21">
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Grid Bounce Req ($)</label>
                  <input type="number" step="0.05" id="cfg-grid_bounce_req" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white" placeholder="default 0.40">
                </div>
              </div>
            </div>"""

assert old_lever2_box in content, "old_lever2_box not found"
content = content.replace(old_lever2_box, new_lever2_and_3_box)

# 4. Update JS live telemetry update
old_js_update = """          } else {
            rRsiBadge.innerText = 'NORMAL';
            rRsiBadge.className = 'px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700';
            rRsiBadge.title = `RSI (${rsiNum.toFixed(1)}) within safe bounds (${osLevel}-${obLevel}): Momentum clear for entries`;
          }
        }"""

new_js_update = """          } else {
            rRsiBadge.innerText = 'NORMAL';
            rRsiBadge.className = 'px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700';
            rRsiBadge.title = `RSI (${rsiNum.toFixed(1)}) within safe bounds (${osLevel}-${obLevel}): Momentum clear for entries`;
          }
        }

        const rHtfBadge = document.getElementById('radar-htf-badge');
        const txtHtf = document.getElementById('txt-htf');
        if (telem && telem.htf_status) {
          const status = telem.htf_status;
          const tfStr = telem.htf_tf || 'M5';
          const fastVal = telem.htf_fast || 0;
          const slowVal = telem.htf_slow || 0;
          if (rHtfBadge) {
            rHtfBadge.innerText = `${tfStr} ${status}`;
            if (status === 'BULLISH') {
              rHtfBadge.className = 'px-1.5 py-0.2 rounded text-[10px] font-extrabold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30';
              rHtfBadge.title = `${tfStr} Bullish (EMA ${fastVal} > ${slowVal}): BUY only, SELL entries blocked`;
            } else if (status === 'BEARISH') {
              rHtfBadge.className = 'px-1.5 py-0.2 rounded text-[10px] font-extrabold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30';
              rHtfBadge.title = `${tfStr} Bearish (EMA ${fastVal} < ${slowVal}): SELL only, BUY entries blocked`;
            } else {
              rHtfBadge.className = 'px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700';
              rHtfBadge.title = `${tfStr} Neutral: Both BUY & SELL entries allowed`;
            }
          }
          if (txtHtf) {
            txtHtf.innerText = status;
            txtHtf.className = status === 'BULLISH' ? 'font-mono text-emerald-500 font-bold' : (status === 'BEARISH' ? 'font-mono text-rose-500 font-bold' : 'font-mono text-slate-700 dark:text-slate-300');
          }
        }"""

assert old_js_update in content, "old_js_update not found"
content = content.replace(old_js_update, new_js_update)

# 5. Update saveConfig in JS
old_save_cfg = """        max_atr: parseFloat(document.getElementById('cfg-max_atr')?.value) || 0.0,
        max_ma_dist: parseFloat(document.getElementById('cfg-max_ma_dist').value) || 0.0,"""

new_save_cfg = """        max_atr: parseFloat(document.getElementById('cfg-max_atr')?.value) || 0.0,
        htf_filter: document.getElementById('cfg-htf_filter') ? document.getElementById('cfg-htf_filter').checked : true,
        htf_tf: document.getElementById('cfg-htf_tf')?.value || 'M5',
        htf_ema_fast: parseInt(document.getElementById('cfg-htf_ema_fast')?.value) || 9,
        htf_ema_slow: parseInt(document.getElementById('cfg-htf_ema_slow')?.value) || 21,
        grid_bounce_req: parseFloat(document.getElementById('cfg-grid_bounce_req')?.value) || 0.0,
        max_ma_dist: parseFloat(document.getElementById('cfg-max_ma_dist').value) || 0.0,"""

assert old_save_cfg in content, "old_save_cfg not found"
content = content.replace(old_save_cfg, new_save_cfg)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied Lever 3 UI successfully to templates/index.html")

