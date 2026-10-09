"""
Coverage Disruption Value (CDV) — model + outputs builder.

The engine is Expected Completion (xComp): a calibrated, out-of-fold estimate of the probability
a pass is completed given the play's situation (defensive coverage scheme, down, distance,
play-action, and whether the defense generated pressure). It is a reusable play-level model
(shrunk grouped rates fit with 5-fold cross-validation by game), not a season player ranking.

The extension this project is built around is CDV, a defense-side value metric:
    Coverage Disruption Value (CDV) = league-average completion - xComp
i.e. the expected completion points a coverage + pass-rush situation removes versus an average
dropback. The signature finding is that pressure's value is coverage-specific: pressure suppresses
completion far more behind some coverages than others, which a single league-wide CPOE number hides.

Completion Over Expected (COE) for a single play = actual completion (1/0) - xComp.

Outputs written next to this script:
  xcomp_outputs.json  — everything the visualisation needs:
    * meta (sample sizes, out-of-fold logloss vs baseline, AUC, calibration error)
    * calibration deciles (predicted vs observed)
    * coverage × pressure grid of mean xComp and actual completion
    * hardest completions made (lowest xComp, completed) as highlight examples

Method notes / honesty:
  * No leakage: every play is scored by a model fit on the OTHER 4/5 of games.
  * Shrinkage pulls small context buckets toward the league mean so rare situations
    are not over-fit.
  * Intended unit of analysis is the play / the coverage-situation, NOT a QB leaderboard
    (the per-player residual is not stable in a single 8-game sample).

Usage:
    python build_xcomp.py
"""
from __future__ import annotations
import json
import os
import numpy as np
import pandas as pd

DATA_DIR = os.environ.get("BDB_DATA_DIR", "../data")
OUT = os.path.join(os.path.dirname(__file__), "xcomp_outputs.json")

SHRINK = 30.0          # empirical-Bayes strength toward the league mean
N_FOLDS = 5
SEED = 0

# context features used by the model
KEYS = ["pff_passCoverage", "down", "ytg_bin", "pa", "press"]


def load() -> pd.DataFrame:
    plays = pd.read_csv(os.path.join(DATA_DIR, "plays.csv"))
    pff = pd.read_csv(os.path.join(DATA_DIR, "pffScoutingData.csv"))

    rush = pff[pff.pff_role == "Pass Rush"].copy()
    rush["pr"] = ((rush.pff_hurry.fillna(0) + rush.pff_hit.fillna(0) + rush.pff_sack.fillna(0)) > 0)
    press = rush.groupby(["gameId", "playId"]).pr.max().rename("press")

    d = plays.set_index(["gameId", "playId"]).join(press).reset_index()
    d["press"] = d.press.fillna(False).astype(int)

    # week + gameDate for chronological validation (gameId is yyyymmdd-ordered too)
    try:
        games = pd.read_csv(os.path.join(DATA_DIR, "games.csv"))
        wk = games.set_index("gameId").week.to_dict()
        d["week"] = d.gameId.map(wk)
    except Exception:
        d["week"] = np.nan

    # pass attempts only (completion is defined): complete / incomplete / intercepted
    d = d[d.passResult.isin(["C", "I", "IN"])].copy()
    d["complete"] = (d.passResult == "C").astype(float)

    d = d.dropna(subset=["down", "yardsToGo", "pff_passCoverage", "pff_passCoverageType"])
    d["ytg_bin"] = pd.cut(d.yardsToGo, [-1, 3, 7, 100], labels=["short", "medium", "long"]).astype(str)
    d["pa"] = d.pff_playAction.fillna(0).astype(int).astype(str)
    d["down"] = d.down.astype(int)
    return d.reset_index(drop=True)


def _fit_rate_table(d_train, keys, shrink=SHRINK):
    """Shrunk grouped completion rates + support counts from a training frame."""
    y = d_train.complete.values
    glob = float(y.mean())
    key = d_train[keys].astype(str).agg("|".join, axis=1)
    tmp = pd.DataFrame({"k": key.values, "y": y})
    g = tmp.groupby("k").y.agg(["sum", "size"])
    rate = ((g["sum"] + shrink * glob) / (g["size"] + shrink))
    return rate.to_dict(), g["size"].astype(int).to_dict(), glob


def _predict(d_eval, keys, rate, glob):
    key = d_eval[keys].astype(str).agg("|".join, axis=1)
    return key.map(rate).fillna(glob).values


