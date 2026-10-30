with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add Noob/Pro Mode Toggle Card right after form-config opening tag
target_form_top = '''      <!-- Form Body with Scrollable Inputs and Pinned Footer -->
      <form id="form-config" onsubmit="saveConfig(event)" class="mt-3 sm:mt-4 flex-1 flex flex-col min-h-0">
        <!-- Scrollable Inputs Container -->
        <div class="overflow-y-auto pr-1 sm:pr-2 space-y-4 flex-1 min-h-0">'''

noob_pro_banner = '''      <!-- Form Body with Scrollable Inputs and Pinned Footer -->
      <form id="form-config" onsubmit="saveConfig(event)" class="mt-3 sm:mt-4 flex-1 flex flex-col min-h-0">
        <!-- Scrollable Inputs Container -->
        <div class="overflow-y-auto pr-1 sm:pr-2 space-y-4 flex-1 min-h-0">

          <!-- MODE SELECTOR: NOOB VS PRO -->
          <div class="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent dark:from-amber-500/20 dark:via-amber-500/10 dark:to-transparent border border-amber-500/30 rounded-xl p-3 sm:p-4 shadow-sm">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
                <span>🎛️ Operation Mode</span>
              </span>
              <div class="flex items-center space-x-2 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
                <label class="cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all select-none" id="lbl-mode-noob">
                  <input type="radio" name="ui_mode" value="noob" id="mode-noob" onchange="toggleUiMode('noob')" class="sr-only">
                  <span>🐣 Noob (Auto)</span>
                </label>
                <label class="cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all select-none" id="lbl-mode-pro">
                  <input type="radio" name="ui_mode" value="pro" id="mode-pro" onchange="toggleUiMode('pro')" class="sr-only">
                  <span>⚡ Pro (Manual)</span>
                </label>
              </div>
            </div>

            <!-- NOOB SLIDER CARD -->
            <div id="noob-slider-container" class="space-y-3 pt-1">
              <div class="flex items-center justify-between text-xs">
                <div class="flex items-center space-x-2">
                  <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400">Risk & Activity:</span>
                  <span id="txt-noob-badge" class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">Level 3: Balanced</span>
                </div>
                <span id="txt-noob-sl-tp" class="font-mono text-[11px] font-bold text-slate-700 dark:text-slate-300">SL: -$4.50 | Arm: +$1.40</span>
              </div>

              <!-- 5-Level Stepped Range Slider -->
              <div class="relative py-1">
                <input type="range" id="noob-slider" min="1" max="5" step="1" value="3" oninput="onNoobSliderChange(this.value)" class="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500">
                <div class="flex justify-between text-[10px] text-slate-400 dark:text-slate-500 font-bold px-1 mt-1.5">
                  <span class="text-emerald-500 cursor-pointer" onclick="onNoobSliderChange(1)">1: Safe</span>
                  <span class="cursor-pointer" onclick="onNoobSliderChange(2)">2: Cons</span>
                  <span class="text-indigo-500 cursor-pointer" onclick="onNoobSliderChange(3)">3: Bal</span>
                  <span class="cursor-pointer" onclick="onNoobSliderChange(4)">4: Scalp</span>
                  <span class="text-amber-500 cursor-pointer" onclick="onNoobSliderChange(5)">5: Mom</span>
                </div>
              </div>

              <!-- Dynamic Description -->
              <div id="txt-noob-desc" class="text-[11px] text-slate-600 dark:text-slate-300 bg-white/70 dark:bg-slate-800/70 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-700/60">
                Optimal sweet spot: 3/4 Pillars, ADX &gt;= 18, balanced risk-reward ($4.50 max cut, $1.40 trail arm).
              </div>
            </div>

            <!-- PRO MODE NOTICE -->
            <div id="pro-notice-container" class="hidden text-xs text-slate-600 dark:text-slate-400 py-1 flex items-center justify-between">
              <span class="flex items-center space-x-1.5">
                <span class="text-amber-500 font-bold">⚙️ Pro Mode Active:</span>
                <span>Slider disabled. All 25+ parameters below are fully unlocked for custom manual tuning.</span>
              </span>
            </div>
          </div>'''

assert target_form_top in text, "target_form_top not found"
text = text.replace(target_form_top, noob_pro_banner, 1)

