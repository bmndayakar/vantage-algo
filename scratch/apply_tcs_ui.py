import sys

with open("templates/index.html", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add TCS Panel in Section 2 right below panel-entry-radar
panel_target = '''        </div>
      </div>
    </div>

    <!-- SECTION 3: PERFORMANCE ANALYTICS & ORDER MANAGEMENT -->'''

tcs_panel_html = '''        </div>
      </div>

      <!-- TCS 4-PILLAR TREND CONFIRMATION RADAR -->
      <div id="panel-tcs-radar" class="mt-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-3.5 sm:p-4 shadow-sm transition-all duration-200">
        <!-- Top bar: TCS status banner + candle discipline tag + mode switch badge -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5 mb-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="has-tooltip inline-flex items-center">
              <span class="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200 flex items-center space-x-1.5">
                <span class="text-amber-500 text-sm">🛡️</span>
                <span>Trend Confirmation System (TCS)</span>
              </span>
              <span class="tip-icon">i</span>
              <span class="tooltip-box tip-left">
                <strong class="block text-amber-400 font-semibold mb-0.5">4-Pillar Regime Filter</strong>
                Filters weak, choppy signals by strictly validating Trend Direction (50/200 EMA), Strength (ADX &ge; 25), Price Structure (HH/HL vs LH/LL), and Momentum (MACD Histogram) on closed candles.
              </span>
            </span>
            <span id="badge-tcs-mode" class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">HYBRID MODE</span>
            <span id="badge-tcs-closed-candle" class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700">✓ BAR CLOSED DISCIPLINE</span>
          </div>
          <div class="flex items-center space-x-2">
            <span id="badge-tcs-summary" class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
              CALCULATING PILLARS...
            </span>
          </div>
        </div>

        <!-- 4 Pillars Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 text-xs">
          <!-- Pillar 1: Direction -->
          <div class="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-2.5 border border-slate-100 dark:border-slate-800/80 flex flex-col justify-between">
            <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
              <span class="font-bold flex items-center space-x-1">
                <span>1. Direction</span>
              </span>
              <span id="badge-p1-status" class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">---</span>
            </div>
            <div class="font-mono text-[11px] space-y-0.5 my-1">
              <div class="flex justify-between"><span>50 EMA:</span> <strong id="tcs-ema-fast" class="text-slate-800 dark:text-slate-200">---</strong></div>
              <div class="flex justify-between"><span>200 EMA:</span> <strong id="tcs-ema-slow" class="text-slate-800 dark:text-slate-200">---</strong></div>
            </div>
            <div class="text-[10px] text-slate-400 border-t border-slate-200/50 dark:border-slate-700/50 pt-1 mt-0.5 flex justify-between">
              <span>Align:</span>
              <span id="tcs-p1-desc" class="font-mono font-semibold text-slate-600 dark:text-slate-300">50 vs 200</span>
            </div>
          </div>

          <!-- Pillar 2: Strength -->
          <div class="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-2.5 border border-slate-100 dark:border-slate-800/80 flex flex-col justify-between">
            <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
              <span class="font-bold flex items-center space-x-1">
                <span>2. Strength</span>
              </span>
              <span id="badge-p2-status" class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">---</span>
            </div>
            <div class="font-mono text-[11px] space-y-0.5 my-1">
              <div class="flex justify-between"><span>ADX(14):</span> <strong id="tcs-adx-val" class="text-slate-800 dark:text-slate-200">---</strong></div>
              <div class="flex justify-between"><span>+DI / -DI:</span> <span class="text-slate-700 dark:text-slate-300"><strong id="tcs-di-plus" class="text-emerald-500">--</strong> / <strong id="tcs-di-minus" class="text-rose-500">--</strong></span></div>
            </div>
            <div class="text-[10px] text-slate-400 border-t border-slate-200/50 dark:border-slate-700/50 pt-1 mt-0.5 flex justify-between">
              <span>Slope:</span>
              <span id="tcs-adx-slope" class="font-mono font-semibold text-slate-600 dark:text-slate-300">---</span>
            </div>
          </div>

          <!-- Pillar 3: Structure -->
          <div class="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-2.5 border border-slate-100 dark:border-slate-800/80 flex flex-col justify-between">
            <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
              <span class="font-bold flex items-center space-x-1">
                <span>3. Structure</span>
              </span>
              <span id="badge-p3-status" class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">---</span>
            </div>
            <div class="font-mono text-[11px] space-y-0.5 my-1">
              <div class="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate" id="tcs-struct-tag">CHOPPY</div>
              <div class="text-[10px] text-slate-400 font-sans">Swing Pivots (20b)</div>
            </div>
            <div class="text-[10px] text-slate-400 border-t border-slate-200/50 dark:border-slate-700/50 pt-1 mt-0.5 flex justify-between">
              <span>HH/HL:</span>
              <span id="tcs-p3-desc" class="font-mono font-semibold text-slate-600 dark:text-slate-300">Checking...</span>
            </div>
          </div>

          <!-- Pillar 4: Momentum -->
          <div class="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-2.5 border border-slate-100 dark:border-slate-800/80 flex flex-col justify-between">
            <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
              <span class="font-bold flex items-center space-x-1">
                <span>4. Momentum</span>
              </span>
              <span id="badge-p4-status" class="px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">---</span>
            </div>
            <div class="font-mono text-[11px] space-y-0.5 my-1">
              <div class="flex justify-between"><span>MACD Hist:</span> <strong id="tcs-macd-hist" class="text-slate-800 dark:text-slate-200">---</strong></div>
              <div class="flex justify-between"><span>Slope:</span> <strong id="tcs-macd-slope" class="text-slate-700 dark:text-slate-300">---</strong></div>
            </div>
            <div class="text-[10px] text-slate-400 border-t border-slate-200/50 dark:border-slate-700/50 pt-1 mt-0.5 flex justify-between">
              <span>Sign:</span>
              <span id="tcs-p4-desc" class="font-mono font-semibold text-slate-600 dark:text-slate-300">---</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SECTION 3: PERFORMANCE ANALYTICS & ORDER MANAGEMENT -->'''

if panel_target not in code:
    print("Could not find panel_target in templates/index.html")
    sys.exit(1)

code = code.replace(panel_target, tcs_panel_html)

# 2. Add Settings Modal TCS card
settings_target = '''            <!-- Lever 3: Higher-Timeframe (HTF) Macro Alignment & Grid Momentum Gate -->'''

tcs_settings_html = '''            <!-- Trend Confirmation System (TCS - 4 Pillars) -->
            <div class="sm:col-span-2 p-3 rounded-xl bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/40">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="text-base">🛡️</span>
                  <div>
                    <span class="text-xs font-bold text-slate-800 dark:text-slate-200">Trend Confirmation System (4-Pillars: 50/200 EMA + ADX + Structure + MACD)</span>
                    <span class="block text-[10px] text-slate-500 dark:text-slate-400">Institutional regime filter to block low-conviction choppy market traps on closed candles</span>
                  </div>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Confirmation System Switch</label>
                  <select id="cfg-trend_system" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white">
                    <option value="hybrid">Hybrid (TCS Macro + Pullback Timing)</option>
                    <option value="tcs">TCS Strict (4 Pillars Only)</option>
                    <option value="legacy">Legacy (250 SMA + Lever 3 HTF)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">TCS Timeframe</label>
                  <select id="cfg-tcs_tf" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white">
                    <option value="M1">M1 (1-Minute Candles)</option>
                    <option value="M5">M5 (5-Minute Candles)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[11px] text-slate-600 dark:text-slate-400 mb-0.5">Min Confirming Pillars</label>
                  <select id="cfg-tcs_min_pillars" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-900 dark:text-white">
                    <option value="3">3 of 4 Pillars (High Quality)</option>
                    <option value="4">4 of 4 Pillars (Sniper Strict)</option>
                  </select>
                </div>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-2.5">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-0.5">P1 Fast EMA</label>
                  <input type="number" id="cfg-tcs_ema_fast" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs font-mono" placeholder="50">
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-0.5">P1 Slow EMA</label>
                  <input type="number" id="cfg-tcs_ema_slow" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs font-mono" placeholder="200">
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-0.5">P2 ADX Threshold</label>
                  <input type="number" step="1.0" id="cfg-tcs_adx_min" class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs font-mono" placeholder="25.0">
                </div>
                <div class="flex items-center space-x-2 pt-4">
                  <input type="checkbox" id="cfg-tcs_adx_require_rising" class="w-4 h-4 rounded text-purple-600 focus:ring-purple-500">
                  <label for="cfg-tcs_adx_require_rising" class="text-[10px] font-medium text-slate-600 dark:text-slate-400">Require Rising ADX</label>
                </div>
              </div>
            </div>

''' + settings_target

if settings_target not in code:
    print("Could not find settings_target in templates/index.html")
    sys.exit(1)

code = code.replace(settings_target, tcs_settings_html)

# 3. Add JS function updateTcsRadar and hook it into updateDashboard
js_tcs_update = '''
    function updateTcsRadar(telem) {
      if (!telem) return;
      const tcsDir = telem.tcs_dir || 0;
      const tcsStatus = telem.tcs_status || 'NEUTRAL';
      const bScore = telem.tcs_bull_score || 0;
      const sScore = telem.tcs_bear_score || 0;
      const trendSys = (telem.trend_system || 'hybrid').toUpperCase();

      // Mode Badge
      const modeBadge = document.getElementById('badge-tcs-mode');
      if (modeBadge) {
        modeBadge.innerText = `${trendSys} MODE`;
        modeBadge.className = trendSys === 'TCS' ? 'px-2 py-0.5 rounded text-[10px] font-extrabold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20' : (trendSys === 'HYBRID' ? 'px-2 py-0.5 rounded text-[10px] font-extrabold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20' : 'px-2 py-0.5 rounded text-[10px] font-extrabold bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700');
      }

      // Summary Badge
      const sumBadge = document.getElementById('badge-tcs-summary');
      if (sumBadge) {
        sumBadge.innerText = tcsStatus;
        if (tcsDir === 1) {
          sumBadge.className = 'px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shadow-sm';
        } else if (tcsDir === -1) {
          sumBadge.className = 'px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 shadow-sm';
        } else {
          sumBadge.className = 'px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30';
        }
      }

      // Pillar 1: Direction
      const p1Badge = document.getElementById('badge-p1-status');
      const efEl = document.getElementById('tcs-ema-fast');
      const esEl = document.getElementById('tcs-ema-slow');
      const p1Desc = document.getElementById('tcs-p1-desc');
      if (efEl) efEl.innerText = telem.tcs_ema_fast ? telem.tcs_ema_fast.toFixed(2) : '---';
      if (esEl) esEl.innerText = telem.tcs_ema_slow ? telem.tcs_ema_slow.toFixed(2) : '---';
      if (p1Badge) {
        if (telem.tcs_p1_bull) {
          p1Badge.innerText = 'BULLISH';
          p1Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
          if (p1Desc) p1Desc.innerText = '50 > 200 & P > Both';
        } else if (telem.tcs_p1_bear) {
          p1Badge.innerText = 'BEARISH';
          p1Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400';
          if (p1Desc) p1Desc.innerText = '50 < 200 & P < Both';
        } else {
          p1Badge.innerText = 'NEUTRAL';
          p1Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
          if (p1Desc) p1Desc.innerText = 'EMAs Mixed';
        }
      }

      // Pillar 2: Strength
      const p2Badge = document.getElementById('badge-p2-status');
      const adxValEl = document.getElementById('tcs-adx-val');
      const diPlusEl = document.getElementById('tcs-di-plus');
      const diMinusEl = document.getElementById('tcs-di-minus');
      const adxSlopeEl = document.getElementById('tcs-adx-slope');
      if (adxValEl) adxValEl.innerText = telem.tcs_adx ? telem.tcs_adx.toFixed(1) : '---';
      if (diPlusEl) diPlusEl.innerText = telem.tcs_di_plus ? telem.tcs_di_plus.toFixed(1) : '--';
      if (diMinusEl) diMinusEl.innerText = telem.tcs_di_minus ? telem.tcs_di_minus.toFixed(1) : '--';
      if (adxSlopeEl) {
        adxSlopeEl.innerText = telem.tcs_adx_rising ? 'Rising ↗' : 'Falling ↘';
        adxSlopeEl.className = telem.tcs_adx_rising ? 'font-mono font-semibold text-emerald-500' : 'font-mono font-semibold text-slate-400';
      }
      if (p2Badge) {
        if (telem.tcs_p2_bull) {
          p2Badge.innerText = 'BULLISH';
          p2Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
        } else if (telem.tcs_p2_bear) {
          p2Badge.innerText = 'BEARISH';
          p2Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400';
        } else {
          p2Badge.innerText = telem.tcs_adx < 25 ? 'WEAK (<25)' : 'CHOP';
          p2Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/15 text-amber-600 dark:text-amber-400';
        }
      }

      // Pillar 3: Structure
      const p3Badge = document.getElementById('badge-p3-status');
      const structTagEl = document.getElementById('tcs-struct-tag');
      const p3Desc = document.getElementById('tcs-p3-desc');
      if (structTagEl) structTagEl.innerText = telem.tcs_structure || 'CHOPPY';
      if (p3Badge) {
        if (telem.tcs_p3_bull) {
          p3Badge.innerText = 'HH / HL';
          p3Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
          if (p3Desc) p3Desc.innerText = 'Higher Highs/Lows';
        } else if (telem.tcs_p3_bear) {
          p3Badge.innerText = 'LH / LL';
          p3Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400';
          if (p3Desc) p3Desc.innerText = 'Lower Highs/Lows';
        } else {
          p3Badge.innerText = 'CHOP';
          p3Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
          if (p3Desc) p3Desc.innerText = 'No Clean Pivots';
        }
      }

      // Pillar 4: Momentum
      const p4Badge = document.getElementById('badge-p4-status');
      const macdHistEl = document.getElementById('tcs-macd-hist');
      const macdSlopeEl = document.getElementById('tcs-macd-slope');
      const p4Desc = document.getElementById('tcs-p4-desc');
      if (macdHistEl) macdHistEl.innerText = telem.tcs_macd_hist ? telem.tcs_macd_hist.toFixed(2) : '---';
      if (macdSlopeEl) {
        macdSlopeEl.innerText = telem.tcs_macd_rising ? 'Rising ↗' : 'Falling ↘';
        macdSlopeEl.className = telem.tcs_macd_rising ? 'text-emerald-500 font-bold' : 'text-rose-500 font-bold';
      }
      if (p4Badge) {
        if (telem.tcs_p4_bull) {
          p4Badge.innerText = '+ RISING';
          p4Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
          if (p4Desc) p4Desc.innerText = 'Positive & Rising';
        } else if (telem.tcs_p4_bear) {
          p4Badge.innerText = '- FALLING';
          p4Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-500/15 text-rose-600 dark:text-rose-400';
          if (p4Desc) p4Desc.innerText = 'Negative & Falling';
        } else {
          p4Badge.innerText = 'MIXED';
          p4Badge.className = 'px-1.5 py-0.2 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
          if (p4Desc) p4Desc.innerText = 'Counter-Slope';
        }
      }
    }
'''

update_dash_target = '''      // Win Rate & Performance Matrix
      if (s.win_rate_stats) {
        updateWinRateMatrix(s.win_rate_stats);
      }'''

update_dash_replacement = '''      // Win Rate & Performance Matrix
      if (s.win_rate_stats) {
        updateWinRateMatrix(s.win_rate_stats);
      }

      // TCS 4-Pillar Trend Confirmation Radar
      if (s.telemetry) {
        updateTcsRadar(s.telemetry);
      }'''

if update_dash_target not in code:
    print("Could not find update_dash_target in templates/index.html")
    sys.exit(1)

code = code.replace(update_dash_target, update_dash_replacement)

# 4. Insert updateTcsRadar JS function right above updateWinRateMatrix
fn_target = '    function updateWinRateMatrix(stats) {'
if fn_target not in code:
    print("Could not find fn_target in templates/index.html")
    sys.exit(1)

code = code.replace(fn_target, js_tcs_update + '\n' + fn_target)

# 5. Add TCS fields to saveConfig
save_cfg_target = '''        entry_mode: document.getElementById('cfg-entry_mode') ? document.getElementById('cfg-entry_mode').value : 'pullback','''

save_cfg_replacement = '''        entry_mode: document.getElementById('cfg-entry_mode') ? document.getElementById('cfg-entry_mode').value : 'pullback',
        trend_system: document.getElementById('cfg-trend_system')?.value || 'hybrid',
        tcs_tf: document.getElementById('cfg-tcs_tf')?.value || 'M1',
        tcs_ema_fast: parseInt(document.getElementById('cfg-tcs_ema_fast')?.value) || 50,
        tcs_ema_slow: parseInt(document.getElementById('cfg-tcs_ema_slow')?.value) || 200,
        tcs_adx_period: 14,
        tcs_adx_min: parseFloat(document.getElementById('cfg-tcs_adx_min')?.value) || 25.0,
        tcs_adx_require_rising: document.getElementById('cfg-tcs_adx_require_rising') ? document.getElementById('cfg-tcs_adx_require_rising').checked : false,
        tcs_min_pillars: parseInt(document.getElementById('cfg-tcs_min_pillars')?.value) || 3,'''

if save_cfg_target not in code:
    print("Could not find save_cfg_target in templates/index.html")
    sys.exit(1)

code = code.replace(save_cfg_target, save_cfg_replacement)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(code)

print("templates/index.html successfully updated with TCS radar and controls!")