def brier(y, p):
    return float(np.mean((np.asarray(p) - y) ** 2))


def oof_xcomp(d: pd.DataFrame) -> np.ndarray:
    """Out-of-fold expected completion via shrunk grouped rates, folds by game."""
    y = d.complete.values
    key = d[KEYS].astype(str).agg("|".join, axis=1)
    rng = np.random.RandomState(SEED)
    games = d.gameId.unique()
    fold = {g: rng.randint(0, N_FOLDS) for g in games}
    f = d.gameId.map(fold).values
    out = np.zeros(len(d))
    for cur in range(N_FOLDS):
        tr = f != cur
        te = f == cur
        glob = y[tr].mean()
        tmp = pd.DataFrame({"k": key[tr].values, "y": y[tr]})
        g = tmp.groupby("k").y.agg(["sum", "size"])
        rate = ((g["sum"] + SHRINK * glob) / (g["size"] + SHRINK)).to_dict()
        out[te] = pd.Series(key[te].values).map(rate).fillna(glob).values
    return out


def logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def auc(y, p):
    order = np.argsort(p)
    r = np.empty(len(p)); r[order] = np.arange(len(p))
    pos = y == 1
    npos, nneg = pos.sum(), (~pos).sum()
    if npos == 0 or nneg == 0:
        return float("nan")
    return float((r[pos].sum() - npos * (npos - 1) / 2) / (npos * nneg))


PERPLAY = os.path.join(os.path.dirname(__file__), "xcomp_per_play.csv")


