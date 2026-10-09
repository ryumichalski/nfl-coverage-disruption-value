"""
Build the self-contained Expected Completion (xComp) visualisation.

Embeds xcomp_outputs.json into index.html so the page works by just opening the file
(no server, no CDN, no network). Layout, top to bottom:
  * Hero: the Play Predictor (the main interactive piece)
  * Key insight: coverage x pressure expected-completion grid
  * Try it on real plays: historical play lookup + hardest completions
  * Methodology & validation (calibration, chronological split, ablation) at the bottom

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
<title>Coverage Disruption Value (CDV) — what each coverage + pass rush takes away</title>
<style>
  :root{
    --bg:#0b0e13; --panel:#151b24; --panel2:#0f141c; --ink:#eef3f8; --muted:#93a1b0;
    --line:#273040; --accent:#5aa2ff; --good:#3fb950; --bad:#ff6b63; --warn:#e8a93a;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       background:radial-gradient(1200px 600px at 50% -200px,#17202e 0%,var(--bg) 60%);color:var(--ink)}
  .container{max-width:1040px;margin:0 auto;padding:0 22px}
  a{color:var(--accent)}

  /* hero */
  .hero{text-align:center;padding:52px 22px 20px}
  .eyebrow{color:var(--accent);font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:12px}
  .hero h1{font-size:40px;margin:10px 0 8px;letter-spacing:-.5px}
  .hero p{color:var(--muted);max-width:720px;margin:0 auto;font-size:16px}

  /* predictor card */
  .predictor{background:linear-gradient(180deg,#1a2330,#131a24);border:1px solid var(--line);
             border-radius:18px;padding:26px;margin:26px 0 10px;box-shadow:0 20px 60px rgba(0,0,0,.35)}
  .predictor h2{margin:0 0 2px;font-size:19px}
  .predictor .hint{color:var(--muted);font-size:13px;margin-bottom:20px}
  .pgrid{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;align-items:center}
  @media(max-width:760px){.pgrid{grid-template-columns:1fr}}
  .controls .field{margin-bottom:16px}
  .controls label{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
  select,input[type=number],input.lookup{background:#0b1016;color:var(--ink);border:1px solid var(--line);
      border-radius:9px;padding:10px 12px;font-size:15px;width:100%}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden;width:100%}
  .seg button{flex:1;background:#0b1016;color:var(--muted);border:0;padding:10px 0;cursor:pointer;font-size:14px;transition:.12s}
  .seg button.on{background:var(--accent);color:#07243f;font-weight:800}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}

  /* dial */
  .dial{display:flex;flex-direction:column;align-items:center;justify-content:center;
        background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:22px}
  .ring{position:relative;width:208px;height:208px}
  .ring svg{transform:rotate(-90deg)}
  .ring .center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .ring .pct{font-size:48px;font-weight:800;line-height:1}
  .ring .cap{font-size:12px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-top:4px}
  .support{font-size:13px;color:var(--muted);text-align:center;margin-top:14px;min-height:20px}
  .fallback{color:var(--warn);font-weight:600}

  /* sections */
  section{padding:34px 0}
  .sec-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:14px}
  .sec-head h2{font-size:22px;margin:0}
  .sec-head .k{color:var(--muted);font-size:13px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:20px}
  @media(max-width:760px){.cols{grid-template-columns:1fr}}
  .note{color:var(--muted);font-size:13px;margin:0 0 14px}

  table{border-collapse:collapse;width:100%}
  th,td{padding:8px 10px;text-align:center;font-size:13px}
  th{color:var(--muted);font-weight:600;border-bottom:1px solid var(--line)}
  td.l,th.l{text-align:left}
  .covcell{font-weight:600;text-align:left}
  .pill{display:inline-block;border-radius:6px;padding:5px 0;min-width:62px;font-weight:800;color:#07243f}
  .sub11{font-size:10px;color:var(--muted)}
  .drop{color:var(--bad);font-weight:700}
  svg.cal{display:block;background:var(--panel2);border-radius:10px}
  .legend{color:var(--muted);font-size:12px;margin-top:10px}
  .ex{font-size:13px;border-bottom:1px solid var(--line);padding:8px 0;display:flex;justify-content:space-between;gap:10px;align-items:center}
  .ex .ctx{color:var(--muted)}
  .lk{font-size:14px;margin-top:12px;line-height:1.9}
  .lk .big{font-size:22px;font-weight:800}
  .banner{background:#2a230f;border:1px solid #5f4c16;color:#f0e2b4;border-radius:10px;padding:12px 16px;font-size:13px}
  .banner b{color:#fff}
  .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:4px}
  @media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
  .kpi .big{font-size:22px;font-weight:800}
  .kpi .lab{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-top:3px}
  code{background:#0b1016;padding:1px 6px;border-radius:5px;font-size:12px}
  .foot{color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);margin-top:20px;padding:22px 0 50px}
  .foot b{color:var(--ink)}
  .divider{height:1px;background:var(--line);margin:6px 0 0}
</style>
</head>
<body>
<div class="container">

  <div class="hero">
    <div class="eyebrow">NFL × AWS Big Data Bowl</div>
    <h1>Coverage Disruption Value</h1>
    <p>Expected Completion (think Expected Goals for passing) tells you how likely a throw was to be
    completed. <b>Coverage Disruption Value</b> builds on it to answer a defense's question: how many
    expected completion points did this coverage, plus the pass rush, take away from an average
    dropback? The headline finding is that pressure is worth far more behind some coverages than
    others.</p>
  </div>

  <!-- HERO: PLAY PREDICTOR -->
  <div class="predictor">
    <h2>Play Predictor</h2>
    <div class="hint">Set the situation. The dial is expected completion (xComp); below it is the
    Coverage Disruption Value, the completion points this situation removes versus a league-average
    dropback. Each estimate shows how many real plays it is based on.</div>
    <div class="pgrid">
      <div class="controls">
        <div class="field">
          <label>Coverage</label>
          <select id="pCov"></select>
        </div>
        <div class="two">
          <div class="field"><label>Down</label>
            <select id="pDown"><option>1</option><option>2</option><option>3</option><option>4</option></select></div>
          <div class="field"><label>Yards to go</label>
            <input type="number" id="pYtg" value="8" min="1" max="40"/></div>
        </div>
        <div class="two">
          <div class="field"><label>Pressure</label>
            <div class="seg" id="pPress"><button data-v="0" class="on">Clean</button><button data-v="1">Pressured</button></div></div>
          <div class="field"><label>Play-action</label>
            <div class="seg" id="pPa"><button data-v="0" class="on">No</button><button data-v="1">Yes</button></div></div>
        </div>
      </div>
      <div class="dial">
        <div class="ring">
          <svg width="208" height="208" viewBox="0 0 208 208">
            <circle cx="104" cy="104" r="92" fill="none" stroke="#1e2735" stroke-width="18"/>
            <circle id="pArc" cx="104" cy="104" r="92" fill="none" stroke="#5aa2ff" stroke-width="18"
                    stroke-linecap="round" stroke-dasharray="578" stroke-dashoffset="578"/>
          </svg>
          <div class="center"><div class="pct" id="pNum">—</div><div class="cap">xComp</div></div>
        </div>
        <div id="pCdv" style="margin-top:14px;font-size:15px"></div>
        <div class="support" id="pSup"></div>
      </div>
    </div>
  </div>

  <!-- SIGNATURE INSIGHT: pressure amplification by coverage -->
  <section id="amp-sec">
    <div class="sec-head"><h2>The finding: pressure is worth more behind some coverages</h2>
      <span class="k">completion points lost when the rush gets home, by coverage</span></div>
    <div class="panel">
      <div class="note">This is what a single leaguewide completion-over-expected number hides. The
      bar is how far completion drops when the defense generates pressure, <b>within</b> each
      coverage. Getting pressure home is worth far more behind some calls than others.</div>
      <div id="amp"></div>
      <div class="legend" id="ampNote"></div>
    </div>
  </section>

  <!-- CDV + coverage grid -->
  <section id="insight">
    <div class="sec-head"><h2>Coverage Disruption Value: points taken away</h2>
      <span class="k">league mean − expected completion, clean vs under pressure</span></div>
    <div class="panel">
      <div class="note">CDV is the completion points a situation removes versus an average dropback
      (league completion is <b id="lgc"></b>). Positive means the defense suppressed completion below
      average. The grid shows expected completion itself, clean vs pressured, with the pressure drop
      on the right. Cells shown where n ≥ 25.</div>
      <div id="cdvtab" style="margin-bottom:18px"></div>
      <div id="grid"></div>
      <div class="legend">Colour runs red (low completion, good for the defense) to green (high).</div>
    </div>
  </section>

  <!-- TRY IT ON REAL PLAYS -->
  <section id="plays">
    <div class="sec-head"><h2>Try it on real plays</h2></div>
    <div class="cols">
      <div class="panel">
        <h3 style="margin:0 0 2px">Historical play lookup</h3>
        <div class="note">Enter a <code>gameId</code> and <code>playId</code> for the actual result,
        the out-of-fold xComp, and Completion Over Expected.</div>
        <div class="two" style="grid-template-columns:1fr 1fr auto;align-items:end;gap:12px">
          <div><label class="note" style="margin:0 0 6px;display:block">gameId</label><input class="lookup" id="lkG" placeholder="2021090900"/></div>
          <div><label class="note" style="margin:0 0 6px;display:block">playId</label><input class="lookup" id="lkP" placeholder="137"/></div>
          <button id="lkBtn" style="background:var(--accent);color:#07243f;font-weight:800;border:0;border-radius:9px;padding:11px 16px;cursor:pointer">Look up</button>
        </div>
        <div class="lk" id="lkOut"><span class="support">Try game 2021090900, play 137.</span></div>
      </div>
      <div class="panel">
        <h3 style="margin:0 0 2px">Hardest completions made</h3>
        <div class="note">Completed passes the model rated least likely to be caught. The best
        examples of a throw beating the odds (big positive COE).</div>
        <div id="hard"></div>
      </div>
    </div>
  </section>

  <!-- METHODOLOGY -->
  <section id="methodology">
    <div class="sec-head"><h2>Methodology &amp; validation</h2>
      <span class="k">how the model is built and why you can trust it</span></div>
    <div class="divider"></div>

    <div class="banner" style="margin:18px 0">⚠ <b>Retrospective model, not a pre-snap forecast.</b>
      One input, whether the defense generated pressure, is only known during or after the play.
      xComp describes completion odds given the full in-play context, for review and analysis. It is
      not a real-time pre-snap prediction.</div>

    <div class="kpis" id="kpis"></div>

    <div class="cols" style="margin-top:20px">
      <div class="panel">
        <h3 style="margin:0 0 2px">Calibration</h3>
        <div class="note">Plays grouped into deciles of predicted xComp. Dots on the diagonal mean a
        predicted X% really completes about X% of the time.</div>
        <svg id="cal" class="cal" width="340" height="300"></svg>
        <div class="legend" id="calnote"></div>
      </div>
      <div class="panel">
        <h3 style="margin:0 0 2px">Holds out of time (chronological split)</h3>
        <div class="note" id="chronoNote"></div>
        <table id="chronoTab"></table>
        <h3 style="margin:18px 0 2px">Features earn their place (ablation)</h3>
        <div class="note">Each model scored out-of-fold. Lower log-loss, higher AUC is better.</div>
        <table id="ablTab"></table>
      </div>
    </div>

    <div class="foot">
      <b>How it works.</b> xComp = P(complete | coverage, down, distance band, play-action, pressure),
      estimated as shrunk grouped completion rates (pulled toward the league mean so rare situations
      are not over-fit), scored with 5-fold cross-validation by game so no play is graded by a model
      that saw it. Pressure is a PFF pass-rush label (any hurry, hit, or sack on the play). Pass
      attempts only. <b>Coverage Disruption Value (CDV)</b> = league-average completion − xComp, the
      completion points a situation removes versus an average dropback. <b>Honest limits:</b> xComp is
      for the play or situation, not a season QB ranking (the per-player residual is not stable in a
      single 8-game sample); the pressure-by-coverage ordering is directionally real but noisy at one
      season (split-half r ≈ 0.3); and this is not a causal claim that a coverage caused the result. <b>Data:</b> NFL Next Gen Stats + PFF scouting,
      2021, <b id="np"></b> pass attempts across <b id="ng"></b> games. The Play Predictor and the
      play lookup use the identical fitted table as the Python <code>fit_scorer()</code>.
    </div>
  </section>

</div>

<script>
const P = __PAYLOAD__;
const M = P.meta;
const $ = id => document.getElementById(id);

$("np").textContent = M.n_plays.toLocaleString();
$("ng").textContent = M.n_games;

const rgb=a=>`rgb(${a[0]},${a[1]},${a[2]})`;
function color(rate){
  const stops=[[0.40,[192,57,43]],[0.60,[217,179,16]],[0.75,[33,140,70]]];
  let r=rate;
  if(r<=stops[0][0])return rgb(stops[0][1]);
  if(r>=stops[2][0])return rgb(stops[2][1]);
  for(let i=0;i<stops.length-1;i++){const[x0,c0]=stops[i],[x1,c1]=stops[i+1];
    if(r>=x0&&r<=x1){const t=(r-x0)/(x1-x0);return rgb([0,1,2].map(k=>Math.round(c0[k]+t*(c1[k]-c0[k]))))}}
  return rgb(stops[2][1]);
}

// KPIs
const kpis = [
  ["League completion", (M.league_completion*100).toFixed(1)+"%"],
  ["Log-loss vs baseline", M.baseline_logloss.toFixed(3)+" → "+M.xcomp_logloss.toFixed(3)],
  ["AUC (out-of-fold)", M.auc.toFixed(3)],
  ["Calibration error", (M.calibration_mae*100).toFixed(1)+" pp"],
  ["Clean → pressured", (M.clean_xcomp*100).toFixed(0)+"% → "+(M.pressured_xcomp*100).toFixed(0)+"%"],
];
$("kpis").innerHTML = kpis.map(k=>`<div class="kpi"><div class="big">${k[1]}</div><div class="lab">${k[0]}</div></div>`).join("");

// ---------- PLAY PREDICTOR (mirrors fit_scorer() key logic exactly) ----------
const PRED=P.predictor, RATE=PRED.rate_table, LEAGUE=PRED.league_mean;
const ARC_LEN=578; // 2*pi*92
function ytgBin(y){ return y<=3 ? "short" : (y<=7 ? "medium" : "long"); }
let pState={press:"0", pa:"0"};
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
  const col=color(xc);
  $("pNum").textContent=(xc*100).toFixed(0)+"%";
  $("pNum").style.color=col;
  const arc=$("pArc"); arc.style.stroke=col;
  arc.style.strokeDashoffset = ARC_LEN*(1-xc);
  // Coverage Disruption Value = league mean - xComp (completion points removed)
  const cdv=(LEAGUE-xc)*100;
  const sign=cdv>=0?"+":"";
  const cdvCol = cdv>=0 ? "#3fb950" : "#ff6b63";
  $("pCdv").innerHTML=`Coverage Disruption Value: <b style="color:${cdvCol};font-size:18px">${sign}${cdv.toFixed(1)} pp</b>`;
  if(hit){
    $("pSup").innerHTML=`based on <b>${hit.n.toLocaleString()}</b> real plays in this exact situation`;
  }else{
    $("pSup").innerHTML=`<span class="fallback">no plays for this exact situation — falling back to the league average (${(LEAGUE*100).toFixed(1)}%)</span>`;
  }
}
["pCov","pDown","pYtg"].forEach(id=>$(id).addEventListener("input",predict));
predict();

// ---------- COVERAGE GRID ----------
const byCov={};
P.grid.forEach(r=>{(byCov[r.coverage]=byCov[r.coverage]||{})[r.press]=r});
const covOrder = Object.keys(byCov).sort((a,b)=>{
  const ca=(byCov[a][0]||byCov[a][1]).xcomp, cb=(byCov[b][0]||byCov[b][1]).xcomp; return ca-cb;});
let gh="<table><tr><th class='l'>Coverage</th><th>Clean</th><th>Pressured</th><th>Δ pressure</th></tr>";
covOrder.forEach(cov=>{
  const clean=byCov[cov][0], pres=byCov[cov][1];
  const cC=clean?`<span class="pill" style="background:${color(clean.xcomp)}">${(clean.xcomp*100).toFixed(0)}%</span><br><span class="sub11">n=${clean.n}</span>`:"—";
  const pC=pres?`<span class="pill" style="background:${color(pres.xcomp)}">${(pres.xcomp*100).toFixed(0)}%</span><br><span class="sub11">n=${pres.n}</span>`:"—";
  const drop=(clean&&pres)?`<span class="drop">−${((clean.xcomp-pres.xcomp)*100).toFixed(0)} pp</span>`:"—";
  gh+=`<tr><td class="covcell">${cov}</td><td>${cC}</td><td>${pC}</td><td>${drop}</td></tr>`;
});
gh+="</table>"; $("grid").innerHTML=gh;

// ---------- CDV + AMPLIFICATION ----------
const CDV=P.cdv;
$("lgc").textContent=(CDV.league_completion*100).toFixed(1)+"%";

// pressure amplification bars (sorted smallest -> largest penalty)
(function(){
  const rows=CDV.amplification.slice().sort((a,b)=>a.penalty_pp-b.penalty_pp);
  const max=Math.max(...rows.map(r=>r.penalty_pp));
  let h="";
  rows.forEach(r=>{
    const w=Math.max(3,(r.penalty_pp/max)*320);
    h+=`<div style="display:flex;align-items:center;gap:12px;margin:7px 0">
      <div style="width:92px;text-align:right;font-size:13px;color:var(--ink);font-weight:600">${r.coverage}</div>
      <div style="height:22px;width:${w}px;border-radius:5px;background:linear-gradient(90deg,#5aa2ff,#ff6b63)"></div>
      <div style="font-size:13px;color:var(--muted)">−${r.penalty_pp.toFixed(0)} pp
        <span class="sub11">(clean ${(r.clean*100).toFixed(0)}% → pressured ${(r.pressured*100).toFixed(0)}%, n=${(r.n_clean+r.n_press).toLocaleString()})</span></div>
    </div>`;
  });
  $("amp").innerHTML=h;
  const stab = CDV.amplification_stability;
  $("ampNote").innerHTML=`Pressure's completion penalty ranges about
    <b>${CDV.penalty_range[0].toFixed(0)}–${CDV.penalty_range[1].toFixed(0)} pp</b> across coverages.
    <span style="color:var(--warn)">Honest caveat:</span> with one 8-game season the exact ordering is
    noisy (split-half stability r = ${stab}); the broad gap (pressure matters much more behind some
    coverages) is solid, a precise ranking of the middle is not.`;
})();

// CDV table (coverage x pressure, points removed vs league)
(function(){
  const rows=CDV.by_cov_press.slice().sort((a,b)=>b.cdv_pp-a.cdv_pp).slice(0,10);
  let h="<table><tr><th class='l'>Coverage</th><th>Pressure</th><th>xComp</th><th>CDV (pp removed)</th><th>n</th></tr>";
  rows.forEach(r=>{
    const cdvCol = r.cdv_pp>=0 ? "#3fb950" : "#ff6b63";
    h+=`<tr><td class="l covcell">${r.coverage}</td>
      <td>${r.press?"pressured":"clean"}</td>
      <td><span class="pill" style="background:${color(r.xcomp)}">${(r.xcomp*100).toFixed(0)}%</span></td>
      <td style="font-weight:800;color:${cdvCol}">${r.cdv_pp>=0?"+":""}${r.cdv_pp.toFixed(1)}</td>
      <td class="sub11">${r.n.toLocaleString()}</td></tr>`;
  });
  h+="</table>";
  $("cdvtab").innerHTML=h;
})();

// ---------- CALIBRATION ----------
(function(){
  const W=340,H=300,pad=44;
  const x=v=>pad+(v-0.4)/0.4*(W-pad-14), y=v=>H-pad-(v-0.4)/0.4*(H-pad-14);
  let s=`<line x1="${x(0.4)}" y1="${y(0.4)}" x2="${x(0.8)}" y2="${y(0.8)}" stroke="#2b3647" stroke-dasharray="4 4"/>`;
  [0.4,0.5,0.6,0.7,0.8].forEach(v=>{
    s+=`<text x="${x(v)}" y="${H-pad+16}" fill="#93a1b0" font-size="10" text-anchor="middle">${(v*100)|0}%</text>`;
    s+=`<text x="${pad-8}" y="${y(v)+3}" fill="#93a1b0" font-size="10" text-anchor="end">${(v*100)|0}%</text>`;
  });
  s+=`<text x="${W/2}" y="${H-6}" fill="#93a1b0" font-size="11" text-anchor="middle">predicted xComp</text>`;
  s+=`<text x="13" y="${H/2}" fill="#93a1b0" font-size="11" text-anchor="middle" transform="rotate(-90 13 ${H/2})">observed completion</text>`;
  P.calibration.forEach(d=>{ s+=`<circle cx="${x(d.pred)}" cy="${y(d.obs)}" r="5" fill="#5aa2ff"/>`; });
  $("cal").innerHTML=s;
  $("calnote").textContent=`Mean gap between predicted and observed: ${(M.calibration_mae*100).toFixed(1)} percentage points.`;
})();

// ---------- CHRONO + ABLATION ----------
const C=P.chrono;
if(C){
  $("chronoNote").innerHTML=`Trained on weeks <b>${C.train_weeks}</b> (${C.n_train.toLocaleString()} plays),
    tested on weeks <b>${C.test_weeks}</b> (${C.n_test.toLocaleString()} plays), a true out-of-time split.`;
  $("chronoTab").innerHTML=
    `<tr><th class="l">metric</th><th>baseline</th><th>xComp</th></tr>
     <tr><td class="l">Log-loss</td><td>${C.baseline_logloss.toFixed(3)}</td><td><b>${C.model_logloss.toFixed(3)}</b></td></tr>
     <tr><td class="l">Brier</td><td>${C.baseline_brier.toFixed(3)}</td><td><b>${C.model_brier.toFixed(3)}</b></td></tr>
     <tr><td class="l">AUC</td><td>0.500</td><td><b>${C.auc.toFixed(3)}</b></td></tr>
     <tr><td class="l">Calibration</td><td>—</td><td><b>${(C.calibration_mae*100).toFixed(1)} pp</b></td></tr>`;
}else{ $("chronoNote").textContent="Chronological split unavailable."; }
$("ablTab").innerHTML =
  `<tr><th class="l">model</th><th>log-loss</th><th>Brier</th><th>AUC</th></tr>` +
  P.ablation.map(a=>`<tr><td class="l">${a.model}</td><td>${a.logloss.toFixed(3)}</td>
     <td>${a.brier.toFixed(3)}</td><td><b>${a.auc.toFixed(3)}</b></td></tr>`).join("");

// ---------- HARDEST COMPLETIONS ----------
$("hard").innerHTML = P.hardest.map(h=>{
  const sit=`${h.coverage}, ${h.down}&amp;${h.yardsToGo}${h.press?", pressured":""}`;
  return `<div class="ex"><span>game ${h.gameId} · play ${h.playId}<br><span class="ctx">${sit}</span></span>
          <span class="pill" style="background:${color(h.xcomp)}">${(h.xcomp*100).toFixed(0)}%</span></div>`;
}).join("");

// ---------- PLAY LOOKUP ----------
const LK=P.lookup;
function doLookup(){
  const g=($("lkG").value||"").trim(), p=($("lkP").value||"").trim();
  const rec=LK[g+"_"+p];
  if(!rec){ $("lkOut").innerHTML=`<span class="fallback">No pass attempt found for game ${g}, play ${p}.</span>`; return; }
  const res = rec.complete ? "COMPLETE" : "incomplete / INT";
  const coe = rec.coe>=0 ? "+"+rec.coe.toFixed(2) : rec.coe.toFixed(2);
  const sit=`${rec.coverage}, ${rec.down}&amp;${rec.ytg}${rec.press?", pressured":", clean"}${rec.pa?", play-action":""}`;
  $("lkOut").innerHTML=
    `<div><span class="support" style="text-align:left">${sit}</span></div>
     <div>Actual: <b>${res}</b></div>
     <div>xComp: <span class="big" style="color:${color(rec.xcomp)}">${(rec.xcomp*100).toFixed(0)}%</span></div>
     <div>Completion Over Expected: <b style="color:${rec.coe>=0?'#3fb950':'#ff6b63'}">${coe}</b></div>`;
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