# 2. Add wrapper around manual fields
target_grid_start = '<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-xs">'
replace_grid_start = '<div id="manual-config-fields" class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-xs transition-opacity duration-200">'
assert target_grid_start in text, "target_grid_start not found"
text = text.replace(target_grid_start, replace_grid_start, 1)

# 3. Add JavaScript handlers for Noob/Pro toggle, slider presets, and openConfigModal bindings
target_save_cfg = '    async function saveConfig(e) {'
js_noob_pro = '''    // ==========================================
    // NOOB VS PRO MODE & 5-LEVEL SLIDER ENGINE
    // ==========================================
    const NOOB_PRESETS_CLIENT = {
      1: {
        name: "Level 1: Ultra-Safe",
        badgeClass: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30",
        desc: "Institutional trend alignment only: 4/4 Pillars, ADX >= 25, tightest $3.50 loss ceiling, $2.00 trail arm.",
        sltp: "SL: -$3.50 | Arm: +$2.00",
        fields: {
          tcs_min_pillars: 4, tcs_adx_min: 25.0, max_ma_dist: 12.0, pullback_zone: 8.0,
          grid_sl: 3.50, trail_arm: 2.00, trail_min_lock: 0.50, hard_cap_hours: 0.5,
          trend_system: "hybrid", entry_mode: "pullback"
        }
      },
      2: {
        name: "Level 2: Conservative",
        badgeClass: "bg-teal-500/15 text-teal-600 dark:text-teal-400 border border-teal-500/30",
        desc: "High conviction trends, low chop tolerance: 3/4 Pillars, ADX >= 22, $4.00 loss cut, $1.60 trail arm.",
        sltp: "SL: -$4.00 | Arm: +$1.60",
        fields: {
          tcs_min_pillars: 3, tcs_adx_min: 22.0, max_ma_dist: 15.0, pullback_zone: 10.0,
          grid_sl: 4.00, trail_arm: 1.60, trail_min_lock: 0.40, hard_cap_hours: 0.75,
          trend_system: "hybrid", entry_mode: "pullback"
        }
      },
      3: {
        name: "Level 3: Balanced Scalp",
        badgeClass: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30",
        desc: "Optimal sweet spot: 3/4 Pillars, ADX >= 18, balanced risk-reward ($4.50 max cut, $1.40 trail arm).",
        sltp: "SL: -$4.50 | Arm: +$1.40",
        fields: {
          tcs_min_pillars: 3, tcs_adx_min: 18.0, max_ma_dist: 20.0, pullback_zone: 12.0,
          grid_sl: 4.50, trail_arm: 1.40, trail_min_lock: 0.40, hard_cap_hours: 1.0,
          trend_system: "hybrid", entry_mode: "pullback"
        }
      },
      4: {
        name: "Level 4: Active Scalper",
        badgeClass: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30",
        desc: "High trade frequency, shallower pullbacks: 2/4 Pillars, ADX >= 15, $5.00 max cut, $1.20 trail arm.",
        sltp: "SL: -$5.00 | Arm: +$1.20",
        fields: {
          tcs_min_pillars: 2, tcs_adx_min: 15.0, max_ma_dist: 28.0, pullback_zone: 16.0,
          grid_sl: 5.00, trail_arm: 1.20, trail_min_lock: 0.30, hard_cap_hours: 1.0,
          trend_system: "hybrid", entry_mode: "pullback"
        }
      },
      5: {
        name: "Level 5: Momentum Velocity",
        badgeClass: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30",
        desc: "Full trend participation, never locked out of big market runs: 2/4 Pillars, ADX >= 12, $5.50 cut, $1.00 arm.",
        sltp: "SL: -$5.50 | Arm: +$1.00",
        fields: {
          tcs_min_pillars: 2, tcs_adx_min: 12.0, max_ma_dist: 35.0, pullback_zone: 20.0,
          grid_sl: 5.50, trail_arm: 1.00, trail_min_lock: 0.30, hard_cap_hours: 1.0,
          trend_system: "hybrid", entry_mode: "pullback"
        }
      }
    };

    let currentUiMode = 'noob';
    let currentNoobLevel = 3;

    function toggleUiMode(mode) {
      currentUiMode = mode;
      const isNoob = (mode === 'noob');

      const btnNoob = document.getElementById('lbl-mode-noob');
      const btnPro = document.getElementById('lbl-mode-pro');
      const radNoob = document.getElementById('mode-noob');
      const radPro = document.getElementById('mode-pro');
      const sliderBox = document.getElementById('noob-slider-container');
      const proNotice = document.getElementById('pro-notice-container');
      const manualBox = document.getElementById('manual-config-fields');

      if (isNoob) {
        if (radNoob) radNoob.checked = true;
        if (btnNoob) btnNoob.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all bg-white dark:bg-slate-700 text-amber-600 dark:text-amber-400 shadow-sm';
        if (btnPro) btnPro.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';
        if (sliderBox) sliderBox.classList.remove('hidden');
        if (proNotice) proNotice.classList.add('hidden');
        if (manualBox) {
          manualBox.classList.add('opacity-40', 'pointer-events-none');
        }
        applyNoobPresetUI(currentNoobLevel);
      } else {
        if (radPro) radPro.checked = true;
        if (btnPro) btnPro.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all bg-white dark:bg-slate-700 text-amber-600 dark:text-amber-400 shadow-sm';
        if (btnNoob) btnNoob.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';
        if (sliderBox) sliderBox.classList.add('hidden');
        if (proNotice) proNotice.classList.remove('hidden');
        if (manualBox) {
          manualBox.classList.remove('opacity-40', 'pointer-events-none');
        }
      }
    }

    function onNoobSliderChange(val) {
      const lvl = parseInt(val) || 3;
      currentNoobLevel = lvl;
      const slider = document.getElementById('noob-slider');
      if (slider && slider.value != lvl) slider.value = lvl;
      applyNoobPresetUI(lvl);
    }

    function applyNoobPresetUI(lvl) {
      const p = NOOB_PRESETS_CLIENT[lvl];
      if (!p) return;

      const txtBadge = document.getElementById('txt-noob-badge');
      const txtDesc = document.getElementById('txt-noob-desc');
      const txtSlTp = document.getElementById('txt-noob-sl-tp');

      if (txtBadge) {
        txtBadge.innerText = p.name;
        txtBadge.className = 'px-2 py-0.5 rounded text-[11px] font-extrabold ' + p.badgeClass;
      }
      if (txtDesc) txtDesc.innerText = p.desc;
      if (txtSlTp) txtSlTp.innerText = p.sltp;

      // Populate form fields so user can inspect what is being applied
      for (let k in p.fields) {
        const el = document.getElementById('cfg-' + k);
        if (el) el.value = p.fields[k];
      }
      calculateLiveMargin();
    }

'''