def build() -> dict:
    d = load()
    y = d.complete.values
    d["xcomp"] = oof_xcomp(d)
    d["coe"] = d.complete - d.xcomp

    # per-play export: one row per pass attempt with its conditions, xComp, COE and CDV
    d["cdv"] = float(y.mean()) - d.xcomp   # Coverage Disruption Value (league mean - xComp)
    perplay = d[["gameId", "playId", "pff_passCoverage", "pff_passCoverageType",
                 "down", "yardsToGo", "ytg_bin", "pa", "press",
                 "complete", "xcomp", "coe", "cdv"]].copy()
    perplay = perplay.rename(columns={"pff_passCoverage": "coverage",
                                      "pff_passCoverageType": "coverageType",
                                      "pa": "playAction"})
    perplay["xcomp"] = perplay.xcomp.round(4)
    perplay["coe"] = perplay.coe.round(4)
    perplay["cdv"] = perplay.cdv.round(4)
    perplay.to_csv(PERPLAY, index=False)

    base = np.full(len(d), y.mean())
    meta = dict(
        n_plays=int(len(d)),
        n_games=int(d.gameId.nunique()),
        league_completion=round(float(y.mean()), 4),
        baseline_logloss=round(logloss(y, base), 4),
        xcomp_logloss=round(logloss(y, d.xcomp.values), 4),
        auc=round(auc(y, d.xcomp.values), 4),
        shrink=SHRINK,
        features=KEYS,
    )

    # calibration deciles
    d["dec"] = pd.qcut(d.xcomp, 10, labels=False, duplicates="drop")
    cal = (d.groupby("dec")
             .agg(n=("complete", "size"), pred=("xcomp", "mean"), obs=("complete", "mean"))
             .reset_index())
    meta["calibration_mae"] = round(float((cal.pred - cal.obs).abs().mean()), 4)
    calibration = [dict(pred=round(r.pred, 4), obs=round(r.obs, 4), n=int(r.n))
                   for r in cal.itertuples()]

    # coverage x pressure grid
    grid = (d.groupby(["pff_passCoverage", "press"])
              .agg(n=("xcomp", "size"), xcomp=("xcomp", "mean"), actual=("complete", "mean"))
              .reset_index())
    grid = grid[grid.n >= 25]
    grid_rows = [dict(coverage=r.pff_passCoverage, press=int(r.press), n=int(r.n),
                      xcomp=round(r.xcomp, 4), actual=round(r.actual, 4))
                 for r in grid.itertuples()]

    # coverage summary (collapsed over pressure) ordered by difficulty
    cov = (d.groupby("pff_passCoverage")
             .agg(n=("xcomp", "size"), xcomp=("xcomp", "mean"), actual=("complete", "mean"))
             .reset_index())
    cov = cov[cov.n >= 40].sort_values("xcomp")
    coverage_rows = [dict(coverage=r.pff_passCoverage, n=int(r.n),
                          xcomp=round(r.xcomp, 4), actual=round(r.actual, 4))
                     for r in cov.itertuples()]

    # headline numbers: clean vs pressured expected completion
    byp = d.groupby("press").agg(n=("xcomp", "size"), xcomp=("xcomp", "mean"),
                                 actual=("complete", "mean"))
    meta["clean_xcomp"] = round(float(byp.loc[0, "xcomp"]), 4)
    meta["pressured_xcomp"] = round(float(byp.loc[1, "xcomp"]), 4)
    meta["clean_actual"] = round(float(byp.loc[0, "actual"]), 4)
    meta["pressured_actual"] = round(float(byp.loc[1, "actual"]), 4)

    # hardest completions made (lowest xComp, completed) — play-level use example
    hard = (d[d.complete == 1].nsmallest(12, "xcomp")
            [["gameId", "playId", "pff_passCoverage", "down", "yardsToGo", "press", "xcomp"]])
    hardest = [dict(gameId=int(r.gameId), playId=int(r.playId), coverage=r.pff_passCoverage,
                    down=int(r.down), yardsToGo=int(r.yardsToGo), press=int(r.press),
                    xcomp=round(r.xcomp, 3)) for r in hard.itertuples()]

    # ---- (2) CHRONOLOGICAL validation: train early weeks, test later weeks ----
    chrono = None
    if d.week.notna().any():
        wk = d.week.astype(float)
        cut = wk.quantile(0.6)  # ~first 60% of the season trains, rest tests
        tr = d[wk <= cut]
        te = d[wk > cut]
        if len(te) > 100 and len(tr) > 100:
            rate_c, _, glob_c = _fit_rate_table(tr, KEYS)
            p = _predict(te, KEYS, rate_c, glob_c)
            yte = te.complete.values
            base_p = np.full(len(te), tr.complete.mean())
            # calibration deciles on the held-out later weeks
            cdf = pd.DataFrame({"p": p, "y": yte})
            cdf["dec"] = pd.qcut(cdf.p, 8, labels=False, duplicates="drop")
            ccal = cdf.groupby("dec").agg(n=("y", "size"), pred=("p", "mean"),
                                          obs=("y", "mean")).reset_index()
            chrono = dict(
                train_weeks=f"<= {int(cut)}", test_weeks=f"> {int(cut)}",
                n_train=int(len(tr)), n_test=int(len(te)),
                baseline_logloss=round(logloss(yte, base_p), 4),
                model_logloss=round(logloss(yte, p), 4),
                baseline_brier=round(brier(yte, base_p), 4),
                model_brier=round(brier(yte, p), 4),
                auc=round(auc(yte, p), 4),
                calibration_mae=round(float((ccal.pred - ccal.obs).abs().mean()), 4),
                calibration=[dict(pred=round(r.pred, 4), obs=round(r.obs, 4), n=int(r.n))
                             for r in ccal.itertuples()],
            )

    # ---- (3) ABLATION: situation -> +coverage -> +pressure (out-of-fold by game) ----
    def oof_with_keys(keys):
        yv = d.complete.values
        key = d[keys].astype(str).agg("|".join, axis=1)
        rng = np.random.RandomState(SEED)
        games = d.gameId.unique()
        fold = {g: rng.randint(0, N_FOLDS) for g in games}
        f = d.gameId.map(fold).values
        out = np.zeros(len(d))
        for cur in range(N_FOLDS):
            trm, tem = f != cur, f == cur
            glob = yv[trm].mean()
            tmp = pd.DataFrame({"k": key[trm].values, "y": yv[trm]})
            g = tmp.groupby("k").y.agg(["sum", "size"])
            rr = ((g["sum"] + SHRINK * glob) / (g["size"] + SHRINK)).to_dict()
            out[tem] = pd.Series(key[tem].values).map(rr).fillna(glob).values
        return out

    ablation = []
    for label, keys in [
        ("Situation only (down, distance, play-action)", ["down", "ytg_bin", "pa"]),
        ("+ Coverage scheme", ["down", "ytg_bin", "pa", "pff_passCoverage"]),
        ("+ Pressure (full model)", ["down", "ytg_bin", "pa", "pff_passCoverage", "press"]),
    ]:
        p = oof_with_keys(keys)
        yv = d.complete.values
        ablation.append(dict(model=label, n_features=len(keys),
                             logloss=round(logloss(yv, p), 4),
                             brier=round(brier(yv, p), 4),
                             auc=round(auc(yv, p), 4)))

    # ---- (1) FULL fitted rate table + support counts for the client-side predictor ----
    rate_full, support_full, glob_full = _fit_rate_table(d, KEYS)
    rate_table = {k: dict(xcomp=round(v, 4), n=int(support_full.get(k, 0)))
                  for k, v in rate_full.items()}
    coverages = sorted(d.pff_passCoverage.dropna().unique().tolist())
    predictor = dict(
        rate_table=rate_table,
        league_mean=round(glob_full, 4),
        coverages=coverages,
        ytg_bins=[["short", "1-3"], ["medium", "4-7"], ["long", "8+"]],
        key_order=["coverage", "down", "ytg_bin", "playAction", "press"],
    )

    # ---- (4) per-play OOF lookup (gameId+playId -> actual, xComp, COE, CDV) ----
    league = float(y.mean())
    # Coverage Disruption Value for a play = league mean completion - xComp
    # (expected completion points the defense's coverage+rush removed vs an average dropback)
    d["cdv"] = league - d.xcomp
    lookup = {f"{int(r.gameId)}_{int(r.playId)}":
              dict(coverage=r.pff_passCoverage, down=int(r.down), ytg=int(r.yardsToGo),
                   press=int(r.press), pa=int(r.pa), complete=int(r.complete),
                   xcomp=round(float(r.xcomp), 4), coe=round(float(r.coe), 4),
                   cdv=round(float(r.cdv), 4))
              for r in d.itertuples()}

    # ---- (5) COVERAGE DISRUPTION VALUE: pp of completion removed vs league avg ----
    # per coverage x pressure, using the model's expected completion (stable, shrunk)
    cdv_rows = []
    cg = d.groupby(["pff_passCoverage", "press"]).agg(
        n=("xcomp", "size"), xcomp=("xcomp", "mean"), actual=("complete", "mean")).reset_index()
    cg = cg[cg.n >= 40]
    for r in cg.itertuples():
        cdv_rows.append(dict(coverage=r.pff_passCoverage, press=int(r.press), n=int(r.n),
                             xcomp=round(r.xcomp, 4),
                             cdv_pp=round(100 * (league - r.xcomp), 1)))

    # ---- (6) PRESSURE AMPLIFICATION: how much pressure lowers completion, BY coverage ----
    # the signature insight: pressure is worth more behind some coverages than others.
    amp_rows = []
    for cov, g in d.groupby("pff_passCoverage"):
        c = g[g.press == 0]
        p = g[g.press == 1]
        if len(c) >= 60 and len(p) >= 40:
            amp_rows.append(dict(coverage=cov, n_clean=int(len(c)), n_press=int(len(p)),
                                 clean=round(float(c.complete.mean()), 4),
                                 pressured=round(float(p.complete.mean()), 4),
                                 penalty_pp=round(100 * float(c.complete.mean() - p.complete.mean()), 1)))
    amp_rows.sort(key=lambda x: x["penalty_pp"])
    # split-half stability of the amplification pattern (honesty: it is modest)
    d["_half"] = np.where(d.gameId.rank(method="dense") % 2 == 0, "A", "B")
    def _pen(sub):
        o = {}
        for cov, g in sub.groupby("pff_passCoverage"):
            c, p = g[g.press == 0].complete, g[g.press == 1].complete
            if len(c) >= 25 and len(p) >= 15:
                o[cov] = c.mean() - p.mean()
        return pd.Series(o)
    aa, bb = _pen(d[d._half == "A"]), _pen(d[d._half == "B"])
    jj = pd.concat([aa.rename("A"), bb.rename("B")], axis=1).dropna()
    amp_stability = round(float(jj.A.corr(jj.B)), 3) if len(jj) > 2 else None

    cdv = dict(
        league_completion=round(league, 4),
        by_cov_press=sorted(cdv_rows, key=lambda x: -x["cdv_pp"]),
        amplification=amp_rows,
        amplification_stability=amp_stability,
        penalty_range=[amp_rows[0]["penalty_pp"], amp_rows[-1]["penalty_pp"]] if amp_rows else None,
    )

    return dict(meta=meta, calibration=calibration, grid=grid_rows,
                coverage=coverage_rows, hardest=hardest,
                chrono=chrono, ablation=ablation, predictor=predictor,
                lookup=lookup, cdv=cdv)


