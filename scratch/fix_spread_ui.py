with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

target = "document.getElementById('txt-spread').innerText = `$${s.market.spread.toFixed(2)}`;"
replacement = """const sprEl = document.getElementById('txt-spread');
        if (sprEl) {
          sprEl.innerText = `$${s.market.spread.toFixed(2)}`;
          const maxSpr = (s.config && s.config.max_spread) ? s.config.max_spread : 0.50;
          if (maxSpr > 0 && s.market.spread > maxSpr) {
            sprEl.className = 'text-rose-600 dark:text-rose-400 font-black animate-pulse';
            sprEl.title = `Spread $${s.market.spread.toFixed(2)} exceeds Max $${maxSpr.toFixed(2)}! Entries blocked.`;
          } else {
            sprEl.className = 'text-amber-600 dark:text-amber-400 font-bold';
            sprEl.title = 'Normal spread';
          }
        }"""

if target in html:
    html = html.replace(target, replacement, 1)
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Updated txt-spread alert logic in index.html successfully!")
else:
    print("target not found")

