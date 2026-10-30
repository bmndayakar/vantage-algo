with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add signature tracking variables at top of <script>
target_vars = """    let loginPrompted = false;"""
replace_vars = """    let loginPrompted = false;
    let lastClosedSig = '';
    let lastOpenSig = '';
    let lastEventsSig = '';
    let lastWrSig = '';
    let lastChartSec = 0;
    let wsReconnectTimeout = null;"""

assert target_vars in text, "target_vars not found"
text = text.replace(target_vars, replace_vars, 1)

# 2. Patch connectWS with clean disconnect & timeout handling
target_ws = """    // Connect WebSocket
    function connectWS() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${window.location.host}/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to Bot Server WS');
      };

      ws.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          updateUI(state);
        } catch (e) {
          console.error('State parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('WS disconnected, reconnecting in 2s...');
        document.getElementById('dot-mt5').className = 'w-2.5 h-2.5 rounded-full bg-rose-500';
        document.getElementById('txt-mt5').innerText = 'Connecting...';
        setTimeout(connectWS, 2000);
      };
    }"""

replace_ws = """    // Connect WebSocket
    function connectWS() {
      if (wsReconnectTimeout) {
        clearTimeout(wsReconnectTimeout);
        wsReconnectTimeout = null;
      }
      if (ws) {
        try {
          ws.onopen = null;
          ws.onmessage = null;
          ws.onerror = null;
          ws.onclose = null;
          ws.close();
        } catch (e) {}
        ws = null;
      }

      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${window.location.host}/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to Bot Server WS');
      };

      ws.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          updateUI(state);
        } catch (e) {
          console.error('State parse error:', e);
        }
      };

      ws.onclose = () => {
        const dot = document.getElementById('dot-mt5');
        const txt = document.getElementById('txt-mt5');
        if (dot) dot.className = 'w-2.5 h-2.5 rounded-full bg-rose-500';
        if (txt) txt.innerText = 'Connecting...';
        wsReconnectTimeout = setTimeout(connectWS, 2000);
      };
    }"""

assert target_ws in text, "target_ws not found"
text = text.replace(target_ws, replace_ws, 1)

# 3. Chart point throttling to once per second
target_chart = """        // Push live point to chart ONLY when bot is running
        const chartBadge = document.getElementById('badge-chart-status');
        if (s.is_running && chart && s.market) {
          if (chartBadge) {
            chartBadge.innerText = 'STREAMING';
            chartBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30';
          }
          const nowStr = new Date().toLocaleTimeString();
          if (chartData.labels.length > 30) {
            chartData.labels.shift();
            chartData.datasets[0].data.shift();
          }
          chartData.labels.push(nowStr);
          chartData.datasets[0].data.push(b.basket);
          chart.update('none');
        } else {"""

replace_chart = """        // Push live point to chart at most once per second when bot is running
        const chartBadge = document.getElementById('badge-chart-status');
        if (s.is_running && chart && s.market) {
          if (chartBadge) {
            chartBadge.innerText = 'STREAMING';
            chartBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30';
          }
          const nowSec = Math.floor(Date.now() / 1000);
          if (nowSec !== lastChartSec) {
            lastChartSec = nowSec;
            const nowStr = new Date().toLocaleTimeString();
            if (chartData.labels.length > 30) {
              chartData.labels.shift();
              chartData.datasets[0].data.shift();
            }
            chartData.labels.push(nowStr);
            chartData.datasets[0].data.push(b.basket);
            chart.update('none');
          }
        } else {"""

assert target_chart in text, "target_chart not found"
text = text.replace(target_chart, replace_chart, 1)

# 4. Open Positions table dirty check
target_open_pos = """      // Positions Table (Open)
      const tbl = document.getElementById('tbl-positions');
      const countEl = document.getElementById('badge-open-count');
      if (s.positions && s.positions.length > 0) {"""

replace_open_pos = """      // Positions Table (Open with Diffing)
      const tbl = document.getElementById('tbl-positions');
      const countEl = document.getElementById('badge-open-count');
      const curOpenSig = (s.positions && s.positions.length > 0)
        ? s.positions.map(p => `${p.ticket}_${(p.price_current || p.price_open).toFixed(2)}_${p.profit.toFixed(2)}_${p.duration || ''}`).join('|')
        : 'empty';

      if (curOpenSig !== lastOpenSig) {
        lastOpenSig = curOpenSig;
        if (s.positions && s.positions.length > 0) {"""

assert target_open_pos in text, "target_open_pos not found"
text = text.replace(target_open_pos, replace_open_pos, 1)

# Close the open table if block
target_open_close = """        tbl.innerHTML = html;
      } else {
        countEl.innerText = '0';
        tbl.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400 dark:text-slate-500 font-sans">No open positions</td></tr>';
      }

      // Closed Positions Table"""

replace_open_close = """        tbl.innerHTML = html;
        } else {
          countEl.innerText = '0';
          tbl.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400 dark:text-slate-500 font-sans">No open positions</td></tr>';
        }
      }

      // Closed Positions Table"""

assert target_open_close in text, "target_open_close not found"
text = text.replace(target_open_close, replace_open_close, 1)

