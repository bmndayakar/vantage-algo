import os

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update the Daily Goal block in updateUI
target_goal = """        const pct = Math.min(Math.max((b.daily / goal) * 100, 0), 100);
        document.getElementById('bar-daily-progress').style.width = `${pct}%`;
        document.getElementById('txt-daily-pct').innerText = `${pct.toFixed(0)}%`;
        if (b.daily >= goal) {
          document.getElementById('txt-goal-status').innerText = '🎉 Daily Goal Achieved!';
          document.getElementById('txt-goal-status').className = 'text-emerald-600 dark:text-emerald-400 font-semibold';
        } else {
          document.getElementById('txt-goal-status').innerText = 'Trading in progress';
          document.getElementById('txt-goal-status').className = 'text-slate-400 dark:text-slate-500';
        }"""

replacement_goal = """        const pct = Math.min(Math.max((b.daily / goal) * 100, 0), 100);
        document.getElementById('bar-daily-progress').style.width = `${pct}%`;
        document.getElementById('txt-daily-pct').innerText = `${pct.toFixed(0)}%`;

        const goalStatusEl = document.getElementById('txt-goal-status');
        if (goalStatusEl) {
          if (b.daily >= goal) {
            goalStatusEl.innerText = '🎉 Goal Achieved!';
            goalStatusEl.className = 'text-emerald-600 dark:text-emerald-400 font-semibold';
          } else {
            goalStatusEl.innerText = 'Trading in progress';
            goalStatusEl.className = 'text-slate-400 dark:text-slate-500';
          }
        }

        const todayBrokerEl = document.getElementById('txt-today-broker');
        if (todayBrokerEl) {
          const dayPnl = (b.broker_daily !== undefined) ? b.broker_daily : b.daily;
          const dayDeals = (b.broker_deals !== undefined) ? b.broker_deals : b.deals;
          todayBrokerEl.innerText = `Day: ${dayPnl >= 0 ? '+' : ''}$${Number(dayPnl).toFixed(2)} (${dayDeals})`;
        }"""

assert target_goal in text, "target_goal not found in index.html"
text = text.replace(target_goal, replacement_goal)

# 2. Add resetSessionGoal and improve setHistoryPeriod
target_fn = """    function setHistoryPeriod(period) {
      fetch('/api/history_period', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period: period })
      })"""

replacement_fn = """    function resetSessionGoal() {
      fetch('/api/reset_goal', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
          const pEl = document.getElementById('txt-daily-profit');
          if (pEl) pEl.innerText = '$0.00';
          const dEl = document.getElementById('txt-deals-count');
          if (dEl) dEl.innerText = '0 Deals';
          const bEl = document.getElementById('bar-daily-progress');
          if (bEl) bEl.style.width = '0%';
          const pctEl = document.getElementById('txt-daily-pct');
          if (pctEl) pctEl.innerText = '0%';
        })
        .catch(e => console.error('Failed to reset session goal:', e));
    }

    function setHistoryPeriod(period) {
      updateHistoryPeriodButtons(period);
      fetch('/api/history_period', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period: period })
      })"""

assert target_fn in text, "target_fn not found in index.html"
text = text.replace(target_fn, replacement_fn)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated index.html JS successfully!")

