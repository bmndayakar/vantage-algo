with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update toggleUiMode to selectively disable only the 8 slider-managed fields
target_ui_mode = '''        if (manualBox) {
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
      }'''

replace_ui_mode = '''        const noobControlledKeys = [
          'tcs_min_pillars', 'tcs_adx_min', 'max_ma_dist', 'pullback_zone',
          'grid_sl', 'trail_arm', 'trail_min_lock', 'hard_cap_hours',
          'trend_system', 'entry_mode'
        ];
        noobControlledKeys.forEach(k => {
          const el = document.getElementById('cfg-' + k);
          if (el) {
            el.disabled = true;
            el.classList.add('opacity-50', 'cursor-not-allowed', 'bg-slate-100', 'dark:bg-slate-800/60');
          }
        });
        applyNoobPresetUI(currentNoobLevel);
      } else {
        if (radPro) radPro.checked = true;
        if (btnPro) btnPro.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all bg-white dark:bg-slate-700 text-amber-600 dark:text-amber-400 shadow-sm';
        if (btnNoob) btnNoob.className = 'cursor-pointer flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';
        if (sliderBox) sliderBox.classList.add('hidden');
        if (proNotice) proNotice.classList.remove('hidden');
        
        const noobControlledKeys = [
          'tcs_min_pillars', 'tcs_adx_min', 'max_ma_dist', 'pullback_zone',
          'grid_sl', 'trail_arm', 'trail_min_lock', 'hard_cap_hours',
          'trend_system', 'entry_mode'
        ];
        noobControlledKeys.forEach(k => {
          const el = document.getElementById('cfg-' + k);
          if (el) {
            el.disabled = false;
            el.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-slate-100', 'dark:bg-slate-800/60');
          }
        });
      }'''

assert target_ui_mode in text, "target_ui_mode not found"
text = text.replace(target_ui_mode, replace_ui_mode, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("templates/index.html updated successfully with selective field disabling!")

