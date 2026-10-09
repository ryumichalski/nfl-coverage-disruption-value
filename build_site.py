"""
Build the self-contained Expected Completion (xComp) visualisation.

Embeds xcomp_outputs.json into index.html so the page works by just opening the file
(no server, no CDN, no network). Three views:
  1. Coverage x Pressure grid of expected completion (headline: clean vs pressured gap)
  2. Calibration plot (predicted vs observed) — proves the metric is trustworthy
  3. Hardest completions made (lowest xComp, completed) — play-level use example

Usage:
    python build_xcomp.py   # first -> xcomp_outputs.json
    python build_site.py    # then  -> index.html
"""
import json
import os

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "xcomp_outputs.json")) as f:
    payload = json.load(f)
OUT = os.path.join(HERE, "index.html")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Expected Completion — how coverage and pressure change the odds of a completion</title>
<style>
  :root{--bg:#0e1116;--panel:#161b22;--ink:#e6edf3;--muted:#8b949e;--line:#30363d;--accent:#58a6ff}
  *{box-sizing:border-box}
  body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
  header{padding:24px 28px 6px}
  h1{margin:0 0 6px;font-size:23px}
  .sub{color:var(--muted);max-width:960px}
  .kpis{display:flex;gap:14px;flex-wrap:wrap;padding:14px 28px}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:150px}
  .kpi .big{font-size:24px;font-weight:700}
  .kpi .lab{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  .wrap{display:flex;gap:20px;padding:10px 28px 40px;flex-wrap:wrap;align-items:flex-start}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
  h2{font-size:16px;margin:0 0 4px}
  .note{color:var(--muted);font-size:12px;margin-bottom:12px}
  table{border-collapse:collapse}
  th,td{padding:7px 9px;text-align:center;font-size:13px}
  th{color:var(--muted);font-weight:600;border-bottom:1px solid var(--line)}
  .covcell{font-weight:600;text-align:left;color:var(--ink)}
  .pill{display:inline-block;border-radius:5px;padding:5px 2px;min-width:66px;font-weight:700;color:#06240f}
  .drop{font-size:11px;color:#ff7b72;font-weight:700}
  .barwrap{display:flex;align-items:center;gap:8px;margin:4px 0}
  .barlab{width:88px;text-align:right;color:var(--muted);font-size:12px}
  svg{display:block}
  .legend{color:var(--muted);font-size:12px;margin-top:10px}
  .ex{font-size:13px;border-bottom:1px solid var(--line);padding:6px 0;display:flex;justify-content:space-between;gap:10px}
  .ex .ctx{color:var(--muted)}
  code{background:#0d1117;padding:1px 5px;border-radius:4px}
  .foot{color:var(--muted);font-size:12px;margin:0 28px 32px;max-width:960px}
  .foot b{color:var(--ink)}
  .banner{margin:12px 28px 0;max-width:960px;background:#2d2410;border:1px solid #6b5417;
          color:#e8d9a8;border-radius:8px;padding:10px 14px;font-size:13px}
  .banner b{color:#fff}
  .pred-row{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:14px}
  .pred-row label{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}
  select,input[type=number]{background:#0d1117;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:7px}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
  .seg button{background:#0d1117;color:var(--muted);border:0;padding:7px 12px;cursor:pointer;font-size:13px}
  .seg button.on{background:var(--accent);color:#06240f;font-weight:700}
  .result{display:flex;align-items:center;gap:18px;margin-top:6px}
  .result .num{font-size:42px;font-weight:800}
  .support{font-size:12px;color:var(--muted)}
  .fallback{color:#e8a93a;font-weight:600}
  .vtab{width:100%;margin-top:4px}
  .vtab td,.vtab th{text-align:center}
  .vtab td.l{text-align:left;color:var(--ink)}
  input.lookup{width:150px}
  .lk{font-size:13px;margin-top:8px;line-height:1.7}
  .lk .big{font-size:20px;font-weight:700}
</style>
</head>
<body>
<header>
  <h1>Expected Completion (xComp)</h1>
  <div class="sub">How much do defensive coverage and pass-rush pressure change the odds that a
  pass is completed? xComp is a calibrated, cross-validated estimate of completion probability
  from the play situation (coverage scheme, down, distance, play-action, and whether the defense
  generated pressure). <b>Completion Over Expected (COE)</b> on a play is the actual result minus
  xComp — a way to see which completions were harder than they looked. This is a reusable
  play-level model, scored out-of-fold by game, not a QB leaderboard.</div>
  <div class="banner">⚠ <b>Retrospective model, not a pre-snap forecast.</b> One of the inputs —
  whether the defense generated pressure — is only known <i>during or after</i> the play. xComp
  therefore describes the completion odds given the full in-play context, for review and analysis.
  It is not a real-time, pre-snap prediction.</div>
</header>

<div class="kpis" id="kpis"></div>

<div class="wrap">
  <div class="panel" style="min-width:360px">
    <h2>▶ Play Predictor</h2>
    <div class="note">Pick a game situation and get the fitted xComp. Uses the exact full-data
    rate table from <code>fit_scorer()</code>, embedded in this page. Shows how many training
    plays back the estimate, and flags when it falls back to the league mean.</div>
    <div class="pred-row">
      <div><label>Coverage</label><select id="pCov"></select></div>
      <div><label>Down</label><select id="pDown"><option>1</option><option>2</option><option>3</option><option>4</option></select></div>
      <div><label>Yards to go</label><input type="number" id="pYtg" value="8" min="1" max="40" style="width:80px"/></div>
    </div>
    <div class="pred-row">
      <div><label>Pressure (known in-play)</label>
        <div class="seg" id="pPress"><button data-v="0" class="on">Clean</button><button data-v="1">Pressured</button></div></div>
      <div><label>Play-action</label>
        <div class="seg" id="pPa"><button data-v="0" class="on">No</button><button data-v="1">Yes</button></div></div>
    </div>
    <div class="result">
      <div><div class="num" id="pNum">—</div><div class="support" id="pSup"></div></div>
    </div>
  </div>

  <div class="panel" style="min-width:300px">
    <h2>🔎 Historical play lookup</h2>
    <div class="note">Enter a <code>gameId</code> and <code>playId</code> to see the actual result,
    the out-of-fold xComp, and COE for that specific pass.</div>
    <div class="pred-row">
      <div><label>gameId</label><input class="lookup" id="lkG" placeholder="2021090900"/></div>
      <div><label>playId</label><input class="lookup" id="lkP" placeholder="137" style="width:100px"/></div>
      <div style="align-self:flex-end"><button class="seg" id="lkBtn" style="padding:7px 14px;cursor:pointer;background:var(--accent);color:#06240f;font-weight:700;border:0;border-radius:6px">Look up</button></div>
    </div>
    <div class="lk" id="lkOut"><span class="support">Try game 2021090900, play 137.</span></div>
  </div>

  <div class="panel" style="min-width:420px">
    <h2>Does it hold out of time? (chronological validation)</h2>
    <div class="note" id="chronoNote"></div>
    <table class="vtab" id="chronoTab"></table>
    <h2 style="margin-top:16px">Do our features earn their place? (ablation)</h2>
    <div class="note">Each model scored out-of-fold. Lower log-loss / higher AUC is better.
    Coverage and especially pressure are the distinctive inputs.</div>
    <table class="vtab" id="ablTab"></table>
  </div>
</div>

<div class="wrap">
  <div class="panel">
    <h2>Coverage × pressure: expected completion</h2>
    <div class="note">Each cell is mean xComp for that coverage, clean vs under pressure.
    The red number is the drop in expected completion when the defense gets pressure. Only
    cells with n&nbsp;≥&nbsp;25 shown.</div>
    <div id="grid"></div>
    <div class="legend">Colour: red = low expected completion (good for defense) → green = high.</div>
  </div>

  <div class="panel">
    <h2>Is xComp trustworthy? (calibration)</h2>
    <div class="note">Plays binned into deciles of predicted xComp. If the dots sit on the
    diagonal, a predicted X% really completes about X% of the time.</div>
    <svg id="cal" width="340" height="320"></svg>
    <div class="legend" id="calnote"></div>
  </div>

  <div class="panel" style="max-width:380px">
    <h2>Hardest completions made</h2>
    <div class="note">Completed passes with the lowest xComp — the throws the model rated least
    likely to be caught. A play-level use of COE.</div>
    <div id="hard"></div>
  </div>
</div>

<div class="foot">
  Data: NFL Next Gen Stats + PFF scouting, 2021 (Big Data Bowl), <b id="np"></b> pass attempts
  across <b id="ng"></b> games. Model: shrunk grouped completion rates over coverage × down ×
  distance × play-action × pressure, evaluated out-of-fold by game (no leakage). Pressure is a PFF
  pass-rush label (any hurry/hit/sack on the play). <b>Honest limits:</b> xComp is for the play /
  situation, not a season QB ranking (the per-player residual is not stable in a single 8-game
  sample); pressure is contemporaneous with the throw, so xComp describes the odds under those
  conditions rather than claiming the coverage <i>caused</i> the result. Because pressure is an
  in-play input, this is a <b>retrospective play-context model, not a pre-snap forecast</b>.
  Validated two ways: 5-fold out-of-fold by game, and a chronological early-weeks→later-weeks
  split (both shown above). The Play Predictor and the per-play lookup use the identical fitted
  table as the Python <code>fit_scorer()</code>.
</div>

<script>
const P = __PAYLOAD__;
const M = P.meta;
const $ = id => document.getElementById(id);

// KPIs
const kpis = [
  ["League completion", (M.league_completion*100).toFixed(1)+"%"],
  ["xComp vs baseline (logloss)", M.baseline_logloss.toFixed(3)+" → "+M.xcomp_logloss.toFixed(3)],
  ["AUC", M.auc.toFixed(3)],
  ["Calibration error", (M.calibration_mae*100).toFixed(1)+" pp"],
  ["Clean → pressured xComp", (M.clean_xcomp*100).toFixed(0)+"% → "+(M.pressured_xcomp*100).toFixed(0)+"%"],
];
$("kpis").innerHTML = kpis.map(k=>`<div class="kpi"><div class="big">${k[1]}</div><div class="lab">${k[0]}</div></div>`).join("");
$("np").textContent = M.n_plays.toLocaleString();
$("ng").textContent = M.n_games;

const rgb=a=>`rgb(${a[0]},${a[1]},${a[2]})`;
function color(rate){
  // 0.40 red -> 0.60 gold -> 0.75 green
  const stops=[[0.40,[192,57,43]],[0.60,[217,179,16]],[0.75,[27,120,60]]];
  let r=rate;
  if(r<=stops[0][0])return rgb(stops[0][1]);
  if(r>=stops[2][0])return rgb(stops[2][1]);
  for(let i=0;i<stops.length-1;i++){const[x0,c0]=stops[i],[x1,c1]=stops[i+1];
    if(r>=x0&&r<=x1){const t=(r-x0)/(x1-x0);return rgb([0,1,2].map(k=>Math.round(c0[k]+t*(c1[k]-c0[k]))))}}
  return rgb(stops[2][1]);
}

// Grid: coverage rows, clean vs pressured
const byCov={};
P.grid.forEach(r=>{(byCov[r.coverage]=byCov[r.coverage]||{})[r.press]=r});
// order coverages by clean xComp ascending (hardest first)
const covOrder = Object.keys(byCov).sort((a,b)=>{
  const ca=(byCov[a][0]||byCov[a][1]).xcomp, cb=(byCov[b][0]||byCov[b][1]).xcomp; return ca-cb;});
let gh="<table><tr><th>Coverage</th><th>Clean</th><th>Pressured</th><th>Δ pressure</th></tr>";
covOrder.forEach(cov=>{
  const clean=byCov[cov][0], pres=byCov[cov][1];
  const cC=clean?`<span class="pill" style="background:${color(clean.xcomp)}">${(clean.xcomp*100).toFixed(0)}%</span><br><span style="font-size:10px;color:#8b949e">n=${clean.n}</span>`:"—";
  const pC=pres?`<span class="pill" style="background:${color(pres.xcomp)}">${(pres.xcomp*100).toFixed(0)}%</span><br><span style="font-size:10px;color:#8b949e">n=${pres.n}</span>`:"—";
  const drop=(clean&&pres)?`<span class="drop">−${((clean.xcomp-pres.xcomp)*100).toFixed(0)} pp</span>`:"—";
  gh+=`<tr><td class="covcell">${cov}</td><td>${cC}</td><td>${pC}</td><td>${drop}</td></tr>`;
});
gh+="</table>";
$("grid").innerHTML=gh;

// Calibration plot
(function(){
  const W=340,H=320,pad=46;
  const x=v=>pad+v*(W-pad-14), y=v=>H-pad-v*(H-pad-14);
  let s=`<rect x="0" y="0" width="${W}" height="${H}" fill="#0d1117"/>`;
  // diagonal
  s+=`<line x1="${x(0.4)}" y1="${y(0.4)}" x2="${x(0.8)}" y2="${y(0.8)}" stroke="#30363d" stroke-dasharray="4 4"/>`;
  // axes ticks
  [0.4,0.5,0.6,0.7,0.8].forEach(v=>{
    s+=`<text x="${x(v)}" y="${H-pad+16}" fill="#8b949e" font-size="10" text-anchor="middle">${(v*100)|0}%</text>`;
    s+=`<text x="${pad-8}" y="${y(v)+3}" fill="#8b949e" font-size="10" text-anchor="end">${(v*100)|0}%</text>`;
  });
  s+=`<text x="${W/2}" y="${H-8}" fill="#8b949e" font-size="11" text-anchor="middle">predicted xComp</text>`;
  s+=`<text x="14" y="${H/2}" fill="#8b949e" font-size="11" text-anchor="middle" transform="rotate(-90 14 ${H/2})">observed completion</text>`;
  P.calibration.forEach(d=>{ s+=`<circle cx="${x(d.pred)}" cy="${y(d.obs)}" r="5" fill="#58a6ff" opacity="0.9"/>`; });
  $("cal").innerHTML=s;
  $("calnote").textContent=`Mean gap between predicted and observed: ${(M.calibration_mae*100).toFixed(1)} percentage points across deciles.`;
})();

// Hardest completions
$("hard").innerHTML = P.hardest.map(h=>{
  const sit=`${h.coverage}, ${h.down}&amp;${h.yardsToGo}${h.press?", pressured":""}`;
  return `<div class="ex"><span>game ${h.gameId} · play ${h.playId}<br><span class="ctx">${sit}</span></span>
          <span class="pill" style="background:${color(h.xcomp)};align-self:center">${(h.xcomp*100).toFixed(0)}%</span></div>`;
}).join("");

// ---------- (1) PLAY PREDICTOR (mirrors fit_scorer() key logic exactly) ----------
const PRED = P.predictor;
const RATE = PRED.rate_table;           // { "coverage|down|ytg|pa|press": {xcomp, n} }
const LEAGUE = PRED.league_mean;
function ytgBin(y){ return y<=3 ? "short" : (y<=7 ? "medium" : "long"); }   // same thresholds as Python
let pState = {press:"0", pa:"0"};
// populate coverages
PRED.coverages.forEach(c=>{const o=document.createElement("option");o.value=c;o.textContent=c;$("pCov").appendChild(o);});
$("pCov").value = PRED.coverages.includes("Cover-3") ? "Cover-3" : PRED.coverages[0];

function segBind(id,field){
  const box=$(id);
  box.querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{
    box.querySelectorAll("button").forEach(x=>x.classList.remove("on"));
    b.classList.add("on"); pState[field]=b.dataset.v; predict();
  }));
}
segBind("pPress","press"); segBind("pPa","pa");

function predict(){
  const cov=$("pCov").value, dn=$("pDown").value;
  const ytg=Math.max(1,parseInt($("pYtg").value||"8",10));
  const key=[cov, dn, ytgBin(ytg), pState.pa, pState.press].join("|");
  const hit=RATE[key];
  const xc = hit ? hit.xcomp : LEAGUE;
  $("pNum").textContent=(xc*100).toFixed(0)+"%";
  $("pNum").style.color=color(xc);
  if(hit){
    $("pSup").innerHTML=`backed by <b>${hit.n.toLocaleString()}</b> training plays in this exact context`;
  }else{
    $("pSup").innerHTML=`<span class="fallback">no training plays for this exact context — using league mean (${(LEAGUE*100).toFixed(1)}%)</span>`;
  }
}
["pCov","pDown","pYtg"].forEach(id=>$(id).addEventListener("input",predict));
predict();

// ---------- (2)+(3) CHRONOLOGICAL VALIDATION + ABLATION tables ----------
const C=P.chrono;
if(C){
  $("chronoNote").innerHTML=`Trained on weeks <b>${C.train_weeks}</b> (${C.n_train.toLocaleString()} plays),
    tested on weeks <b>${C.test_weeks}</b> (${C.n_test.toLocaleString()} plays) — a true out-of-time split.`;
  $("chronoTab").innerHTML=
    `<tr><th>metric</th><th>league-rate baseline</th><th>xComp model</th></tr>
     <tr><td class="l">Log-loss</td><td>${C.baseline_logloss.toFixed(3)}</td><td><b>${C.model_logloss.toFixed(3)}</b></td></tr>
     <tr><td class="l">Brier score</td><td>${C.baseline_brier.toFixed(3)}</td><td><b>${C.model_brier.toFixed(3)}</b></td></tr>
     <tr><td class="l">AUC</td><td>0.500</td><td><b>${C.auc.toFixed(3)}</b></td></tr>
     <tr><td class="l">Calibration error</td><td>—</td><td><b>${(C.calibration_mae*100).toFixed(1)} pp</b></td></tr>`;
}else{
  $("chronoNote").textContent="Chronological split unavailable (no week data).";
}
$("ablTab").innerHTML =
  `<tr><th>model</th><th>log-loss</th><th>Brier</th><th>AUC</th></tr>` +
  P.ablation.map(a=>`<tr><td class="l">${a.model}</td><td>${a.logloss.toFixed(3)}</td>
     <td>${a.brier.toFixed(3)}</td><td><b>${a.auc.toFixed(3)}</b></td></tr>`).join("");

// ---------- (4) HISTORICAL PLAY LOOKUP ----------
const LK=P.lookup;
function doLookup(){
  const g=($("lkG").value||"").trim(), p=($("lkP").value||"").trim();
  const rec=LK[g+"_"+p];
  if(!rec){ $("lkOut").innerHTML=`<span class="fallback">No pass attempt found for game ${g}, play ${p}. (Only pass attempts with coverage labels are modelled.)</span>`; return; }
  const res = rec.complete ? "COMPLETE" : "incomplete / INT";
  const coe = rec.coe>=0 ? "+"+rec.coe.toFixed(2) : rec.coe.toFixed(2);
  const sit=`${rec.coverage}, ${rec.down}&amp;${rec.ytg}${rec.press?", pressured":", clean"}${rec.pa?", play-action":""}`;
  $("lkOut").innerHTML=
    `<div><span class="support">${sit}</span></div>
     <div>Actual: <b>${res}</b></div>
     <div>Out-of-fold xComp: <span class="big" style="color:${color(rec.xcomp)}">${(rec.xcomp*100).toFixed(0)}%</span></div>
     <div>Completion Over Expected: <b style="color:${rec.coe>=0?'#3fb950':'#ff7b72'}">${coe}</b></div>`;
}
$("lkBtn").addEventListener("click",doLookup);
$("lkP").addEventListener("keydown",e=>{if(e.key==="Enter")doLookup();});
</script>
</body>
</html>
"""

html = HTML.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
with open(OUT, "w") as f:
    f.write(html)
print(f"wrote {OUT} ({len(html)//1024} KB)")
