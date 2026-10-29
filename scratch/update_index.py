with open('templates/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''              <span class="text-[10px] text-slate-400 font-mono flex items-center space-x-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
                <span>MT5 Ground Truth</span>
              </span>'''

replacement = '''              <div class="flex items-center space-x-2">
                <a href="/api/export_trades_csv" download="closed_trades.csv" class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-all inline-flex items-center space-x-1" title="Download complete offline closed trades CSV ledger with timestamps and telemetry">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  <span>Export CSV</span>
                </a>
                <span class="text-[10px] text-slate-400 font-mono flex items-center space-x-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
                  <span>Auto-Synced</span>
                </span>
              </div>'''

c_norm = c.replace('\r\n', '\n')
t_norm = target.replace('\r\n', '\n')
r_norm = replacement.replace('\r\n', '\n')

if t_norm in c_norm:
    c_norm = c_norm.replace(t_norm, r_norm)
    with open('templates/index.html', 'w', encoding='utf-8', newline='') as f:
        f.write(c_norm.replace('\n', '\r\n'))
    print('Updated index.html successfully')
else:
    print('Target not found in index.html')

