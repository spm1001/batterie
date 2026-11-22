/* dragram — connectors + drag + (edit-only) pan/zoom.
 *
 * Jobs:
 *   1. Draw connectors from the declared edge list (#edges) using LIVE box geometry, so
 *      arrows follow whatever positions the boxes currently have. Runs always.
 *   2. If ?edit: make .node elements draggable; drops persist left/top to the .html via
 *      POST /save (serve.py). Placement = positional; topology = declarative; the file is
 *      the single shared artefact.
 *   3. If ?edit: pan/zoom the canvas (it's a fixed 1720×1080 stage, bigger than most windows).
 *      Wheel = zoom toward cursor; drag empty space = pan; f/0 = fit; +/- = zoom; HUD shows %.
 *      All of this is editor chrome ONLY — read-only (render) mode applies no transform, so
 *      the headless screenshot captures the stage at native size.
 *   4. Relational alignment (runs always; gestures only under ?edit). A block may say that one
 *      of its lines sits on another block's line — data-align-x="center:analyst.center",
 *      data-align-y="top:report.top". Dragging near another block's edge or centre snaps to it
 *      and RECORDS that relation; the grid is the root anchor, so dropping on plain grid clears
 *      it. Detaching is re-aligning: there is no unlink gesture. Alt-drag = free, no relation.
 *   5. If ?edit: resize by grabbing a block's edge — width always, height only where the file
 *      states one; content reflows and is never squeezed further than the file already had it.
 */
