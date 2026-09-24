/* RAW MATERIALS DAILY — card renderer
   window.renderPost(post, brand) -> { cards: n, warnings: [...] }
   Text markup: **강조** -> accent color,  \n -> line break
*/
(function () {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<span class="hl">$1</span>').replace(/\n/g, "<br>");
  const HANGUL = /([가-힣ㄱ-ㅎㅏ-ㅣ](?:[가-힣ㄱ-ㅎㅏ-ㅣ·\s?!.,]*[가-힣ㄱ-ㅎㅏ-ㅣ?!.])?)/g;
  const kz = (html) => html.replace(/(<[^>]+>)|([^<]+)/g, (m, tag, txt) => tag || txt.replace(HANGUL, '<span class="k">$1</span>'));
  const numP = (v) => esc(v).replace(/([,.])/g, '<span class="p">$1</span>');
  const DOW = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

  function dir(chg) {
    const s = String(chg ?? "").trim();
    if (!s) return "flat";
    if (s.startsWith("-") || s.startsWith("−") || s.startsWith("▼")) return "down";
    if (/^[+▲]/.test(s)) return "up";
    const n = parseFloat(s.replace(/[^0-9.\-]/g, ""));
    return !n ? "flat" : n > 0 ? "up" : "down";
  }
  function chgText(chg) {
    const d = dir(chg);
    const body = String(chg ?? "").trim().replace(/^[+\-−▲▼]\s*/, "");
    const arrow = d === "up" ? "▲" : d === "down" ? "▼" : "–";
    return { d, html: `${arrow} ${esc(body)}` };
  }
  const chgSpan = (chg, cls = "chg") => { const c = chgText(chg); return `<span class="${cls} ${c.d}">${c.html}</span>`; };

  function fmtNum(v, dec) {
    return Number(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  /* ---------- chart (drawn after layout, fits its container) ---------- */
  function drawChart(el, spec, accent) {
    const W = el.clientWidth, H = el.clientHeight;
    const vals = spec.values.map(Number);
    const labels = spec.labels || vals.map((_, i) => String(i + 1));
    const dec = spec.decimals ?? 0;
    const padL = 28, padR = 128, padT = 64, padB = 58;
    let lo = Math.min(...vals), hi = Math.max(...vals);
    // "nice" axis: step of 1/2/2.5/5 x 10^n, 4-6 gridlines
    const raw = (hi - lo || Math.abs(hi) || 1) / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((st) => st >= raw);
    lo = spec.yMin ?? Math.floor(lo / step) * step; hi = spec.yMax ?? Math.ceil(hi / step) * step;
    if (hi === lo) hi = lo + step;
    const nTicks = Math.round((hi - lo) / step);
    const tdec = Math.max(dec, Math.min(2, (String(+step.toFixed(6)).split(".")[1] || "").length));
    const x = (i) => padL + (i * (W - padL - padR)) / Math.max(1, vals.length - 1);
    const y = (v) => padT + ((hi - v) * (H - padT - padB)) / (hi - lo);
    const id = "g" + Math.random().toString(36).slice(2, 8);
    let g = "";
    // grid + y labels
    for (let k = 0; k <= nTicks; k++) {
      const v = lo + step * k, yy = y(v);
      g += `<line x1="${padL}" x2="${W - padR + 12}" y1="${yy}" y2="${yy}" stroke="#1F2733" stroke-width="1.5" ${k === 0 ? "" : 'stroke-dasharray="4 8"'}/>`;
      g += `<text x="${W - padR + 24}" y="${yy + 7}" font-family="InterLatin, Pretendard" font-size="20" fill="#7D8898">${fmtNum(v, tdec)}</text>`;
    }
    // x labels
    const xi = spec.xTicks || [0, Math.floor((vals.length - 1) / 2), vals.length - 1];
    xi.forEach((i) => {
      const anchor = i === 0 ? "start" : i === vals.length - 1 ? "end" : "middle";
      g += `<text x="${x(i)}" y="${H - 20}" text-anchor="${anchor}" font-family="InterLatin, Pretendard" font-size="20" fill="#7D8898">${esc(labels[i])}</text>`;
    });
    // annotations
    (spec.annotations || []).forEach((a) => {
      const xx = x(a.i);
      g += `<line x1="${xx}" x2="${xx}" y1="${padT - 14}" y2="${H - padB}" stroke="#4A5566" stroke-width="2" stroke-dasharray="6 6"/>`;
      g += `<text x="${xx + 10}" y="${padT - 22}" font-family="Pretendard" font-weight="700" font-size="22" fill="#B4BECB">${esc(a.text)}</text>`;
    });
    // area + line
    const pts = vals.map((v, i) => [x(i), y(v)]);
    const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const area = `${line} L ${pts[pts.length - 1][0]} ${H - padB} L ${pts[0][0]} ${H - padB} Z`;
    g = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${accent}" stop-opacity=".30"/><stop offset="1" stop-color="${accent}" stop-opacity="0"/></linearGradient></defs>` + g;
    g += `<path d="${area}" fill="url(#${id})"/>`;
    g += `<path d="${line}" fill="none" stroke="${accent}" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    // hi / lo markers
    const iHi = vals.indexOf(Math.max(...vals)), iLo = vals.indexOf(Math.min(...vals));
    [[iHi, "H", -18], [iLo, "L", 36]].forEach(([i, t, dy]) => {
      if (i === vals.length - 1) return;
      g += `<circle cx="${x(i)}" cy="${y(vals[i])}" r="6" fill="#0A0D12" stroke="#B4BECB" stroke-width="2.5"/>`;
      const anc = x(i) < padL + 80 ? "start" : "middle";
      g += `<text x="${x(i)}" y="${y(vals[i]) + dy}" text-anchor="${anc}" font-family="InterLatin, Pretendard" font-size="20" font-weight="700" fill="#B4BECB">${t} ${fmtNum(vals[i], dec)}</text>`;
    });
    // last point
    const [lx, ly] = pts[pts.length - 1];
    g += `<circle cx="${lx}" cy="${ly}" r="18" fill="${accent}" opacity=".22"/><circle cx="${lx}" cy="${ly}" r="8" fill="${accent}"/>`;
    const lastTxt = fmtNum(vals[vals.length - 1], dec);
    const bw = lastTxt.length * 14.5 + 28;
    g += `<rect x="${W - padR + 14}" y="${ly - 22}" width="${bw}" height="44" rx="6" fill="${accent}"/>`;
    g += `<text x="${W - padR + 28}" y="${ly + 8}" font-family="InterLatin, Pretendard" font-weight="800" font-size="23" fill="#0A0D12">${lastTxt}</text>`;
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${g}</svg>`;
  }

  function spark(values, accent, w = 330, h = 120) {
    const v = values.map(Number), lo = Math.min(...v), hi = Math.max(...v), s = hi - lo || 1;
    const p = v.map((n, i) => [(i * (w - 12)) / (v.length - 1) + 6, h - 8 - ((n - lo) * (h - 16)) / s]);
    const d = p.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
    const [lx, ly] = p[p.length - 1];
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${d}" fill="none" stroke="${accent}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${lx}" cy="${ly}" r="7" fill="${accent}"/></svg>`;
  }

  const ICON = {
    save: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M6 3h12v18l-6-4.5L6 21z"/></svg>',
    share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg>',
    follow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M19 8v6M16 11h6"/></svg>',
  };

  /* ---------- sources: every number/fact points to post.sources[].id ---------- */
  const ids = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]).filter(Boolean);
  const dot = (d) => String(d || "").replace(/-/g, ".");
  // collect every src id used on a slide (slide-level + item-level), in order of appearance
  function slideRefs(s) {
    const out = [...ids(s.src)];
    const add = (x) => ids(x && x.src).forEach((i) => out.push(i));
    add(s.ticker); (s.items || []).forEach(add); (s.rows || []).forEach(add); (s.bars || []).forEach(add); (s.facts || []).forEach(add); (s.viz || []).forEach(add);
    (s.groups || []).forEach((g) => (g.rows || []).forEach(add));
    return [...new Set(out)];
  }
  // small [n] marker next to an item, shown only when the slide mixes 2+ sources
  const ref = (x, ctx) => {
    if (!ctx.multi) return "";
    const ns = ids(x && x.src).map((i) => ctx.S[i]?.n ?? "?");
    return ns.length ? `<sup class="ref">[${ns.join(",")}]</sup>` : "";
  };
  function srcLine(list, ctx, need, compact) {
    if (!list.length) return need ? `<div class="src missing"><b>SOURCE</b><span>출처 누락 — 게시 불가</span></div>` : "";
    const bad = list.filter((i) => !ctx.S[i]);
    if (bad.length) return `<div class="src missing"><b>SOURCE</b><span>등록되지 않은 출처 ID: ${esc(bad.join(", "))}</span></div>`;
    if (compact) {
      const groups = [];
      [...list].sort((a, b) => ctx.S[a].n - ctx.S[b].n).forEach((i) => {
        const x = ctx.S[i], key = [x.publisher, x.via, x.date].join("|");
        const g = groups.find((q) => q.key === key);
        g ? g.ns.push(x.n) : groups.push({ key, x, ns: [x.n] });
      });
      const txt = groups.map((g) => `<em>${g.ns.map((n) => `[${n}]`).join("")}</em> ${esc(g.x.publisher)}${g.x.via ? ` (via ${esc(g.x.via)})` : ""} · ${dot(g.x.date)}`).join('<i class="sep"></i>');
      return `<div class="src"><b>SOURCE</b><span>${txt}</span></div>`;
    }
    list = [...list].sort((a, b) => ctx.S[a].n - ctx.S[b].n);
    const one = list.length === 1;
    const txt = list.map((i) => { const x = ctx.S[i];
      return `<em>[${x.n}]</em> ${esc(x.publisher)}${x.via ? ` (via ${esc(x.via)})` : ""}${one ? ` · ${esc(x.title)}` : ""} · ${dot(x.date)}`; }).join('<i class="sep"></i>');
    return `<div class="src"><b>SOURCE</b><span>${txt}</span></div>`;
  }

  /* ---------- slide bodies ---------- */
  const label = (s) => (s.label ? `<div class="label">${kz(md(s.label))}</div>` : "");
  const head = (s) => `${label(s)}${s.headline ? `<div class="h1">${md(s.headline)}</div>` : ""}${s.sub ? `<div class="sub">${md(s.sub)}</div>` : ""}`;


  /* ---------- VIZ: data-driven visual blocks for news slides ---------- */
  const DAY = 86400000;
  const dparse = (d) => new Date(String(d) + "T00:00:00Z");
  const ddiff = (a, b) => Math.round((dparse(b) - dparse(a)) / DAY);
  const mmdd = (d) => String(d).slice(5).replace("-", ".");
  const calcTag = (x) => (x && x.calc ? '<span class="calc">계산값</span>' : x && x.est ? '<span class="calc est">추정</span>' : "");
  const vhead = (v, ctx) => (v.title ? `<div class="vh"><span>${kz(esc(v.title))}</span>${ref(v, ctx)}</div>` : "");
  const VIZ = {
    status(v, ctx) {
      const items = (v.items || []).map((it) => `<div class="st-i ${esc(it.tone || "")}"><div class="st-k">${kz(esc(it.k))}</div><div class="st-v">${md(it.v)}</div>${it.sub ? `<div class="st-s">${md(it.sub)}</div>` : ""}</div>`).join("");
      return `${vhead(v, ctx)}<div class="stt" style="grid-template-columns: repeat(${(v.items || []).length || 1}, minmax(0, 1fr))">${items}</div>`;
    },
    stats(v, ctx) {
      const items = (v.items || []).map((it) => `<div class="kpi ${it.hi ? "hi" : ""}"><div class="kv">${esc(it.value)}${it.unit ? `<small>${esc(it.unit)}</small>` : ""}</div><div class="kl">${kz(esc(it.label))}${calcTag(it)}</div></div>`).join("");
      return `${vhead(v, ctx)}<div class="kpis" style="grid-template-columns: repeat(${(v.items || []).length || 1}, minmax(0, 1fr))">${items}</div>`;
    },
    split(v, ctx) {
      const total = (v.parts || []).reduce((a, p) => a + Number(p.value), 0) || 1;
      const shades = ["var(--accent)", "#8D97A6", "#4A5566", "#2B3441"];
      const segs = (v.parts || []).map((p, i) => `<div class="sp-s" style="width:${(Number(p.value) / total) * 100}%; background:${shades[i] || shades[3]}"></div>`).join("");
      const labs = (v.parts || []).map((p, i) => `<div class="sp-l" style="width:${(Number(p.value) / total) * 100}%"><i style="background:${shades[i] || shades[3]}"></i><b>${esc(p.value)}${esc(v.unit || "")}${p.calc ? "*" : ""}</b><span>${esc(p.label)}</span></div>`).join("");
      const leg = (v.parts || []).map((p, i) => `<div class="sp-g"><i style="background:${shades[i] || shades[3]}"></i><span>${esc(p.label)}</span><b>${esc(p.value)}${esc(v.unit || "")}${p.calc ? "*" : ""}</b></div>`).join("");
      return `${vhead(v, ctx)}<div class="sp">${segs}</div>${v.half ? `<div class="sp-gs">${leg}</div>` : `<div class="sp-ls">${labs}</div>`}${v.note ? `<div class="vnote">${md(v.note)}</div>` : ""}`;
    },
    timeline(v, ctx) {
      const span = ddiff(v.start, v.end) || 1;
      const pos = (d) => Math.max(0, Math.min(100, (ddiff(v.start, d) / span) * 100));
      const sp = v.span ? `<div class="tl-span" style="left:${pos(v.span.from)}%; width:${pos(v.span.to) - pos(v.span.from)}%">${v.span.label ? `<span>${kz(esc(v.span.label))}</span>` : ""}</div>` : "";
      const ev = (v.events || []).map((e, i) => {
        const x = pos(e.d), side = i % 2 ? "b" : "t";
        const al = x > 85 ? "r" : x < 15 ? "l" : "c";
        return `<div class="tl-e ${side} ${al} ${e.hi ? "hi" : ""}" style="left:${x}%"><i></i><div class="tl-t"><b>${mmdd(e.d)}</b>${kz(esc(e.t))}</div></div>`;
      }).join("");
      return `${vhead(v, ctx)}<div class="tl"><div class="tl-line"></div>${sp}${ev}</div>`;
    },
    calendar(v, ctx) {
      const n = v.days || 14, cols = `repeat(${n}, minmax(0, 1fr))`;
      const days = Array.from({ length: n }, (_, i) => new Date(dparse(v.start).getTime() + i * DAY));
      const head = days.map((d) => {
        const iso = d.toISOString().slice(0, 10);
        return `<span class="${iso === v.today ? "today" : ""} ${d.getUTCDate() === 1 ? "m1" : ""}">${String(d.getUTCDate()).padStart(2, "0")}</span>`;
      }).join("");
      const months = [];
      days.forEach((d, i) => { if (i === 0 || d.getUTCDate() === 1) months.push({ i, m: d.toLocaleString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase() }); });
      const mrow = months.map((m, k) => `<span style="grid-column:${m.i + 1} / ${(months[k + 1] ? months[k + 1].i : n) + 1}">${m.m}</span>`).join("");
      const rows = (v.rows || []).map((r) => {
        const bars = (r.bars || []).map((b) => {
          const a = Math.max(0, ddiff(v.start, b.from)), z = Math.min(n - 1, ddiff(v.start, b.to));
          if (z < 0 || a > n - 1) return "";
          return `<div class="cb ${esc(b.kind || "on")}" style="grid-column:${a + 1} / ${z + 2}"><span>${kz(esc(b.label || ""))}</span></div>`;
        }).join("");
        const ti = v.today ? ddiff(v.start, v.today) : -1;
        const tmark = ti >= 0 && ti < n ? `<div class="ct" style="grid-column:${ti + 1} / ${ti + 2}"></div>` : "";
        return `<div class="cr"><div class="cr-h"><b>${esc(r.label)}</b>${r.sub ? `<span>${kz(esc(r.sub))}</span>` : ""}${ref(r, ctx)}</div><div class="cg" style="grid-template-columns:${cols}; background-size: calc(100% / ${n}) 100%">${tmark}${bars}</div></div>`;
      }).join("");
      const legend = (v.legend || []).map((l) => `<span><i class="cb ${esc(l.kind)}"></i><em>${kz(esc(l.t))}</em></span>`).join("");
      return `${vhead(v, ctx)}<div class="cal"><div class="cm" style="grid-template-columns:${cols}">${mrow}</div><div class="cd" style="grid-template-columns:${cols}">${head}</div>${rows}</div>${legend ? `<div class="cl">${legend}</div>` : ""}${v.note ? `<div class="vnote">${md(v.note)}</div>` : ""}`;
    },
    gauge(v, ctx) {
      const max = v.max || 100, a = (Number(v.from) / max) * 100, b = (Number(v.to ?? v.from) / max) * 100;
      return `${vhead(v, ctx)}<div class="gg"><div class="gg-bar"><div class="gg-f" style="width:${a}%"></div><div class="gg-r" style="left:${a}%; width:${b - a}%"></div></div>
        <div class="gg-v"><b>${esc(v.display || "")}</b>${v.label ? `<span>${kz(esc(v.label))}</span>` : ""}</div></div>`;
    },
  };
  const renderViz = (list, ctx) => (list || []).map((v) => `<div class="viz v-${esc(v.type)} ${v.half ? "half" : ""}">${(VIZ[v.type] || (() => ""))(v, ctx)}</div>`).join("");
  const plain = (t) => String(t || "").replace(/\*\*/g, "").replace(/\n/g, " ");
  function outletLine(s, ctx) {
    const x = ctx.S[ids(s.src)[0]];
    if (!x) return "";
    const MON = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
    const [yy, mm, dd] = String(x.date || "").split("-");
    const when = [dd && mm ? `${Number(dd)} ${MON[Number(mm) - 1]} ${yy}` : "", x.time].filter(Boolean).join(" · ");
    return `<div class="outlet"><span class="ob">${esc(x.publisher)}</span>${x.via ? `<span class="via">via ${esc(x.via)}</span>` : ""}<span class="ot">${esc(when)}</span></div>`;
  }
  function toc(ctx) {
    const news = ctx.post.slides.map((x, i) => ({ x, i })).filter((o) => o.x.type === "news");
    if (!news.length) return "";
    return `<div class="toc">${news.map((o, k) => {
      const cat = ctx.brand.categories[o.x.category || ctx.post.category] || {};
      const src = ctx.S[ids(o.x.src)[0]] || {};
      return `<div class="toc-i" style="--gc:${cat.accent || "#fff"}"><span class="tn">${String(k + 1).padStart(2, "0")}</span>
        <div><div class="tc">${esc(cat.ko || "")}<span>${esc(src.publisher || "")}</span></div><div class="th">${esc(o.x.toc || plain(o.x.headline))}</div></div>
        ${o.x.key ? `<div class="tk"><b>${esc(o.x.key.value)}</b><span>${kz(esc(o.x.key.label || ""))}</span></div>` : "<div></div>"}</div>`;
    }).join("")}</div>`;
  }

  const BODY = {
    news(s, ctx) {
      const facts = (s.facts || []).map((f) => `<li><span class="fd"></span><div>${md(f.t)}${ref(f, ctx)}</div></li>`).join("");
      return `${outletLine(s, ctx)}
        <div class="h1 news-h">${md(s.headline)}</div>
        ${s.orig ? `<div class="orig">“${esc(s.orig)}”</div>` : ""}
        ${s.viz ? `<div class="vizs">${renderViz(s.viz, ctx)}</div>` : ""}
        ${facts ? `<ul class="facts">${facts}</ul>` : ""}
        <div class="spacer"></div>
        ${s.why ? `<div class="why"><div class="wk"><span class="k">구매 관점</span><span class="op">의견</span></div><div class="wt">${md(s.why)}</div></div>` : ""}
        ${srcLine(ctx.refs, ctx, ctx.need, true)}`;
    },
    cover(s, ctx) {
      const t = s.ticker;
      return `
        ${s.kicker ? `<div class="kicker">${kz(esc(s.kicker))}</div>` : ""}
        <div class="title">${md(s.title)}</div>
        ${s.sub ? `<div class="sub">${md(s.sub)}</div>` : ""}
        ${s.points ? `<div class="points">${s.points.map((x, i) => `<span><b>${String(i + 1).padStart(2, "0")}</b>${esc(x)}</span>`).join("")}</div>` : ""}
        <div class="spacer"></div>
        ${s.toc ? `<div class="toc-h"><span>IN THIS ISSUE</span><span>${kz("뉴스 " + ctx.post.slides.filter((x) => x.type === "news").length + "건")}</span></div>${toc(ctx)}` : ""}
        ${t ? `<div class="ticker"><div>
            <div class="t-label">${kz(esc(t.label))}</div>
            <div class="t-val">${numP(t.value)}${t.unit ? `<small>${esc(t.unit)}</small>` : ""}</div>
            ${t.chg ? `<div class="t-chg">${chgSpan(t.chg, "chg-badge")}${t.vs ? `<span>${esc(t.vs)}</span>` : ""}</div>` : ""}
          </div>${t.spark ? spark(t.spark, ctx.accent) : ""}</div>
          <div class="t-src">${srcLine(ids(t.src), ctx, true)}</div>` : ""}
        `;
    },
    number(s, ctx) {
      return `${head(s)}
        <div class="big"><span class="v">${numP(s.value)}</span>${s.unit ? `<span class="u">${esc(s.unit)}</span>` : ""}
          ${s.chg ? chgSpan(s.chg, "chg-badge") : ""}${s.vs ? `<span class="vs">${esc(s.vs)}</span>` : ""}</div>
        ${s.chart ? `<div class="chart" data-chart='${esc(JSON.stringify(s.chart))}'></div>` : '<div class="spacer"></div>'}
        ${s.note ? `<div class="note">${md(s.note)}</div>` : ""}
        ${srcLine(ctx.refs, ctx, ctx.need)}`;
    },
    bullets(s, ctx) {
      const items = (s.items || []).map((it, i) => `
        <div class="item"><div class="n">${String(i + 1).padStart(2, "0")}</div>
          <div><div class="t">${md(it.title)}${ref(it, ctx)}${it.tag ? `<span class="tag">${esc(it.tag)}</span>` : ""}</div>
          ${it.desc ? `<div class="d">${md(it.desc)}</div>` : ""}</div></div>`).join("");
      return `${head(s)}<div class="items">${items}</div><div class="spacer"></div>
        ${s.note ? `<div class="note">${md(s.note)}</div>` : ""}${srcLine(ctx.refs, ctx, ctx.need)}`;
    },
    table(s, ctx) {
      const cols = s.columns || [];
      const th = cols.map((c) => `<th class="${c.num ? "num" : ""}">${kz(esc(c.name))}</th>`).join("");
      const rows = (s.rows || []).map((r) => {
        const cells = r.cells || r;
        const td = cells.map((v, j) => {
          const c = cols[j] || {};
          if (c.chg) return `<td class="num">${chgSpan(v)}</td>`;
          const [main, subtxt] = String(v ?? "").split("|");
          return `<td class="${c.num ? "num" : ""}">${md(main)}${j === 0 ? ref(r, ctx) : ""}${subtxt ? `<span class="muted">${md(subtxt)}</span>` : ""}</td>`;
        }).join("");
        return `<tr class="${r.hi ? "hi" : ""}">${td}</tr>`;
      }).join("");
      return `${head(s)}<table class="tbl"><thead><tr>${th}</tr></thead><tbody>${rows}</tbody></table>
        <div class="spacer"></div>${s.note ? `<div class="note">${md(s.note)}</div>` : ""}${srcLine(ctx.refs, ctx, ctx.need)}`;
    },
    bars(s, ctx) {
      const max = s.max ?? Math.max(...s.bars.map((b) => Number(b.value)));
      const bars = s.bars.map((b) => `
        <div class="bar ${b.hi ? "hi" : ""}"><div class="bl">${md(b.label)}${ref(b, ctx)}${b.sub ? `<small>${esc(b.sub)}</small>` : ""}</div>
          <div class="track"><div class="fill" style="width:${Math.max(1.5, (Number(b.value) / max) * 100)}%"></div></div>
          <div class="bv">${esc(b.display ?? b.value)}</div></div>`).join("");
      return `${head(s)}<div class="bars">${bars}</div>${s.unit ? `<div class="bars-unit">${kz(esc(s.unit))}</div>` : ""}
        <div class="spacer"></div>${s.note ? `<div class="note">${md(s.note)}</div>` : ""}${srcLine(ctx.refs, ctx, ctx.need)}`;
    },
    insight(s, ctx) {
      const lv = { low: 1, mid: 2, high: 3 }[s.impact] || 0;
      const lvTxt = ["", "낮음", "중간", "높음"][lv];
      const imp = lv ? `<div class="impact"><span class="il">원가 영향도</span>
          <span class="seg">${[1, 2, 3].map((k) => `<i class="${k <= lv ? "on" : ""}"></i>`).join("")}</span>
          <span class="iv">${lvTxt}</span><span class="op">의견</span></div>` : "";
      const blocks = (s.blocks || []).map((b) => `<div class="block"><div class="bk">${kz(esc(b.k))}</div><div class="bt">${md(b.t)}</div></div>`).join("");
      return `${head(s)}${imp}<div class="blocks">${blocks}</div><div class="spacer"></div>
        ${s.note ? `<div class="note">${md(s.note)}</div>` : ""}${srcLine(ctx.refs, ctx, false)}`;
    },
    board(s, ctx) {
      const grps = (s.groups || []).map((g) => {
        const cat = ctx.brand.categories[g.category] || {};
        const rows = g.rows.map((r) => `<div class="row"><div class="rn">${esc(r.name)}${r.unit ? `<small>${esc(r.unit)}</small>` : ""}${ref(r, ctx)}</div>
            <div class="rv">${esc(r.value)}</div><div class="rc">${chgSpan(r.chg)}</div></div>`).join("");
        return `<div class="grp" style="--gc:${cat.accent || "#fff"}"><div class="grp-h"><i></i><span>${esc(cat.en || g.category)}</span><span class="ko">${esc(cat.ko || "")}</span></div>${rows}</div>`;
      }).join("");
      return `${head(s)}${s.asof ? `<div class="asof">AS OF ${kz(esc(s.asof))}</div>` : ""}<div class="board">${grps}</div>
        <div class="spacer"></div>${s.note ? `<div class="note">${md(s.note)}</div>` : ""}${srcLine(ctx.refs, ctx, ctx.need)}`;
    },
    closing(s, ctx) {
      const list = (ctx.post.sources || []).map((x, i) => `<li><div class="sn">[${i + 1}]</div><div>
          <div class="st"><b>${esc(x.publisher)}</b>${x.via ? ` <span class="vv">via ${esc(x.via)}</span>` : ""} — ${esc(x.title)}</div>
          <div class="sd"><span class="k">게재</span> ${dot(x.date)}${x.time ? ` ${esc(x.time)}` : ""}${x.accessed ? ` · <span class="k">확인</span> ${dot(x.accessed)}` : ""}${x.url ? ` · <span class="u">${esc(x.url.replace(/^https?:\/\//, ""))}</span>` : ""}</div></div></li>`).join("");
      const missing = !(ctx.post.sources || []).length ? `<div class="src missing"><b>SOURCE</b><span>출처 목록 없음 — 게시 불가</span></div>` : "";
      return `<div class="label">SOURCES <span class="ko">이번 호 출처</span></div><ul class="srcs">${list}</ul>${missing}
        <div class="disc">${md(s.disclaimer || ctx.brand.disclaimer)}</div>
        <div class="spacer"></div>
        ${s.next ? `<div class="next"><b>NEXT</b><span>${md(s.next)}</span></div>` : ""}
        <div class="cta"><div class="cq">${md(s.cta || ctx.brand.tagline)}</div>
          <div class="cm2"><b>${esc(ctx.brand.handle)}</b>${ctx.brand.editor_note ? `<span>${esc(ctx.brand.editor_note)}</span>` : ""}</div></div>`;
    },
  };

  window.renderPost = function (post, brand) {
    const root = document.getElementById("root");
    root.innerHTML = "";
    const W = brand.size?.width || 1080, H = brand.size?.height || 1350;
    document.documentElement.style.setProperty("--W", W + "px");
    document.documentElement.style.setProperty("--H", H + "px");
    if (brand.color_convention === "global") document.body.classList.add("cv-global");
    const need = new Set(brand.rules?.source_required_types || []);
    const d = new Date(post.date + "T00:00:00");
    const dateTxt = `${post.date.replace(/-/g, ".")} ${DOW[d.getDay()]}`;
    const N = post.slides.length;
    const warnings = [];
    const S = {};
    (post.sources || []).forEach((x, i) => { if (x.id) S[x.id] = { ...x, n: i + 1 }; });

    post.slides.forEach((s, idx) => {
      const catKey = s.category || post.category;
      const cat = brand.categories[catKey] || {};
      const top = catKey === "brief" ? {} : (brand.topics[s.topic || post.topic] || {});
      const accent = cat.accent || "#FB923C";
      const refs = slideRefs(s);
      const ctx = { brand, post, accent, need: need.has(s.type), S, refs, multi: refs.length > 1 };
      const card = document.createElement("section");
      card.className = `card t-${s.type}`;
      card.style.setProperty("--accent", accent);
      card.innerHTML = `
        <header class="hd"><div class="brand">${esc(brand.series)}</div>
          <div class="date">${post.issue ? `No.${String(post.issue).padStart(3, "0")} · ` : ""}${dateTxt}</div></header>
        <div class="meta"><span class="mk"></span><span class="mc">${esc(cat.ko || "")}</span><span class="me">${esc(cat.en || catKey)}</span>
          ${top.ko ? `<span class="ms">/</span><span class="mt">${esc(top.ko)}</span>` : ""}${s.update_of ? `<span class="ms">/</span><span class="mu">후속 보도</span>` : ""}</div>
        ${post.sample ? '<div class="stamp">SAMPLE · <span class="ko">가상 데이터</span></div>' : ""}
        <div class="body">${(BODY[s.type] || (() => `<div class="h1">Unknown type: ${esc(s.type)}</div>`))(s, ctx)}</div>
        <footer class="ft"><div class="ft-row"><div class="handle">${esc(brand.handle)}<em>${esc(brand.editor || brand.series_ko)}</em></div>
          <div class="page">${idx + 1} / ${N}</div></div></footer>`;
      root.appendChild(card);
      if (ctx.need && !refs.length) warnings.push(`slide ${idx + 1} (${s.type}): src 누락`);
      refs.filter((i) => !S[i]).forEach((i) => warnings.push(`slide ${idx + 1}: 등록되지 않은 출처 ID "${i}"`));
    });

    // auto-fit: tighten density on cards whose content overflows
    document.querySelectorAll(".card").forEach((card) => {
      const body = card.querySelector(".body");
      if (body.scrollHeight > body.clientHeight + 2) card.classList.add("dense");
      if (body.scrollHeight > body.clientHeight + 2) card.classList.add("denser");
    });
    // auto-fit (반대 방향): 여백이 크게 남는 카드는 글자·그래픽을 키운다 (3:4 캔버스 대응)
    document.querySelectorAll(".card").forEach((card) => {
      const body = card.querySelector(".body");
      const sp = card.querySelector(".body > .spacer");
      if (!sp || card.classList.contains("dense")) return;
      if (sp.offsetHeight > 260) {
        card.classList.add("roomy");
        if (body.scrollHeight > body.clientHeight + 2) card.classList.remove("roomy");
      }
    });

    // draw charts after layout
    document.querySelectorAll(".chart[data-chart]").forEach((el) => {
      const accent = getComputedStyle(el.closest(".card")).getPropertyValue("--accent").trim();
      drawChart(el, JSON.parse(el.dataset.chart), accent);
    });

    // overflow QA
    document.querySelectorAll(".card").forEach((card, i) => {
      const body = card.querySelector(".body");
      if (body.scrollHeight > body.clientHeight + 2) warnings.push(`slide ${i + 1}: 내용이 카드 높이를 ${body.scrollHeight - body.clientHeight}px 초과`);
      card.querySelectorAll(".body *").forEach((el) => {
        if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflow !== "visible" && !el.classList.contains("su") && !el.classList.contains("sd"))
          warnings.push(`slide ${i + 1}: 가로 넘침 <${el.className}>`);
      });
    });
    return { cards: N, warnings };
  };
})();