# 5. Closed Positions table dirty check
target_closed_pos = """      // Closed Positions Table
      const tblClosed = document.getElementById('tbl-closed-positions');
      const countClosedEl = document.getElementById('badge-closed-count');
      if (s.closed_positions && s.closed_positions.length > 0) {"""

replace_closed_pos = """      // Closed Positions Table (Diffed: only re-renders when trades change)
      const tblClosed = document.getElementById('tbl-closed-positions');
      const countClosedEl = document.getElementById('badge-closed-count');
      const curClosedSig = (s.closed_positions && s.closed_positions.length > 0)
        ? `${s.closed_positions.length}_${s.closed_positions[0].ticket}_${s.closed_positions[0].profit}`
        : 'empty';

      if (curClosedSig !== lastClosedSig) {
        lastClosedSig = curClosedSig;
        if (s.closed_positions && s.closed_positions.length > 0) {"""

assert target_closed_pos in text, "target_closed_pos not found"
text = text.replace(target_closed_pos, replace_closed_pos, 1)

target_closed_end = """        tblClosed.innerHTML = htmlClosed;
      } else {
        countClosedEl.innerText = '0';
        tblClosed.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400 dark:text-slate-500 font-sans">No closed trades in selected period</td></tr>';
      }

      if (s.history_period) {"""

replace_closed_end = """        tblClosed.innerHTML = htmlClosed;
        } else {
          countClosedEl.innerText = '0';
          tblClosed.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-slate-400 dark:text-slate-500 font-sans">No closed trades in selected period</td></tr>';
        }
      }

      if (s.history_period) {"""

assert target_closed_end in text, "target_closed_end not found"
text = text.replace(target_closed_end, replace_closed_end, 1)

# 6. Terminal Log dirty check
target_terminal = """      // Live Terminal Feed
      if (s.events && s.events.length > 0) {
        const term = document.getElementById('log-terminal');
        const shouldScroll = term.scrollTop + term.clientHeight >= term.scrollHeight - 30;
        let logHtml = '';
        s.events.forEach(ev => {
          let badgeColor = 'text-slate-400';
          if (ev.event === 'ENTRY') badgeColor = 'text-emerald-400 font-bold';
          else if (ev.event === 'CLOSE') badgeColor = 'text-amber-400 font-bold';
          else if (ev.event === 'PANIC') badgeColor = 'text-rose-500 font-bold';
          logHtml += `<div class="leading-relaxed"><span class="text-slate-500">${ev.time}</span> <span class="${badgeColor}">${ev.event}</span> ${ev.side || ''} ${ev.detail || ''} <span class="text-slate-400">${ev.price > 0 ? '@' + ev.price.toFixed(2) : ''}</span></div>`;
        });
        term.innerHTML = logHtml;
        if (shouldScroll) term.scrollTop = term.scrollHeight;
      }"""

replace_terminal = """      // Live Terminal Feed (Diffed: only updates when new event arrives)
      const curEventsSig = (s.events && s.events.length > 0)
        ? `${s.events.length}_${s.events[s.events.length - 1].time}_${s.events[s.events.length - 1].event}`
        : 'empty';

      if (curEventsSig !== lastEventsSig) {
        lastEventsSig = curEventsSig;
        if (s.events && s.events.length > 0) {
          const term = document.getElementById('log-terminal');
          const shouldScroll = term.scrollTop + term.clientHeight >= term.scrollHeight - 30;
          let logHtml = '';
          s.events.forEach(ev => {
            let badgeColor = 'text-slate-400';
            if (ev.event === 'ENTRY') badgeColor = 'text-emerald-400 font-bold';
            else if (ev.event === 'CLOSE') badgeColor = 'text-amber-400 font-bold';
            else if (ev.event === 'PANIC') badgeColor = 'text-rose-500 font-bold';
            logHtml += `<div class="leading-relaxed"><span class="text-slate-500">${ev.time}</span> <span class="${badgeColor}">${ev.event}</span> ${ev.side || ''} ${ev.detail || ''} <span class="text-slate-400">${ev.price > 0 ? '@' + ev.price.toFixed(2) : ''}</span></div>`;
          });
          term.innerHTML = logHtml;
          if (shouldScroll) term.scrollTop = term.scrollHeight;
        }
      }"""

assert target_terminal in text, "target_terminal not found"
text = text.replace(target_terminal, replace_terminal, 1)

# 7. Win Rate Matrix diffing
target_wr = """      // Win Rate & Performance Matrix
      if (s.win_rate_stats) {
        updateWinRateMatrix(s.win_rate_stats);
      }"""

replace_wr = """      // Win Rate & Performance Matrix (Diffed)
      if (s.win_rate_stats) {
        const wr = s.win_rate_stats;
        const curWrSig = `${wr.today?.total}_${wr.today?.pnl}_${wr.yesterday?.total}_${wr.this_week?.total}`;
        if (curWrSig !== lastWrSig) {
          lastWrSig = curWrSig;
          updateWinRateMatrix(wr);
        }
      }"""

assert target_wr in text, "target_wr not found"
text = text.replace(target_wr, replace_wr, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("templates/index.html successfully patched with DOM diffing and leak guards!")