# ---------------------------------------------------------------------------
# Reusable scorer: xComp for ANY play from its conditions
# ---------------------------------------------------------------------------
def fit_scorer():
    """Fit the full-data xComp lookup once and return a score_play(...) function.

    Unlike build()'s out-of-fold numbers (used for honest evaluation), this fits on
    ALL data to score new, unseen plays — the normal way you'd deploy an expected model.
    """
    d = load()
    # EXACT same fitted table the website's Play Predictor embeds (via build()->predictor)
    rate, support, glob = _fit_rate_table(d, KEYS)

    def ytg_bin(yards):
        return "short" if yards <= 3 else "medium" if yards <= 7 else "long"

    def score_play(coverage, down, yardsToGo, pressure, play_action=0, with_support=False):
        """Return expected completion probability for one play's conditions.

        coverage    : PFF coverage scheme string, e.g. "Cover-3", "Cover-1", "Cover-2"
        down        : 1-4
        yardsToGo   : yards to the first down (int)
        pressure    : 1 if the defense generated pressure, else 0
        play_action : 1 if play-action, else 0
        with_support: if True, also return (n training plays, used_fallback_to_league_mean)
        """
        k = "|".join([str(coverage), str(int(down)), ytg_bin(yardsToGo),
                      str(int(play_action)), str(int(pressure))])
        if k in rate:
            xc = round(rate[k], 4)
            return (xc, int(support.get(k, 0)), False) if with_support else xc
        return (round(glob, 4), 0, True) if with_support else round(glob, 4)

    score_play.league_mean = round(glob, 4)
    return score_play


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "score":
        # ad-hoc single-play scoring:
        #   python build_xcomp.py score "Cover-1" 3 8 1 0
        _, _, cov, dn, ytg, pr, *rest = sys.argv + ["0"]
        pa = int(rest[0]) if rest else 0
        sp = fit_scorer()
        xc = sp(cov, int(dn), int(ytg), int(pr), pa)
        print(f"xComp({cov}, down {dn}, {ytg} to go, pressure={pr}, PA={pa}) = {xc:.3f} "
              f"(league mean {sp.league_mean})")
        sys.exit(0)

    payload = build()
    with open(OUT, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    m = payload["meta"]
    print(f"wrote {OUT}")
    print(f"wrote {PERPLAY} (per-play xComp + COE)")
    print(f"  {m['n_plays']} pass attempts across {m['n_games']} games")
    print(f"  5-fold OOF: baseline logloss {m['baseline_logloss']} -> xComp {m['xcomp_logloss']} "
          f"(AUC {m['auc']}, calibration MAE {m['calibration_mae']})")

    if payload.get("chrono"):
        c = payload["chrono"]
        print(f"\n  CHRONOLOGICAL (train weeks {c['train_weeks']}, test weeks {c['test_weeks']}; "
              f"n_test={c['n_test']}):")
        print(f"    logloss {c['baseline_logloss']} -> {c['model_logloss']} | "
              f"brier {c['baseline_brier']} -> {c['model_brier']} | "
              f"AUC {c['auc']} | calib MAE {c['calibration_mae']}")

    print("\n  ABLATION (out-of-fold):")
    for a in payload["ablation"]:
        print(f"    {a['model']:46s} logloss={a['logloss']} brier={a['brier']} auc={a['auc']}")

    cv = payload["cdv"]
    print("\n  COVERAGE DISRUPTION VALUE (top situations, pp of completion removed vs league):")
    for r in cv["by_cov_press"][:5]:
        tag = "pressured" if r["press"] else "clean"
        print(f"    {r['coverage']:10s} {tag:9s} CDV={r['cdv_pp']:+.1f} pp (n={r['n']})")
    print(f"  Pressure penalty by coverage ranges {cv['penalty_range'][0]:.0f}–{cv['penalty_range'][1]:.0f} pp "
          f"(split-half stability r={cv['amplification_stability']})")

    # quick demo of the reusable scorer (same table the website uses)
    sp = fit_scorer()
    print("\nscore_play() examples:")
    for args in [("Cover-1", 3, 8, 1, 0), ("Cover-3", 1, 10, 0, 0),
                 ("Cover-2", 2, 5, 0, 1), ("Cover-0", 3, 12, 1, 0)]:
        xc, n, fb = sp(*args, with_support=True)
        tag = " (fallback: league mean)" if fb else f" (n={n})"
        print(f"  {args} -> xComp {xc:.3f}{tag}")