assert target_save_cfg in text, "target_save_cfg not found"
text = text.replace(target_save_cfg, js_noob_pro + target_save_cfg, 1)

# 4. In openConfigModal, initialize ui_mode and noob_level
target_modal_open = '''      const activeSym = document.getElementById('badge-active-symbol').innerText;
      const cfgSym = document.getElementById('cfg-symbol');
      if (cfgSym && activeSym) cfgSym.value = activeSym;
      calculateLiveMargin();'''

replace_modal_open = '''      const activeSym = document.getElementById('badge-active-symbol').innerText;
      const cfgSym = document.getElementById('cfg-symbol');
      if (cfgSym && activeSym) cfgSym.value = activeSym;

      // Sync UI Mode (Noob vs Pro) and Slider Level
      const savedMode = (latestConfig && latestConfig.ui_mode) ? latestConfig.ui_mode : 'noob';
      const savedLvl = (latestConfig && latestConfig.noob_level) ? parseInt(latestConfig.noob_level) : 3;
      currentNoobLevel = savedLvl;
      const slider = document.getElementById('noob-slider');
      if (slider) slider.value = savedLvl;
      toggleUiMode(savedMode);

      calculateLiveMargin();'''

assert target_modal_open in text, "target_modal_open not found"
text = text.replace(target_modal_open, replace_modal_open, 1)

# 5. In saveConfig, pass ui_mode and noob_level
target_save_body = '''        symbol: symVal || 'XAUUSD','''
replace_save_body = '''        ui_mode: currentUiMode,
        noob_level: currentNoobLevel,
        symbol: symVal || 'XAUUSD','''
assert target_save_body in text, "target_save_body not found"
text = text.replace(target_save_body, replace_save_body, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("templates/index.html successfully updated with Noob/Pro radio buttons and 5-level slider!")