(function () {
  "use strict";

  const stage = document.querySelector(".stage");
  const viewport = document.querySelector(".viewport");
  const SVGNS = "http://www.w3.org/2000/svg";
  // A fixture that forgets the wires layer or the edge list used to throw here and silently
  // draw nothing (drag-tohuvi). Mint the layer instead, and say so in the state contract.
  const mintedWires = !document.getElementById("wires");
  const svg = document.getElementById("wires") || (() => {
    const w = document.createElementNS(SVGNS, "svg");
    w.id = "wires";
    w.setAttribute("style", `position:absolute; left:0; top:0; width:${stage.offsetWidth}px; ` +
                            `height:${stage.offsetHeight}px; z-index:1; pointer-events:none;`);
    stage.appendChild(w);
    console.warn("dragram: no <svg id=\"wires\"> in the file — minted one at runtime");
    return w;
  })();
  const edgesEl = document.getElementById("edges");
  const edges = edgesEl ? JSON.parse(edgesEl.textContent) : [];
  if (!edgesEl) console.warn("dragram: no #edges block — drawing no connectors");
  // Keylines paint under the wires whatever order the author's CSS rules come in: a late
  // `.node { z-index:… }` rule used to lift a keyline over the wires inside it (drag-tohuvi).
  document.querySelectorAll(".keyline").forEach((k) => { k.style.zIndex = "0"; });
  const GRID = 20; // px grid — drag snaps to it (edit) and the on-grid contract checks it. 1720 & 1920 both divide by 20.
  // Edge classes: personal/aggregate are real flows (arrowhead); gated is a flow that is
  // *intended but legally blocked* — drawn red/dashed ending in a stop-bar "wall", not an arrow.
  const STROKE = { personal: "#2c3e50", aggregate: "#229954", gated: "#c0392b", muted: "#ced4da" };

  // ---- connectors (runs in every mode) ----
  function ensureDefs() {
    if (svg.querySelector("defs")) return;
    const defs = document.createElementNS(SVGNS, "defs");
    // marker shape per class: arrowhead for flows, a perpendicular stop-bar for gated (blocked).
    const SHAPE = {
      personal:  { d: "M0,0 L7,3 L0,6 Z",          w: 9, h: 9,  rx: 7, ry: 3 },
      aggregate: { d: "M0,0 L7,3 L0,6 Z",          w: 9, h: 9,  rx: 7, ry: 3 },
      gated:     { d: "M0,1 L3,1 L3,11 L0,11 Z",   w: 6, h: 12, rx: 1, ry: 6 },
    };
    for (const [name, color] of Object.entries(STROKE)) {
      const s = SHAPE[name] || SHAPE.personal;
      const m = document.createElementNS(SVGNS, "marker");
      m.setAttribute("id", "ah-" + name);
      m.setAttribute("markerWidth", s.w); m.setAttribute("markerHeight", s.h);
      m.setAttribute("refX", s.rx); m.setAttribute("refY", s.ry);
      m.setAttribute("orient", "auto-start-reverse"); m.setAttribute("markerUnits", "userSpaceOnUse");
      const p = document.createElementNS(SVGNS, "path");
      p.setAttribute("d", s.d); p.setAttribute("fill", color);
      m.appendChild(p); defs.appendChild(m);
    }
    svg.appendChild(defs);
  }

  const box = (el) => ({ x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight });

  function endpoints(a, b) {
    const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
    const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
    const dx = bc.x - ac.x, dy = bc.y - ac.y;
    let p1, p2, d1, d2;
    if (Math.abs(dx) >= Math.abs(dy)) {
      if (dx >= 0) { p1 = { x: a.x + a.w, y: ac.y }; d1 = { x: 1, y: 0 };
                     p2 = { x: b.x, y: bc.y };        d2 = { x: -1, y: 0 }; }
      else         { p1 = { x: a.x, y: ac.y };        d1 = { x: -1, y: 0 };
                     p2 = { x: b.x + b.w, y: bc.y };   d2 = { x: 1, y: 0 }; }
    } else {
      if (dy >= 0) { p1 = { x: ac.x, y: a.y + a.h };  d1 = { x: 0, y: 1 };
                     p2 = { x: bc.x, y: b.y };         d2 = { x: 0, y: -1 }; }
      else         { p1 = { x: ac.x, y: a.y };         d1 = { x: 0, y: -1 };
                     p2 = { x: bc.x, y: b.y + b.h };    d2 = { x: 0, y: 1 }; }
    }
    return { p1, p2, d1, d2 };
  }

  function renderWires() {
    ensureDefs();
    svg.querySelectorAll("path.wire").forEach((n) => n.remove());
    for (const e of edges) {
      const sa = document.getElementById(e.from), sb = document.getElementById(e.to);
      if (!sa || !sb) { console.warn("edge skipped, missing node:", e); continue; }
      const { p1, p2, d1, d2 } = endpoints(box(sa), box(sb));
      const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      const k = Math.max(40, dist * 0.35);
      const c1 = { x: p1.x + d1.x * k, y: p1.y + d1.y * k };
      const c2 = { x: p2.x + d2.x * k, y: p2.y + d2.y * k };
      const cls = e.cls in STROKE ? e.cls : "personal";
      const path = document.createElementNS(SVGNS, "path");
      path.setAttribute("class", "wire");
      path.setAttribute("d", `M${p1.x},${p1.y} C${c1.x},${c1.y} ${c2.x},${c2.y} ${p2.x},${p2.y}`);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", STROKE[cls]);
      path.setAttribute("stroke-width", "2.6");
      if (cls === "aggregate" || cls === "gated") path.setAttribute("stroke-dasharray", "7 5");
      path.setAttribute("marker-end", `url(#ah-${cls})`);
      if (e.bidir) path.setAttribute("marker-start", `url(#ah-${cls})`);
      svg.appendChild(path);
    }
  }

  // ---- self-sizing keylines: a keyline's box = bbox of its declared members + padding.
  //      Members are listed in data-members="id id …". Runs in every mode (render too), so
  //      keyline geometry is DERIVED — its inline coords in the HTML are placeholders. ----
  const KPAD = 24, KPAD_TOP = 44; // side/bottom padding; extra at top for the keyline label
  const isGroup = (el) => el.classList.contains("keyline") && !!el.dataset.members;
  const membersOf = (k) => k.dataset.members.trim().split(/\s+/)
    .map((id) => document.getElementById(id)).filter(Boolean);
  function layoutKeyline(k, axis) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, any = false;
    for (const m of membersOf(k)) {
      any = true;
      x0 = Math.min(x0, m.offsetLeft); y0 = Math.min(y0, m.offsetTop);
      x1 = Math.max(x1, m.offsetLeft + m.offsetWidth);
      y1 = Math.max(y1, m.offsetTop + m.offsetHeight);
    }
    if (!any) return;
    if (axis !== "y") { k.style.left = (x0 - KPAD) + "px"; k.style.width = (x1 - x0 + 2 * KPAD) + "px"; }
    if (axis !== "x") { k.style.top = (y0 - KPAD_TOP) + "px"; k.style.height = (y1 - y0 + KPAD_TOP + KPAD) + "px"; }
  }

  // ---- relational alignment. Per axis, a block names one of its own lines and one line of an
  //      anchor block: x lines left|center|right, y lines top|middle|bottom. Solved from LIVE
  //      geometry on every relayout, so content-driven heights are honoured. The inline left/top
  //      stays in the file as the fallback, used when the anchor is gone or the relation sits on a
  //      cycle — the block then sits at its last SAVED position, which for a hand-written
  //      relation may not be where it was last shown (drags keep it true; hand edits don't). Positions only: the solver never changes a
  //      size, and never changes which side of what a block sits on — the file said that. ----
  const LINES = { x: { left: 0, center: 0.5, right: 1 }, y: { top: 0, middle: 0.5, bottom: 1 } };
  const ALIGN_KEY = { x: "alignX", y: "alignY" }; // dataset keys for data-align-x / data-align-y
  const suspended = new Set(); // "id|axis" — relations a live gesture is overriding
  let alignReport = [];        // per-relation status, for the state contract

  function parseAlign(el, axis) {
    const raw = el.dataset[ALIGN_KEY[axis]];
    if (!raw) return null;
    const m = raw.trim().match(/^(\w+):(.+)\.(\w+)$/);
    if (!m || !(m[1] in LINES[axis]) || !(m[3] in LINES[axis])) return { raw, bad: true };
    return { raw, mine: m[1], target: m[2], theirs: m[3] };
  }
  const anchorOf = (a) => {
    const t = a && !a.bad ? document.getElementById(a.target) : null;
    return t && t.classList.contains("node") ? t : null;
  };
  // what an element's position on ONE axis depends on: a group on its members' positions on
  // that axis (a bbox's x comes only from its members' x), a block on its live anchor there.
  // Per axis, so "A centred on B, B's top on A's bottom" is two chains, not a false cycle.
  function deps(el, axis) {
    if (isGroup(el)) return membersOf(el);
    if (suspended.has(el.id + "|" + axis)) return [];
    const t = anchorOf(parseAlign(el, axis));
    return t ? [t] : [];
  }
  // everything whose position on axis (transitively) depends on el — it moves when el moves
  function dependantsOf(el, axis) {
    const rev = new Map();
    document.querySelectorAll(".node").forEach((n) => {
      for (const d of deps(n, axis)) { if (!rev.has(d)) rev.set(d, []); rev.get(d).push(n); }
    });
    const seen = new Set(), todo = [el];
    while (todo.length) for (const n of rev.get(todo.pop()) || []) if (!seen.has(n)) { seen.add(n); todo.push(n); }
    return seen;
  }
  const lineAt = (b, axis, name) => axis === "x" ? b.x + b.w * LINES.x[name] : b.y + b.h * LINES.y[name];

  function solveLayout() {
    alignReport = [];
    for (const axis of ["x", "y"]) solveAxis(axis);
  }
  function solveAxis(axis) {
    // topological order over deps, so an anchor (or a group's members) settle before dependants
    const order = [], mark = new Map(), stack = [], cyclic = new Set();
    const visit = (n) => {
      const st = mark.get(n);
      if (st === 2) return;
      if (st === 1) { for (let i = stack.lastIndexOf(n); i < stack.length; i++) cyclic.add(stack[i]); return; }
      mark.set(n, 1); stack.push(n);
      for (const d of deps(n, axis)) visit(d);
      stack.pop(); mark.set(n, 2); order.push(n);
    };
    document.querySelectorAll(".node").forEach(visit);
    for (const n of order) {
      const a = parseAlign(n, axis);
      if (isGroup(n)) {
        layoutKeyline(n, axis);
        // a keyline's box is derived from its members, so a relation on one can never apply
        if (a) alignReport.push({ id: n.id, axis, rel: a.raw, status: "ignored-on-keyline" });
        continue;
      }
      if (!a) continue;
      const rec = { id: n.id, axis, rel: a.raw };
      const t = anchorOf(a);
      if (a.bad) rec.status = "unparseable";
      else if (suspended.has(n.id + "|" + axis)) rec.status = "suspended";
      else if (!t) rec.status = "dangling";
      else if (cyclic.has(n)) rec.status = "cycle";
      else {
        const me = box(n), size = axis === "x" ? me.w : me.h;
        const pos = lineAt(box(t), axis, a.theirs) - size * LINES[axis][a.mine];
        // whole pixels: offset* geometry is integer, and the file stores integers — a centre
        // match between odd and even widths is honest to within half a pixel
        n.style[axis === "x" ? "left" : "top"] = Math.round(pos) + "px";
        rec.status = "held";
      }
      alignReport.push(rec);
    }
  }
  // ---- suggested ties: an arrow that is NEARLY straight almost certainly wants to be straight.
  //      Coincidence is no evidence (every block on a grid row shares a top line); an arrow bent
  //      by a few px is. Per arrow between two plain blocks: find the axis across it (a mostly-
  //      vertical arrow → x, centres), and if the centres are 1..STRAIGHT_PX apart, suggest the
  //      downstream end be centred on the upstream one — or the reverse if downstream is already
  //      tied on that axis. Never suggests what would make a cycle. Accept in ?edit with `a`. ----
  const STRAIGHT_PX = 16;
  function suggestTies() {
    const out = [];
    for (const e of edges) {
      const A = document.getElementById(e.from), B = document.getElementById(e.to);
      if (!A || !B || isGroup(A) || isGroup(B)) continue;
      const a = box(A), b = box(B);
      const dx = (b.x + b.w / 2) - (a.x + a.w / 2), dy = (b.y + b.h / 2) - (a.y + a.h / 2);
      const axis = Math.abs(dy) > Math.abs(dx) ? "x" : "y", off = Math.abs(axis === "x" ? dx : dy);
      if (off === 0 || off > STRAIGHT_PX) continue;
      const line = axis === "x" ? "center" : "middle";
      for (const [dep, anc] of [[B, A], [A, B]]) {
        if (parseAlign(dep, axis) || dependantsOf(dep, axis).has(anc)) continue; // tied, or a cycle
        out.push({ id: dep.id, axis, rel: `${line}:${anc.id}.${line}`, off, arrow: `${e.from}→${e.to}` });
        break;
      }
    }
    return out;
  }

  // ---- state contract: emit computed geometry + invariant results so an agent can read the
  //      diagram's truth WITHOUT pixels — via `chromium --dump-dom` (the #dragram-state blob) or
  //      window.__dragram.state(). Mirrors the cwc "DOM is the machine-readable surface" idea
  //      (anthropics/cwc-workshops · phase-3-verify). Runs in EVERY mode, render included. ----
  const INVARIANTS = [
    { id: "edges-rendered", severity: "fail",
      description: "every declared edge resolves to two real nodes (so a wire is drawn)",
      check: (s) => { const m = s.wires.filter((w) => !w.rendered).map((w) => `${w.from}→${w.to}`);
                      return m.length === 0 || `unrendered: ${m.join(", ")}`; } },
    { id: "keyline-wraps-members", severity: "fail",
      description: "every keyline fully contains its declared members",
      check: (s) => { const bad = [];
        for (const k of s.nodes.filter((n) => n.members)) for (const id of k.members) {
          const m = s.nodes.find((n) => n.id === id); if (!m) continue;
          if (m.x < k.x || m.y < k.y || m.x + m.w > k.x + k.w || m.y + m.h > k.y + k.h) bad.push(`${k.id}⊅${id}`);
        }
        return bad.length === 0 || `not contained: ${bad.join(", ")}`; } },
    { id: "on-grid", severity: "warn",
      description: `every draggable block sits on the ${GRID}px grid on each axis it is not aligned on (Alt-drag may bypass)`,
      check: (s) => {
        const held = new Set(s.alignments.filter((a) => a.status === "held").map((a) => a.id + "|" + a.axis));
        const off = s.nodes.filter((n) => !n.cls.includes("keyline"))
          .filter((n) => (!held.has(n.id + "|x") && n.x % GRID !== 0) || (!held.has(n.id + "|y") && n.y % GRID !== 0))
          .map((n) => `${n.id}@(${n.x},${n.y})`);
        return off.length === 0 || `off-grid: ${off.join(", ")}`; } },
    { id: "alignments-resolve", severity: "warn",
      description: "every stated alignment names a real anchor, parses, and sits on no cycle",
      check: (s) => { const bad = s.alignments.filter((a) => a.status !== "held" && a.status !== "suspended")
          .map((a) => `${a.id}.${a.axis} "${a.rel}" (${a.status})`);
        return bad.length === 0 || bad.join(", "); } },
    { id: "alignments-hold", severity: "fail",
      description: "every held alignment is geometrically true in the computed layout (checks the solver)",
      check: (s) => { const bad = [];
        for (const a of s.alignments.filter((a) => a.status === "held")) {
          const p = a.rel.match(/^(\w+):(.+)\.(\w+)$/);
          const me = s.nodes.find((n) => n.id === a.id), t = s.nodes.find((n) => n.id === p[2]);
          const d = lineAt(t, a.axis, p[3]) - lineAt(me, a.axis, p[1]);
          if (Math.abs(d) > 0.5) bad.push(`${a.id}.${a.axis} off by ${d.toFixed(1)}px`);
        }
        return bad.length === 0 || bad.join(", "); } },
    { id: "arrows-straight", severity: "warn",
      description: `no arrow between two blocks is bent by ${STRAIGHT_PX}px or less (nearly straight = meant straight; see suggestions)`,
      check: (s) => s.suggestions.length === 0 ||
        s.suggestions.map((g) => `${g.arrow} ${g.off}px → ${g.id} ${g.rel}`).join(", ") },
    { id: "content-fits", severity: "warn",
      description: "no block's content spills past its box (clipped by overflow:hidden, or running out of its border), and nothing inside a block is clipped",
      check: (s) => { const px = (o) => Object.entries(o).map(([a, v]) => `${a}+${v}px`).join(" ");
        const bad = s.nodes.filter((n) => n.overflow || n.clipped)
          .map((n) => `${n.id} (${[n.overflow && px(n.overflow), n.clipped && `clipped inside ${px(n.clipped)}`].filter(Boolean).join("; ")})`);
        return bad.length === 0 || `spills: ${bad.join(", ")}`; } },
    { id: "comments-open", severity: "warn",
      description: "no open comments — each is a request to Claude; it's resolved by making the change and deleting the data-comment",
      check: (s) => s.comments.length === 0 || s.comments.map((c) => `${c.id}: ${JSON.stringify(c.text)}`).join(", ") },
    { id: "wires-layer", severity: "warn",
      description: "the file carries its own <svg id=\"wires\"> layer (drag.js mints one if not, so wires still draw)",
      check: () => !mintedWires || "missing from the file — minted at runtime" },
  ];

  function computeState() {
    const nodes = [];
    document.querySelectorAll(".node").forEach((el) => {
      const b = box(el);
      const n = { id: el.id, cls: Array.from(el.classList).filter((c) => c !== "node" && c !== "dragging"),
                  x: b.x, y: b.y, w: b.w, h: b.h };
      if (el.dataset.members) n.members = el.dataset.members.trim().split(/\s+/);
      for (const axis of ["x", "y"]) if (el.dataset[ALIGN_KEY[axis]]) (n.align = n.align || {})[axis] = el.dataset[ALIGN_KEY[axis]];
      // content past the padding box — clipped where overflow is hidden, spilling where it isn't.
      // 1px of slack for subpixel text. Keylines are skipped: their members are siblings, not content.
      if (!isGroup(el)) {
        const ox = el.scrollWidth - el.clientWidth, oy = el.scrollHeight - el.clientHeight;
        if (ox > 1 || oy > 1) n.overflow = Object.assign(ox > 1 ? { x: ox } : {}, oy > 1 ? { y: oy } : {});
        // and content clipped INSIDE the block, by a descendant with overflow:hidden — invisible
        // from the block's own size, and in the render (a fixed-height caption cut short)
        let cx = 0, cy = 0;
        el.querySelectorAll("*").forEach((d) => {
          const cs = getComputedStyle(d);
          if (cs.overflowX === "visible" && cs.overflowY === "visible") return;
          cx = Math.max(cx, (d.scrollWidth - d.clientWidth) || 0); cy = Math.max(cy, (d.scrollHeight - d.clientHeight) || 0);
        });
        if (cx > 1 || cy > 1) n.clipped = Object.assign(cx > 1 ? { x: cx } : {}, cy > 1 ? { y: cy } : {});
      }
      nodes.push(n);
    });
    const wires = edges.map((e) => ({ from: e.from, to: e.to, cls: e.cls,
      rendered: !!(document.getElementById(e.from) && document.getElementById(e.to)) }));
    // point-and-comment (drag-wemitu): each open comment, with the computed box of what it names
    const comments = [...document.querySelectorAll(".node[data-comment]")].map((el) => {
      const b = box(el); return { id: el.id, text: el.dataset.comment, x: b.x, y: b.y, w: b.w, h: b.h };
    });
    const s = { stage: { w: stage.offsetWidth, h: stage.offsetHeight }, nodes, wires, alignments: alignReport,
                suggestions: suggestTies(), comments };
    s.checks = INVARIANTS.map((inv) => {
      let r; try { r = inv.check(s); } catch (err) { r = `threw: ${err}`; }
      return { id: inv.id, description: inv.description,
               status: r === true ? "ok" : inv.severity, detail: r === true ? undefined : r };
    });
    s.verdict = s.checks.some((c) => c.status === "fail") ? "FAIL" : "PASS";
    return s;
  }
  window.__dragram = { version: "1.0", state: computeState };

  function emitState() {
    let host = document.getElementById("dragram-state");
    if (!host) { host = document.createElement("script");
                 host.type = "application/json"; host.id = "dragram-state";
                 document.body.appendChild(host); }
    // "<" escaped: a comment containing </script> would otherwise end this blob early in a DOM dump
    host.textContent = JSON.stringify(computeState()).replace(/</g, "\\u003c");
  }

  let afterLayout = () => {}; // edit mode draws tie marks here; render mode draws nothing
  function relayout() { solveLayout(); renderWires(); emitState(); afterLayout(); }
  // Embedding seam (mcp-app/, 2026-11-22): a host page that changes the DOM itself — moves a
  // block, adds one, pushes an edge onto `edges` (the live list renderWires draws) — then calls
  // window.dragram.relayout() so ties re-solve and wires follow.
  window.dragram = { relayout, edges };

  relayout();
  window.addEventListener("resize", relayout);

  // ---- edit mode ----
  if (!new URLSearchParams(location.search).has("edit")) return;
  document.body.classList.add("edit");

  // Read stage size from the element so each scenario can size its own canvas (e.g. a busier
  // scenario uses a wider 1920×1080 stage). Falls back to 1720 if unset.
  const STAGE_W = stage.offsetWidth || 1720, STAGE_H = stage.offsetHeight || 1080;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const snap = (v) => Math.round(v / GRID) * GRID;
  let scale = 1, tx = 0, ty = 0;

  // set here, not only in grammar.css: six fixtures don't link it, and with the default centre
  // origin fit/zoom-at-cursor misplace the stage
  stage.style.transformOrigin = "0 0";
  function apply() {
    stage.style.transform = `translate(${tx}px,${ty}px) scale(${scale})`;
    afterLayout(); // mark thickness tracks the zoom
    if (cbox) placeBox(); // an open comment box stays beside its element through pan and zoom
    pct.textContent = Math.round(scale * 100) + "%";
  }
  function fit() {
    const m = 80; // margin so the page extent reads as a bordered card when zoomed out
    scale = clamp(Math.min((viewport.clientWidth - m) / STAGE_W,
                           (viewport.clientHeight - m) / STAGE_H), 0.1, 3);
    tx = (viewport.clientWidth - STAGE_W * scale) / 2;
    ty = (viewport.clientHeight - STAGE_H * scale) / 2;
    apply();
  }
  function zoomAt(cx, cy, factor) {
    const ns = clamp(scale * factor, 0.1, 3);
    // keep the stage point under the cursor fixed
    const sx = (cx - tx) / scale, sy = (cy - ty) / scale;
    scale = ns;
    tx = cx - sx * scale; ty = cy - sy * scale;
    apply();
  }

  // HUD
  const hud = document.createElement("div");
  hud.className = "zoomhud";
  hud.innerHTML =
    '<button data-z="out" title="Zoom out (-)">−</button>' +
    '<span class="pct">100%</span>' +
    '<button data-z="in" title="Zoom in (+)">+</button>' +
    '<button data-z="fit" title="Fit (f)">⤢</button>' +
    '<button data-z="comment" title="Comment on an element (c)">✎</button>' +
    '<span class="hint">scroll = zoom · drag empty = pan · drag near an edge = align · edge = resize · c = comment · hover = show ties · t = tie marks · alt = free-drag · g = grid</span>';
  document.body.appendChild(hud);
  const pct = hud.querySelector(".pct");
  const sugg = document.createElement("span");
  sugg.className = "hint"; sugg.style.color = "#7c3aed"; sugg.style.fontWeight = "600";
  hud.appendChild(sugg);
  hud.addEventListener("click", (e) => {
    const z = e.target.dataset.z;
    if (z === "fit") fit();
    else if (z === "comment") setCommentMode(!commentMode);
    else if (z === "in") zoomAt(viewport.clientWidth / 2, viewport.clientHeight / 2, 1.15);
    else if (z === "out") zoomAt(viewport.clientWidth / 2, viewport.clientHeight / 2, 1 / 1.15);
  });

  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.1 : 1 / 1.1);
  }, { passive: false });

  window.addEventListener("keydown", (e) => {
    if (e.target.isContentEditable || /^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
    // shortcuts are bare keys: Cmd/Ctrl+A used to accept every suggested tie (writing the file),
    // Cmd/Ctrl+C to toggle comment mode
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "f" || e.key === "0") fit();
    else if (e.key === "+" || e.key === "=") zoomAt(viewport.clientWidth / 2, viewport.clientHeight / 2, 1.15);
    else if (e.key === "-") zoomAt(viewport.clientWidth / 2, viewport.clientHeight / 2, 1 / 1.15);
    else if (e.key === "g") stage.classList.toggle("nogrid"); // toggle grid overlay
    else if (e.key === "t") { ticksOn = !ticksOn; afterLayout(); } // toggle tie + suggestion marks
    else if (e.key === "a") acceptSuggestions(); // accept every suggested tie
    else if (e.key === "c") setCommentMode(!commentMode);
    else if (e.key === "r") reloadKeepingView();
    else if (e.key === "Escape") { if (cbox) closeComment(); else if (commentMode) setCommentMode(false); }
  });

  // save flash
  const flash = document.createElement("div");
  flash.className = "saveflash";
  document.body.appendChild(flash);
  let flashT;
  function showFlash(msg, ok) {
    flash.textContent = msg;
    flash.style.background = ok ? "#16a34a" : "#dc2626";
    flash.classList.add("show");
    clearTimeout(flashT);
    flashT = setTimeout(() => flash.classList.remove("show"), 1200);
  }
  // One save per element. `align` carries only the axes this gesture changed (relation string,
  // or null to clear), so a hand-written relation on an untouched axis is never re-sent — the
  // server validates what it's given, and must not refuse a move over an axis nobody touched.
  // `size` (a resize) carries width and/or height as the inline style px drag.js set.
  // ---- every write goes through ONE queue: in order (a keyline move's member saves used to race —
  //      drag-timuge), each carrying the file version this page last saw. The server refuses a
  //      save whose base isn't the file on disk (409): the file changed under the page — Claude
  //      resolving a comment, another tab, a hand edit — and saving would silently undo that. ----
  //      A save the page can't confirm — timed out, connection dropped — may or may not have
  //      landed, so it is treated like a change on disk: saves pause until a reload shows the truth.
  //      The editor never sends a save without a base (the server can't check one it isn't given).
  const SAVE_TIMEOUT_MS = 8000;
  let base = null, stale = false, inflight = 0, done = 0, queue = Promise.resolve();
  async function fetchBase() { // the version of the file as served; never overwrites a newer one
    try {
      const v = (await fetch(location.pathname, { method: "HEAD", cache: "no-store" })).headers.get("X-Dragram-Version");
      if (v && base === null) base = v;
    } catch (_) { /* retried by the next save or poll */ }
  }
  const baseReady = fetchBase();
  function post(url, body) {
    inflight++;
    const run = async () => {
      try {
        await baseReady;
        if (base === null) await fetchBase();
        if (base === null) return { ok: false, offline: true };
        if (stale) return { ok: false, stale: true };
        const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), SAVE_TIMEOUT_MS);
        let r, j;
        try {
          r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                                 body: JSON.stringify({ ...body, base }), signal: ctl.signal });
          j = (r.headers.get("Content-Type") || "").includes("json") ? await r.json() : {};
        } catch (_) { markStale("unsure"); return { ok: false, unsure: true }; }
        finally { clearTimeout(timer); }
        if (r.status === 409) { markStale("changed"); return { ok: false, stale: true }; }
        if (r.ok && j.version) base = j.version;
        return { ...j, ok: r.ok, status: r.status };
      } finally { inflight--; done++; }
    };
    return (queue = queue.then(run, run));
  }
  const failWhy = (r, what) => r.stale ? "not saved — the file changed on disk (r = reload)"
    : r.unsure ? `${what} not confirmed — connection? (r = reload)`
    : r.offline ? `${what} failed (offline?)` : `${what} failed (${r.status})`;
  async function persist(node, align, size) {
    const body = { file: location.pathname, id: node.id,
                   left: Math.round(node.offsetLeft), top: Math.round(node.offsetTop), ...size };
    if (align && Object.keys(align).length) body.align = align;
    const r = await post("/save", body);
    showFlash(r.ok ? `saved ${node.id}` : failWhy(r, "save"), r.ok);
  }
  // the page learns the file moved on without it — a poll, and any 409 — and says so
  const banner = document.createElement("div");
  banner.style.cssText = "position:fixed; top:14px; left:50%; transform:translateX(-50%); z-index:101; display:none; " +
    "background:#7c3aed; color:#fff; font:600 13px/1.3 system-ui,sans-serif; padding:8px 14px; border-radius:8px; " +
    "box-shadow:0 4px 16px rgba(15,23,42,.25); cursor:pointer;";
  document.body.appendChild(banner);
  const WHY = { changed: "This file changed on disk", unsure: "A save couldn't be confirmed (connection?)" };
  function markStale(why) {
    stale = true; banner.style.display = "block";
    banner.textContent = `${WHY[why]} — press r (or click here) to reload from disk. Saves are paused until you do.`;
  }
  setInterval(async () => {
    if (stale || inflight) return;
    if (base === null) return fetchBase();
    const d0 = done; // counts completed saves: any in between means this reading may predate one
    try {
      const v = (await fetch(location.pathname, { method: "HEAD", cache: "no-store" })).headers.get("X-Dragram-Version");
      if (v && !inflight && done === d0 && v !== base) markStale("changed");
    } catch (_) { /* server away: the next save will say so */ }
  }, 2500);
  const VIEW_KEY = "dragram-view:" + location.pathname;
  function reloadKeepingView() { // r: reload from disk, keeping zoom, pan and an open draft
    const draft = cbox && cbox._ta.value.trim() ? { id: cbox._el.id, text: cbox._ta.value } : null;
    sessionStorage.setItem(VIEW_KEY, JSON.stringify({ scale, tx, ty, draft }));
    queue.then(() => location.reload()); // queued saves land first (each gives up after 8s)
  }
  // closing or leaving the tab with saves still queued would drop them
  window.addEventListener("beforeunload", (e) => { if (inflight) { e.preventDefault(); e.returnValue = ""; } });
  banner.addEventListener("click", reloadKeepingView);
  const setAlign = (el, axis, rel) => { if (rel) el.dataset[ALIGN_KEY[axis]] = rel; else delete el.dataset[ALIGN_KEY[axis]]; };

  // ---- guides: transient lines on the stage, editor chrome only. "snap" = the line a drag has
  //      caught; "thread" = an existing relation, shown on hover so ties are never invisible. ----
  // violet: in no diagram's palette (reds mean "identified", so the first pink read as content)
  const GUIDE = { snap: "#7c3aed", thread: "rgba(124,58,237,.55)", tick: "#7c3aed" };
  function clearGuides(kind) { stage.querySelectorAll(".dg-guide" + (kind ? "." + kind : "")).forEach((g) => g.remove()); }
  function drawGuide(kind, axis, at, a, b) { // a line at `at` on axis, spanning boxes a and b
    const g = document.createElement("div");
    g.className = "dg-guide " + kind;
    // styled inline: not every fixture links grammar.css, and guides must show in all of them
    g.style.cssText = "position:absolute; z-index:98; pointer-events:none; background:" +
                      GUIDE[kind];
    const lo = axis === "x" ? Math.min(a.y, b.y) : Math.min(a.x, b.x);
    const hi = axis === "x" ? Math.max(a.y + a.h, b.y + b.h) : Math.max(a.x + a.w, b.x + b.w);
    const t = Math.max(1, 1.5 / scale); // hairline at any zoom
    Object.assign(g.style, axis === "x"
      ? { left: (at - t / 2) + "px", top: (lo - 12) + "px", width: t + "px", height: (hi - lo + 24) + "px" }
      : { top: (at - t / 2) + "px", left: (lo - 12) + "px", height: t + "px", width: (hi - lo + 24) + "px" });
    stage.appendChild(g);
  }
  // Registration marks: every held tie shows, always (toggle with t), as short static ticks just
  // outside both boxes at the tied line — outside the border and in the editor's colour, so they
  // read as editor chrome, never as diagram. Hover still draws the full thread.
  let ticksOn = true;
  const TICK = 9, TICK_GAP = 4;
  function drawTicks() {
    clearGuides("tick");
    if (!ticksOn) return;
    const t = Math.max(1.5, 2 / scale);
    for (const r of alignReport) {
      if (r.status !== "held") continue;
      const el = document.getElementById(r.id), a = parseAlign(el, r.axis), anc = anchorOf(a);
      for (const [b, line] of [[box(el), a.mine], [box(anc), a.theirs]]) {
        const at = lineAt(b, r.axis, line);
        const marks = r.axis === "x"
          ? [[at - t / 2, b.y - TICK_GAP - TICK, t, TICK], [at - t / 2, b.y + b.h + TICK_GAP, t, TICK]]
          : [[b.x - TICK_GAP - TICK, at - t / 2, TICK, t], [b.x + b.w + TICK_GAP, at - t / 2, TICK, t]];
        for (const [l, tp, w, h] of marks) {
          const g = document.createElement("div");
          g.className = "dg-guide tick";
          g.style.cssText = `position:absolute; z-index:98; pointer-events:none; background:${GUIDE.tick}; ` +
                            `left:${l}px; top:${tp}px; width:${w}px; height:${h}px; border-radius:1px;`;
          stage.appendChild(g);
        }
      }
    }
  }
  // suggested ties show as HOLLOW marks (outlined ticks) where held ties are solid; `a` accepts all
  function drawSuggestions() {
    clearGuides("ghost");
    if (!ticksOn) return;
    const t = Math.max(1.5, 2 / scale);
    for (const g of suggestTies()) {
      const el = document.getElementById(g.id), a = parseAlign({ dataset: { [ALIGN_KEY[g.axis]]: g.rel } }, g.axis);
      const anc = anchorOf(a);
      for (const [b, line] of [[box(el), a.mine], [box(anc), a.theirs]]) {
        const at = lineAt(b, g.axis, line), w = TICK + 2;
        const marks = g.axis === "x"
          ? [[at - 2.5, b.y - TICK_GAP - w, 5, w], [at - 2.5, b.y + b.h + TICK_GAP, 5, w]]
          : [[b.x - TICK_GAP - w, at - 2.5, w, 5], [b.x + b.w + TICK_GAP, at - 2.5, w, 5]];
        for (const [l, tp, mw, mh] of marks) {
          const m = document.createElement("div");
          m.className = "dg-guide ghost";
          m.style.cssText = `position:absolute; z-index:98; pointer-events:none; box-sizing:border-box; ` +
                            `border:${t / 1.5}px solid ${GUIDE.tick}; background:transparent; border-radius:2px; ` +
                            `left:${l}px; top:${tp}px; width:${mw}px; height:${mh}px;`;
          stage.appendChild(m);
        }
      }
    }
    const n = suggestTies().length;
    sugg.textContent = n ? `${n} suggested tie${n > 1 ? "s" : ""} (hollow marks) · a = accept` : "";
  }
  function acceptSuggestions() {
    const gs = suggestTies();
    if (!gs.length) return;
    snapshot();
    const changed = new Map();
    for (const g of gs) {
      const el = document.getElementById(g.id);
      if (parseAlign(el, g.axis)) continue; // an earlier acceptance in this batch already tied it
      setAlign(el, g.axis, g.rel);
      changed.set(el, { ...changed.get(el), [g.axis]: g.rel });
    }
    relayout();
    for (const [el, align] of changed) persist(el, align);
    persistMovedDependants(new Set(changed.keys()));
  }
  // ---- point-and-comment (drag-wemitu): the defining gesture — point at a thing and tell Claude.
  //      `c` (or the ✎ button) arms comment mode; click any element and write a note. It lands in
  //      the file as data-comment on that element, so the .html stays the one shared artefact:
  //      Claude reads the request beside the element it names (shot.py --comments, or the state
  //      contract, which pairs it with the element's computed box) and resolves it by making the
  //      change and deleting the attribute. Clicking a table cell quotes it, for exactness.
  //      Never drawn in render mode. One note per element: reopening edits it, empty deletes it. ----
  let commentMode = false, cbox = null;
  const modeHint = document.createElement("span");
  modeHint.className = "hint"; modeHint.style.color = "#7c3aed"; modeHint.style.fontWeight = "600";
  hud.appendChild(modeHint);
  const cbtn = hud.querySelector('[data-z="comment"]');
  function setCommentMode(on) {
    commentMode = on;
    document.body.classList.toggle("dg-commenting", on);
    cbtn.style.background = on ? GUIDE.snap : ""; cbtn.style.color = on ? "#fff" : "";
    modeHint.textContent = on ? "comment: click an element · esc = leave" : "";
    if (hoverNode) hoverNode.style.cursor = "";
    hoverNode = null; hoverZone = null; clearGuides("edge");
  }
  function drawComments() {
    stage.querySelectorAll(".dg-comment").forEach((b) => b.remove());
    const d = 22 / scale;
    document.querySelectorAll(".node[data-comment]").forEach((el) => {
      const b = box(el), m = document.createElement("div");
      m.className = "dg-comment"; m.dataset.for = el.id; m.textContent = "✎"; m.title = el.dataset.comment;
      // styled inline, like every other guide: most fixtures don't link grammar.css
      m.style.cssText = `position:absolute; z-index:99; left:${b.x + b.w - d / 2}px; top:${b.y - d / 2}px; ` +
        `width:${d}px; height:${d}px; border-radius:50%; background:${GUIDE.snap}; color:#fff; ` +
        `font:700 ${13 / scale}px/${d}px system-ui,sans-serif; text-align:center; cursor:pointer; ` +
        `box-shadow:0 1px 4px rgba(15,23,42,.3); user-select:none;`;
      m.addEventListener("mousedown", (ev) => { ev.stopPropagation(); ev.preventDefault(); openComment(el, el); });
      stage.appendChild(m);
    });
  }
  const toStage = (cx, cy) => { const r = stage.getBoundingClientRect(); return { x: (cx - r.left) / scale, y: (cy - r.top) / scale }; };
  // a click on a block's hard box-shadow backing (the ".stacked" deck of cards) is a click on the
  // block: it paints there, though its box ends short of it. Soft (blurred) drop shadows don't count.
  function paintedAt(cx, cy) {
    const p = toStage(cx, cy);
    for (const el of document.querySelectorAll(".node")) {
      if (isGroup(el)) continue;
      const sh = getComputedStyle(el).boxShadow;
      if (!sh || sh === "none") continue;
      let right = 0, bottom = 0;
      for (const m of sh.matchAll(/(-?[\d.]+)px (-?[\d.]+)px (-?[\d.]+)px(?: (-?[\d.]+)px)?/g)) {
        if (parseFloat(m[3]) !== 0) continue;
        const spread = parseFloat(m[4] || 0);
        right = Math.max(right, parseFloat(m[1]) + spread); bottom = Math.max(bottom, parseFloat(m[2]) + spread);
      }
      const b = box(el);
      if (p.x >= b.x && p.y >= b.y && p.x <= b.x + b.w + right && p.y <= b.y + b.h + bottom) return el;
    }
    return null;
  }
  function onWire(cx, cy) { // within ~6 screen px of an arrow
    const p = toStage(cx, cy), pt = new DOMPoint(p.x, p.y);
    return [...svg.querySelectorAll("path.wire")].some((w) => {
      // widened, and solid: isPointInStroke honours dashes, so a click in a dash gap missed
      const sw = w.getAttribute("stroke-width"), da = w.getAttribute("stroke-dasharray");
      w.setAttribute("stroke-width", String(12 / scale)); w.removeAttribute("stroke-dasharray");
      const hit = w.isPointInStroke(pt);
      w.setAttribute("stroke-width", sw); if (da) w.setAttribute("stroke-dasharray", da);
      return hit;
    });
  }
  function closeComment() { if (cbox) { cbox.remove(); cbox = null; } }
  function placeBox() { // beside its element: right if there's room, else left; kept on screen
    const r = cbox._el.getBoundingClientRect(), W = 312;
    cbox.style.left = (r.right + W < innerWidth ? r.right + 12 : Math.max(8, r.left - W)) + "px";
    cbox.style.top = Math.max(8, Math.min(r.top, innerHeight - cbox.offsetHeight - 8)) + "px";
  }
  function openComment(el, target) {
    // one box at a time, and a draft is never thrown away by opening another
    if (cbox && cbox._ta.value !== cbox._initial) { showFlash("save (enter) or cancel (esc) the open comment first", false); return; }
    closeComment();
    const existing = el.dataset.comment || "";
    // a click on a table cell quotes it ("this value is wrong"); anywhere else means the element —
    // blocks are full of text, so quoting whatever line was hit would muddy "make this green"
    let quote = "";
    const cell = target && target !== el && target.closest && target.closest("td, th");
    if (!existing && cell && el.contains(cell)) {
      const text = (c) => (c.textContent || "").replace(/\s+/g, " ").trim(), t = text(cell);
      if (t && t.length <= 80) {
        // the same value in two rows (BRND01, BRND01) is ambiguous: name the row by its first cell
        const twin = [...el.querySelectorAll("td, th")].filter((c) => text(c) === t).length > 1;
        const first = cell.closest("tr") && cell.closest("tr").cells[0];
        quote = twin && first && first !== cell ? `re “${t}” (row “${text(first)}”): ` : `re “${t}”: `;
      }
    }
    cbox = document.createElement("div");
    cbox.className = "dg-commentbox";
    cbox.style.cssText = "position:fixed; z-index:100; width:300px; background:#fff; border:2px solid #7c3aed; " +
      "border-radius:10px; padding:10px; box-shadow:0 8px 28px rgba(15,23,42,.25); font:13px/1.4 system-ui,sans-serif; color:#1f2937;";
    const head = document.createElement("div");
    head.style.cssText = "font-weight:700; margin-bottom:6px; color:#7c3aed;";
    head.textContent = `✎ comment on ${el.id}`;
    const ta = document.createElement("textarea");
    ta.value = existing || quote; ta.rows = 3;
    ta.style.cssText = "width:100%; box-sizing:border-box; font:inherit; border:1px solid #cbd5e1; border-radius:6px; padding:6px; resize:vertical;";
    const hint = document.createElement("div");
    hint.style.cssText = "color:#64748b; font-size:11.5px; margin-top:5px;";
    hint.textContent = "enter = save · shift+enter = new line · esc = cancel" + (existing ? " · save empty to delete" : "");
    cbox.append(head, ta, hint);
    document.body.appendChild(cbox);
    cbox._el = el; cbox._ta = ta; cbox._initial = ta.value;
    placeBox();
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); saveComment(el, ta.value); }
      else if (e.key === "Escape") { e.preventDefault(); closeComment(); }
    });
    ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
  }
  async function saveComment(el, text) {
    const r = await post("/comment", { file: location.pathname, id: el.id, text });
    // the page changes only once the file has: on a failure the box stays open, text intact
    if (!r.ok) { showFlash(failWhy(r, "comment"), false); return; }
    const stored = r.text || ""; // exactly what the file now holds (the server trims)
    if (stored) el.dataset.comment = stored; else delete el.dataset.comment;
    showFlash(stored ? `comment on ${el.id}` : `comment removed from ${el.id}`, true);
    closeComment(); setCommentMode(false); relayout();
  }
  afterLayout = () => { drawTicks(); drawSuggestions(); drawComments(); };

  function showThreads(el) { // el's own relations, and every relation that anchors on el
    clearGuides("thread");
    const rels = [];
    document.querySelectorAll(".node").forEach((n) => {
      for (const axis of ["x", "y"]) {
        const a = parseAlign(n, axis), t = anchorOf(a);
        if (t && (n === el || t === el)) rels.push({ n, t, axis, a });
      }
    });
    for (const { n, t, axis, a } of rels) drawGuide("thread", axis, lineAt(box(t), axis, a.theirs), box(n), box(t));
  }

  // ---- snapping: object lines first (within SNAP_PX on screen), the grid otherwise. Returns the
  //      snapped position and the relation it implies (null = grid, i.e. no relation). ----
  const SNAP_PX = 8, INTENT_PX = 3, INTENT_RATIO = 0.25; // screen px
  function snapAxis(axis, pos, size, cands, meBox) {
    const tol = SNAP_PX / scale;
    let best = null;
    for (const c of cands) {
      // like-for-like lines only (left↔left, middle↔middle…). Cross pairs — "my middle on its
      // top" — were five of nine ties in Sameer's first test-drive, none meant (2026-09-27).
      for (const [mine, fm] of Object.entries(LINES[axis])) {
        const theirs = mine;
        const line = lineAt(c.b, axis, theirs), d = line - (pos + size * fm);
        if (Math.abs(d) > tol) continue;
        // ties (common: many blocks share a grid line) break toward the nearest block across
        // the other axis
        const rel = `${mine}:${c.el.id}.${theirs}`;
        const gap = axis === "x" ? Math.max(0, c.b.y - (meBox.y + meBox.h), meBox.y - (c.b.y + c.b.h))
                                 : Math.max(0, c.b.x - (meBox.x + meBox.w), meBox.x - (c.b.x + c.b.w));
        const key = [Math.round(Math.abs(d) * 100), gap];
        if (!best || lexLess(key, best.key)) best = { key, rel, pos: pos + d, line, b: c.b };
      }
    }
    return best ? best : { pos: snap(pos), rel: null };
  }
  const lexLess = (a, b) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i]; return false; };
  // what a block moving on axis may snap to: not itself, not anything that hangs off it on that
  // axis (it moves with it), not a keyline it sits in (it is sized by it) — dependantsOf covers both
  function candidatesFor(n, axis) {
    const exclude = dependantsOf(n, axis); exclude.add(n);
    return [...document.querySelectorAll(".node")]
      .filter((el) => !exclude.has(el) && el.id && el.offsetWidth + el.offsetHeight > 0)
      .map((el) => ({ el, b: box(el) }));
  }

  // ---- resize (drag-fijegu): drag a block's edge, or a corner where both axes are offered.
  //      Width is always the author's; height only where the file already states one — otherwise
  //      the content decides it, and a width change reflows the text. A resize never makes content
  //      fit worse than it already did: the floor is the width the content can wrap to, and the
  //      height it needs at that width, unless the box was already under them (then where it was).
  //      A tie is honoured: the tied line stays put and the dragged edge follows the cursor, so a
  //      centred block grows both ways. Dragging the very edge a tie pins drops that tie (it would
  //      snap straight back) — the precedent is a keyline move. A resize never records a tie: sizes
  //      aren't relations. Keylines size themselves and minihosts are scaled pictures of a block,
  //      so neither offers a handle. Alt = free (no snapping). ----
  const EDGE_PX = 7; // screen px inside a block's border that grab the edge rather than the block
  const CURSOR = { e: "ew-resize", w: "ew-resize", n: "ns-resize", s: "ns-resize",
                   ne: "nesw-resize", sw: "nesw-resize", nw: "nwse-resize", se: "nwse-resize" };
  const HANDLE_MIN_PX = 24; // an axis shorter than this on screen offers no handle: it only moves
  const MIN_SIZE = HANDLE_MIN_PX / 3; // 8px: at the 300% zoom cap still big enough to grab again
  const resizable = (el) => !isGroup(el) && !el.classList.contains("minihost");
  // a height the FILE states: inline, and a length — absent or "auto" means content or CSS decides
  const statesHeight = (el) => !!el.style.height && el.style.height !== "auto";
  function edgeAt(el, cx, cy) { // "e" "w" "n" "s" or a corner "se"…; null = not on an edge
    if (!el || !resizable(el)) return null;
    const r = el.getBoundingClientRect(); // screen px, through the zoom
    // inside the box only: content spilling past the border (a legend's last line) is the block,
    // to move, never its edge (essayeur, 2026-09-28)
    const dl = cx - r.left, dr = r.right - cx, dt = cy - r.top, db = r.bottom - cy;
    if (dl < 0 || dr < 0 || dt < 0 || db < 0) return null;
    // small on screen → no handle on that axis, so a 5px marker always moves; the zone never takes
    // more than a quarter each side, so a central band always moves too
    const zx = r.width < HANDLE_MIN_PX ? 0 : Math.min(EDGE_PX, r.width / 4);
    const zy = r.height < HANDLE_MIN_PX || !statesHeight(el) ? 0 : Math.min(EDGE_PX, r.height / 4);
    const h = dl < zx ? "w" : dr < zx ? "e" : "";
    const v = dt < zy ? "n" : db < zy ? "s" : "";
    return v + h || null;
  }
  // the worst overflow (px) of el or anything inside it at border-box width w — with a stated
  // height measured grown to fit (height:auto), as a resize would leave it
  function spillAt(el, w, chromeX, grows) {
    const ws = el.style.width, hs = el.style.height;
    el.style.width = (w - chromeX) + "px";
    if (grows) el.style.height = "auto";
    let worst = 0;
    for (const e of [el, ...el.querySelectorAll("*")])
      worst = Math.max(worst, (e.scrollWidth - e.clientWidth) || 0, (e.scrollHeight - e.clientHeight) || 0);
    el.style.width = ws; el.style.height = hs;
    return worst;
  }
  // a content-driven measure, read by briefly setting one size (border-box px, as offset* reports)
  function measure(el, prop, value) {
    const was = el.style[prop]; el.style[prop] = value;
    const v = prop === "width" ? el.offsetWidth : el.offsetHeight;
    el.style[prop] = was; return v;
  }
  // what style.width/height leave out under content-box sizing (padding + border); 0 under
  // border-box, which every real fixture uses — but writing offsetWidth into a content-box
  // style.width would grow the box by its padding on every resize
  function boxChrome(el) {
    const cs = getComputedStyle(el), px = (p) => parseFloat(cs[p]) || 0;
    if (cs.boxSizing === "border-box") return { x: 0, y: 0 };
    return { x: px("paddingLeft") + px("paddingRight") + px("borderLeftWidth") + px("borderRightWidth"),
             y: px("paddingTop") + px("paddingBottom") + px("borderTopWidth") + px("borderBottomWidth") };
  }
  // the dragged edge snaps to the same edge of another block (right↔right, top↔top…)
  function snapEdge(axis, at, name, cands, meBox) {
    const tol = SNAP_PX / scale;
    let best = null;
    for (const c of cands) {
      const line = lineAt(c.b, axis, name), d = Math.abs(line - at);
      if (d > tol) continue;
      const gap = axis === "x" ? Math.max(0, c.b.y - (meBox.y + meBox.h), meBox.y - (c.b.y + c.b.h))
                               : Math.max(0, c.b.x - (meBox.x + meBox.w), meBox.x - (c.b.x + c.b.w));
      const key = [Math.round(d * 100), gap];
      if (!best || lexLess(key, best.key)) best = { key, line, b: c.b };
    }
    return best;
  }

  let rz = null; // the resize in progress
  function resizeStart(n, zone, ev) {
    const w0 = n.offsetWidth, h0 = n.offsetHeight;
    rz = { el: n, zone, sx: ev.clientX, sy: ev.clientY, w0, h0, l0: n.offsetLeft, t0: n.offsetTop,
           chrome: boxChrome(n), statedH: statesHeight(n), axes: {}, cands: {}, intent: { x: false, y: false },
           style0: { width: n.style.width, height: n.style.height, left: n.style.left, top: n.style.top } };
    // how far the content already overfills the height: a resize may keep that squeeze, never add
    const autoH0 = measure(n, "height", "auto");
    rz.debtH = Math.max(0, autoH0 - h0);
    // a stated height with NO SLACK (its text fills it, or overfills it) keeps that fit as the width
    // changes, both ways, squeeze and all — which is what a reflow-forced growth leaves, so
    // narrow-then-widen is reversible. One WITH slack keeps its height as a floor: the slack is the
    // author's. (The file has no memory of it, though: once reflow has used the slack up and the
    // gesture ends, the box is slack-free, and a later widening tracks the text down.)
    rz.snug = rz.statedH && autoH0 >= h0;
    // floor: the width the content can wrap to, never under MIN_SIZE — or where it was, if it was
    // already narrower
    let floorW = Math.min(w0, Math.max(MIN_SIZE, measure(n, "width", "min-content")));
    // …and narrower only while nothing in the block overflows more than it did at the start. Text
    // in a height fixed by CSS (timeline bars, a line-height pill, max-height) or in a fixed-height
    // child can't grow, so wrapping it would spill. Binary search: spill grows as width shrinks.
    if (floorW < w0) {
      const spill0 = spillAt(n, w0, rz.chrome.x, rz.statedH);
      const fits = (w) => spillAt(n, w, rz.chrome.x, rz.statedH) <= spill0 + 1;
      if (!fits(floorW)) {
        let lo = floorW, hi = w0; // fits(hi) holds: it's where the gesture started
        while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (fits(mid)) hi = mid; else lo = mid; }
        floorW = hi;
      }
    }
    rz.floorW = floorW;
    for (const axis of ["x", "y"]) {
      const e = axis === "x" ? (zone.includes("e") ? 1 : zone.includes("w") ? 0 : null)
                             : (zone.includes("s") ? 1 : zone.includes("n") ? 0 : null);
      if (e === null) continue;
      const held = alignReport.some((r) => r.id === n.id && r.axis === axis && r.status === "held");
      const tied = held ? LINES[axis][parseAlign(n, axis).mine] : null;
      // f = the line that stays put, as a fraction of the size: the tied line, else the far edge.
      // "pinned" = the tie holds the very edge being dragged: while the hand carries that axis the
      // tie is suspended (and dropped at release), otherwise it keeps holding
      const pinned = tied === e, f = tied === null || pinned ? 1 - e : tied;
      const pos0 = axis === "x" ? rz.l0 : rz.t0, size0 = axis === "x" ? w0 : h0;
      rz.axes[axis] = { e, f, pinned, fixed: pos0 + f * size0, edge0: pos0 + e * size0 };
      rz.cands[axis] = candidatesFor(n, axis);
    }
  }
  function resizeMove(ev) {
    const el = rz.el;
    clearGuides("snap"); clearGuides("size");
    // the intent rule, as for a drag: an axis the hand isn't moving along is held exactly — so a
    // click on an edge changes nothing, and a corner dragged sideways doesn't nudge the height
    const rx = Math.abs(ev.clientX - rz.sx), ry = Math.abs(ev.clientY - rz.sy);
    const moving = { x: rx >= INTENT_PX && rx >= INTENT_RATIO * ry, y: ry >= INTENT_PX && ry >= INTENT_RATIO * rx };
    for (const axis of ["x", "y"]) {
      if (!rz.axes[axis]) moving[axis] = false;
      else if (rz.axes[axis].pinned) {
        if (moving[axis]) suspended.add(el.id + "|" + axis); else suspended.delete(el.id + "|" + axis);
      }
    }
    rz.intent = moving;
    const hits = {};
    const sizeFrom = (axis, floor) => { // the dragged edge follows the pointer, snapped, floored
      const A = rz.axes[axis], me = box(el);
      let at = A.edge0 + (axis === "x" ? ev.clientX - rz.sx : ev.clientY - rz.sy) / scale;
      if (!ev.altKey) {
        const name = axis === "x" ? (A.e ? "right" : "left") : (A.e ? "bottom" : "top");
        const hit = snapEdge(axis, at, name, rz.cands[axis], me);
        if (hit) { at = hit.line; hits[axis] = hit; } else at = snap(at);
      }
      const size = (at - A.fixed) / (A.e - A.f);
      if (size < floor) { delete hits[axis]; return floor; }
      return size;
    };
    const restore = (...props) => props.forEach((p) => { el.style[p] = rz.style0[p]; });
    if (rz.axes.x && moving.x) {
      const w = Math.round(sizeFrom("x", rz.floorW));
      el.style.width = (w - rz.chrome.x) + "px";
      el.style.left = Math.round(rz.axes.x.fixed - rz.axes.x.f * w) + "px";
    } else restore("width", "left");
    if (rz.statedH) {
      // the height the content needs at this width, less whatever squeeze the file already had
      const floorH = Math.max(Math.min(MIN_SIZE, rz.h0), measure(el, "height", "auto") - rz.debtH);
      if (moving.y) {
        const h = Math.round(sizeFrom("y", floorH));
        el.style.height = (h - rz.chrome.y) + "px";
        el.style.top = Math.round(rz.axes.y.fixed - rz.axes.y.f * h) + "px";
      } else if (moving.x) {
        restore("top");
        // a width change alone: a box with no slack tracks its text; one with slack only grows
        const h = Math.round(rz.snug ? floorH : Math.max(rz.h0, floorH));
        if (h !== rz.h0) el.style.height = (h - rz.chrome.y) + "px"; else restore("height");
      } else restore("top", "height"); // no axis carried: nothing changes
    }
    relayout();
    const me = box(el);
    for (const axis of ["x", "y"]) if (hits[axis]) drawGuide("snap", axis, hits[axis].line, me, hits[axis].b);
    const lbl = document.createElement("div"); // size readout, just off the bottom-right corner
    lbl.className = "dg-guide size";
    lbl.textContent = `${me.w} × ${me.h}`;
    lbl.style.cssText = `position:absolute; z-index:99; pointer-events:none; white-space:nowrap; ` +
      `font:600 ${12 / scale}px/1 system-ui,sans-serif; color:#fff; background:${GUIDE.snap}; ` +
      `padding:${3 / scale}px ${5 / scale}px; border-radius:${4 / scale}px; ` +
      `left:${me.x + me.w + 6 / scale}px; top:${me.y + me.h + 6 / scale}px;`;
    stage.appendChild(lbl);
  }
  function resizeEnd() {
    const el = rz.el, align = {};
    clearGuides("snap"); clearGuides("size");
    for (const axis of ["x", "y"]) {
      const A = rz.axes[axis];
      if (!A || !A.pinned) continue;
      suspended.delete(el.id + "|" + axis);
      // dropped only if the hand carried that axis at release and the pinned edge really moved;
      // a click, or a corner dragged along the other axis, keeps it
      const moved = axis === "x" ? el.offsetLeft !== rz.l0 || el.offsetWidth !== rz.w0
                                 : el.offsetTop !== rz.t0 || el.offsetHeight !== rz.h0;
      if (rz.intent[axis] && moved) { setAlign(el, axis, null); align[axis] = null; }
    }
    relayout();
    const size = {};
    if (el.offsetWidth !== rz.w0) size.width = parseFloat(el.style.width);
    if (rz.statedH && el.offsetHeight !== rz.h0) size.height = parseFloat(el.style.height);
    if (Object.keys(size).length || Object.keys(align).length || el.offsetLeft !== rz.l0 || el.offsetTop !== rz.t0) {
      persist(el, align, size);
      persistMovedDependants(new Set([el]));
    }
    rz = null;
  }
  // hovering an edge: the resize cursor, and a violet bar on the edge that will move
  let hoverZone = null;
  function showEdge(el, zone) {
    clearGuides("edge");
    if (!el || !zone) return;
    const b = box(el), t = Math.max(2, 3 / scale);
    for (const side of zone) {
      const g = document.createElement("div");
      g.className = "dg-guide edge";
      const r = side === "e" ? [b.x + b.w - t / 2, b.y, t, b.h] : side === "w" ? [b.x - t / 2, b.y, t, b.h]
              : side === "s" ? [b.x, b.y + b.h - t / 2, b.w, t] : [b.x, b.y - t / 2, b.w, t];
      g.style.cssText = `position:absolute; z-index:98; pointer-events:none; background:${GUIDE.snap}; ` +
                        `left:${r[0]}px; top:${r[1]}px; width:${r[2]}px; height:${r[3]}px;`;
      stage.appendChild(g);
    }
  }

  // ---- regroup (dragram-jitova): dragging a block into or out of a keyline changes its membership.
  //      Judged on the keyline boxes as they were when the gesture STARTED: a keyline wraps its
  //      members, so its live box stretches after a departing member and the block could never
  //      leave. The block's centre must be REGROUP_PX past a dashed line to cross it; in between
  //      nothing changes, so a block sat deliberately ON a boundary ("a block sits where a line
  //      crosses a keyline") is never absorbed by a nudge, and membership
  //      never flickers at an edge. The innermost keyline the centre is well inside becomes its home;
  //      it leaves every other. The LAST member of a keyline never leaves (nothing would be left to
  //      wrap), so the whole regroup is off and the keyline follows it, as before. Previewed live:
  //      data-members changes under the hand, so keylines re-wrap as you drag (speculative rendering,
  //      after Declarative Dragging, UIST 2026). Alt = free: no regroup. ----
  const REGROUP_PX = 24;
  let regroup = null; // { frames: [{ k, m0, box }], warned } for the drag in hand
  const idsOf = (s) => s.trim().split(/\s+/).filter(Boolean);
  function regroupStart(n) {
    regroup = { warned: false, frames: [...document.querySelectorAll(".keyline")]
      .filter((k) => isGroup(k) && k !== n)
      .map((k) => ({ k, m0: k.dataset.members,
                     box: { x: k.offsetLeft, y: k.offsetTop, w: k.offsetWidth, h: k.offsetHeight } })) };
  }
  function regroupMove(n, alt) { // call after moving n, before relayout
    const cx = n.offsetLeft + n.offsetWidth / 2, cy = n.offsetTop + n.offsetHeight / 2;
    const depth = (b) => Math.min(cx - b.x, b.x + b.w - cx, cy - b.y, b.y + b.h - cy); // > 0 inside
    const home = alt ? null : regroup.frames.filter((f) => depth(f.box) > REGROUP_PX)
      .sort((a, b) => a.box.w * a.box.h - b.box.w * b.box.h)[0] || null;
    const plan = regroup.frames.map((f) => {
      const was = idsOf(f.m0), member = was.includes(n.id);
      const want = alt ? member : f === home ? true : member && (home || depth(f.box) < -REGROUP_PX) ? false : member;
      return { f, was, member, want };
    });
    const stuck = plan.find((p) => p.member && !p.want && p.was.length === 1);
    if (stuck && !regroup.warned) {
      regroup.warned = true;
      showFlash(`${n.id} is the only block in ${stuck.f.k.id} — it can't leave`, false);
    }
    for (const { f, was, member, want } of plan) {
      const move = !stuck && want !== member;
      f.k.dataset.members = (move ? (want ? [...was, n.id] : was.filter((id) => id !== n.id)) : was).join(" ");
      f.k.style.outline = move && want ? `2px solid ${GUIDE.snap}` : "";
    }
  }
  function regroupEnd() { // → the keylines whose membership the drop changed
    const changed = regroup.frames.filter((f) => f.k.dataset.members !== f.m0).map((f) => f.k);
    regroup.frames.forEach((f) => { f.k.style.outline = ""; });
    regroup = null;
    return changed;
  }
  async function persistMembers(k) {
    const r = await post("/save", { file: location.pathname, id: k.id, members: k.dataset.members });
    showFlash(r.ok ? `${k.id} now holds ${idsOf(k.dataset.members).length}` : failWhy(r, "regroup"), r.ok);
  }

  // pointer modes: resize (grab a block's edge — see above) · keymove (drag a keyline → move all
  //                its members) · drag (a single node) · pan (empty space). Deltas divided by
  //                scale so motion tracks the cursor.
  let mode = null, node = null, sx0 = 0, sy0 = 0, baseL = 0, baseT = 0, ptx = 0, pty = 0;
  let keyBase = [], keyNode = null, cands = { x: [], y: [] }, snapped = { x: null, y: null }, before = new Map();
  const snapshot = () => { before = new Map(); document.querySelectorAll(".node").forEach((n) => before.set(n, [n.offsetLeft, n.offsetTop])); };
  // after a gesture, every block that moved because it depends on what was dragged gets saved too,
  // so the file's left/top never lies about where a derived block sits
  function persistMovedDependants(except) {
    for (const [n, [l, t]] of before) {
      if (except.has(n) || isGroup(n) || !n.id) continue;
      if (n.offsetLeft !== l || n.offsetTop !== t) persist(n);
    }
  }
  viewport.addEventListener("mousedown", (ev) => {
    const n = ev.target.closest(".node");
    if (commentMode) { // pointing, not dragging: a click opens the note (one open box at a time)
      let at = n;
      if (!at || isGroup(at)) at = paintedAt(ev.clientX, ev.clientY) || at; // a .stacked deck's backing
      if ((!at || isGroup(at)) && onWire(ev.clientX, ev.clientY)) {
        showFlash("arrows can't take comments yet — comment on a block at either end", false);
      } else if (at) openComment(at, ev.target);
      ev.preventDefault(); return;
    }
    clearGuides("thread"); clearGuides("edge");
    snapshot();
    const zone = edgeAt(n, ev.clientX, ev.clientY);
    if (zone) {
      mode = "resize"; resizeStart(n, zone, ev); n.classList.add("dragging");
    } else if (n && isGroup(n)) {
      mode = "keymove"; keyNode = n; sx0 = ev.clientX; sy0 = ev.clientY;
      const group = new Set(membersOf(n));
      keyBase = [...group].map((el) => ({ el, l: el.offsetLeft, t: el.offsetTop }));
      // members tied to anchors OUTSIDE the group would snap straight back; the group move
      // overrides them for the gesture, and drops them on release if that axis actually moved
      for (const el of group) for (const axis of ["x", "y"]) {
        const t = anchorOf(parseAlign(el, axis));
        if (t && !group.has(t)) suspended.add(el.id + "|" + axis);
      }
      n.classList.add("dragging");
    } else if (n) {
      mode = "drag"; node = n; sx0 = ev.clientX; sy0 = ev.clientY;
      baseL = n.offsetLeft; baseT = n.offsetTop; n.classList.add("dragging");
      suspended.add(n.id + "|x"); suspended.add(n.id + "|y");
      for (const axis of ["x", "y"]) cands[axis] = candidatesFor(n, axis);
      regroupStart(n);
    } else {
      mode = "pan"; sx0 = ev.clientX; sy0 = ev.clientY; ptx = tx; pty = ty;
      viewport.classList.add("panning");
    }
    ev.preventDefault();
  });
  window.addEventListener("mousemove", (ev) => {
    if (mode === "drag") {
      let nl = baseL + (ev.clientX - sx0) / scale;
      let nt = baseT + (ev.clientY - sy0) / scale;
      clearGuides("snap");
      snapped = { x: null, y: null };
      // Which axes is the hand actually moving along? One counts once the pointer has gone at least
      // INTENT_PX along it AND at least a quarter as far as along the other — so a long sideways
      // drag with a wobble is sideways only, while a precise 8px nudge still counts. An axis not
      // intended is HELD exactly where it was: no grid snap, no object snap. Otherwise the snap
      // itself nudges it 1–8px onto some distant block's line and records a tie nobody asked for
      // (essayeur, 2026-09-26). Judged on NET motion at every move, so a drag that jogs down
      // before going sideways ends sideways; the drop uses the verdict at release.
      const rx = Math.abs(ev.clientX - sx0), ry = Math.abs(ev.clientY - sy0);
      intent = { x: rx >= INTENT_PX && rx >= INTENT_RATIO * ry,
                 y: ry >= INTENT_PX && ry >= INTENT_RATIO * rx };
      if (!intent.x) nl = baseL;
      if (!intent.y) nt = baseT;
      if (!ev.altKey) { // Alt = free-drag: no grid, no objects, no relation
        const me = { x: nl, y: nt, w: node.offsetWidth, h: node.offsetHeight };
        const sx = intent.x ? snapAxis("x", nl, me.w, cands.x, me) : { pos: nl, rel: null };
        const sy = intent.y ? snapAxis("y", nt, me.h, cands.y, me) : { pos: nt, rel: null };
        nl = sx.pos; nt = sy.pos;
        const at = { x: nl, y: nt, w: me.w, h: me.h };
        if (sx.rel) { snapped.x = sx.rel; drawGuide("snap", "x", sx.line, at, sx.b); }
        if (sy.rel) { snapped.y = sy.rel; drawGuide("snap", "y", sy.line, at, sy.b); }
      }
      node.style.left = nl + "px";
      node.style.top = nt + "px";
      regroupMove(node, ev.altKey);
      relayout();
    } else if (mode === "keymove") {
      let dx = (ev.clientX - sx0) / scale, dy = (ev.clientY - sy0) / scale;
      if (!ev.altKey) { dx = snap(dx); dy = snap(dy); } // snap the delta → members keep alignment
      for (const b of keyBase) { b.el.style.left = (b.l + dx) + "px"; b.el.style.top = (b.t + dy) + "px"; }
      relayout();
    } else if (mode === "resize") {
      resizeMove(ev);
    } else if (mode === "pan") {
      tx = ptx + (ev.clientX - sx0); ty = pty + (ev.clientY - sy0); apply();
    } else {
      const n = ev.target.closest && ev.target.closest(".node");
      const zone = commentMode ? null : edgeAt(n, ev.clientX, ev.clientY);
      if (n !== hoverNode || zone !== hoverZone) {
        if (hoverNode && hoverNode !== n) hoverNode.style.cursor = "";
        if (n) n.style.cursor = commentMode ? "crosshair" : zone ? CURSOR[zone] : "";
        showEdge(n, zone); hoverZone = zone;
      }
      if (n !== hoverNode) { hoverNode = n; if (n) showThreads(n); else clearGuides("thread"); }
    }
  });
  let hoverNode = null, intent = { x: false, y: false };
  window.addEventListener("mouseup", () => {
    if (mode === "drag") {
      node.classList.remove("dragging"); clearGuides("snap");
      // relations change only on an axis the pointer actually carried (out of its start cell);
      // an untouched axis keeps its relation, or its absence. A click keeps everything.
      const align = {};
      // a tie to a keyline the block now belongs to is a cycle (the keyline wraps the block): no tie
      const inGroup = (rel) => { const k = rel && document.getElementById(rel.split(":")[1].split(".")[0]);
                                 return !!k && isGroup(k) && idsOf(k.dataset.members).includes(node.id); };
      for (const axis of ["x", "y"]) if (intent[axis]) {
        const rel = inGroup(snapped[axis]) ? null : snapped[axis];
        setAlign(node, axis, rel); align[axis] = rel;
      }
      intent = { x: false, y: false };
      suspended.delete(node.id + "|x"); suspended.delete(node.id + "|y");
      relayout();
      const regrouped = regroupEnd();
      const moved = node.offsetLeft !== baseL || node.offsetTop !== baseT || Object.keys(align).length;
      if (moved) { persist(node, align); persistMovedDependants(new Set([node])); }
      regrouped.forEach(persistMembers);
    } else if (mode === "keymove") {
      keyNode.classList.remove("dragging");
      const moved = { x: false, y: false };
      for (const b of keyBase) { if (b.el.offsetLeft !== b.l) moved.x = true; if (b.el.offsetTop !== b.t) moved.y = true; }
      const cleared = new Map(); // el -> { axis: null } for ties the group move broke
      for (const b of keyBase) for (const axis of ["x", "y"]) {
        if (!suspended.delete(b.el.id + "|" + axis)) continue;
        if (moved[axis]) { setAlign(b.el, axis, null); cleared.set(b.el, { ...cleared.get(b.el), [axis]: null }); }
      }
      relayout();
      keyBase.forEach((b) => persist(b.el, cleared.get(b.el)));
      persistMovedDependants(new Set(keyBase.map((b) => b.el)));
    }
    else if (mode === "resize") { rz.el.classList.remove("dragging"); resizeEnd(); }
    else if (mode === "pan") { viewport.classList.remove("panning"); }
    mode = null; node = null;
    // mousedown cleared the threads and the edge bar; let the next hover redraw them
    if (hoverNode) hoverNode.style.cursor = "";
    hoverNode = null; hoverZone = null;
  });

  // open zoomed-to-fit (whole page, bordered, centred) — or where you were, after an r reload
  const kept = JSON.parse(sessionStorage.getItem(VIEW_KEY) || "null");
  sessionStorage.removeItem(VIEW_KEY);
  if (kept) { scale = kept.scale; tx = kept.tx; ty = kept.ty; apply(); } else fit();
  if (kept && kept.draft && document.getElementById(kept.draft.id)) { // the note you were writing
    openComment(document.getElementById(kept.draft.id), null);
    cbox._ta.value = kept.draft.text;
  }
})();
