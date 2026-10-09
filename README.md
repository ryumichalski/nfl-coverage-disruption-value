# Coverage Disruption Value (CDV)

### ▶ Live dashboard: https://ryumichalski.github.io/nfl-coverage-disruption-value/

I started from **Expected Completion (xComp)**, basically Expected Goals for NFL passing. It is a
simple model of how likely each pass was to be completed given the coverage, down, distance,
play-action, and whether the quarterback was pressured. The NFL already has a completion-probability
stat, so I built one layer on top of it that is the actual point of this project. **Coverage
Disruption Value (CDV) equals league-average completion minus xComp**, which is the completion
points a coverage plus the pass rush took away compared to an average dropback. The signature
finding is that pressure is worth a lot more behind some coverages than others. Its completion
penalty runs from about 17 points behind Cover-2 up to roughly 27 points behind Cover-6, and a
single league-wide completion-over-expected number averages that away and hides it. I built it for
defensive coaches and analysts, so a coordinator can see which coverage and rush combinations
actually suppress completion, and by how much, instead of judging pressure as one flat number.

![Expected completion by coverage and pressure](docs/screenshot.svg)

Open `index.html` for the interactive Play Predictor, the pressure-amplification chart, the CDV
table, a play lookup, and the validation.

> **Retrospective model, not a pre-snap forecast.** One input, whether the defense generated
> pressure, is only known during or after the play. CDV describes what a coverage and rush took away
> given the full in-play context, for review and analysis. It is not a real-time pre-snap prediction.

## Interactive tool (`index.html`)

1. **Play Predictor.** Set coverage, down, yards-to-go, pressure and play-action, and get the fitted
   expected completion and the Coverage Disruption Value, with the number of real plays behind the
   estimate and a flag when it falls back to the league average. It uses the exact `fit_scorer()`
   rate table, embedded in the page.
2. **Pressure amplification by coverage.** The headline chart, showing how far completion drops under
   pressure within each coverage.
3. **CDV table and coverage grid.** Points removed by situation, and expected completion clean
   versus pressured.
4. **Historical play lookup**, **calibration plot**, **chronological validation**, **ablation**,
   and **hardest completions made**.

## Why it holds up (and what it is not)

- **The engine beats the naive baseline out-of-fold.** Scored by a model fit on the other 4/5 of
  games, xComp improves log-loss from **0.668** (league-rate baseline) to **0.651**, AUC **0.61**.
- **It holds out of time (chronological validation).** Trained on the earlier weeks of 2021 and
  tested on the later weeks (2,622 held-out attempts), log-loss goes **0.670 to 0.656**, Brier
  **0.239 to 0.232**, AUC **0.60**, calibration error **3.3 pp**. It generalises forward, not just
  across random folds.
- **The distinctive features earn their place (ablation).** Out-of-fold AUC rises
  **0.53 (situation only) to 0.56 (+coverage) to 0.61 (+pressure)**. Pressure is the single biggest
  gain, which is exactly what CDV is built on.
- **It is calibrated.** Predicted and observed completion agree to a mean of **3.3 percentage
  points** across deciles, so a predicted 60% really completes about 60% of the time.
- **Honest limits.** CDV is for the play or situation, not a season QB leaderboard, because the
  per-player residual is not stable in one 8-game season. The pressure-by-coverage ordering is
  directionally real but noisy at a single season (split-half stability r is about 0.30), so the
  broad gap is solid while a precise ranking of the middle coverages is not. And it is an
  association, not a claim that a coverage caused the result.

## How it works

`xComp = P(complete | coverage scheme, down, distance bucket, play-action, pressure)`, estimated as
**shrunk grouped completion rates** (empirical-Bayes toward the league mean so rare situations are
not over-fit), evaluated with **5-fold cross-validation by game** so no play is scored by a model
that saw it. Then **CDV equals league-average completion minus xComp** for a situation, which is the
completion points removed versus an average dropback. Pressure is a PFF pass-rush label (any hurry,
hit, or sack charged on the play). The model uses pass attempts only (completions, incompletions,
interceptions), and scrambles are excluded by using pass-result rows.

## Data

NFL Next Gen Stats and PFF scouting, 2021 (Big Data Bowl). Place the competition CSVs in `data/`
one level up (or set `BDB_DATA_DIR`).

```
data/plays.csv
data/pffScoutingData.csv
data/games.csv            # week numbers, for the chronological validation split
```

Tracking files are **not** needed for this project.

## Reproduce

```bash
pip install -r requirements.txt     # pandas + numpy
python build_xcomp.py               # writes xcomp_outputs.json (model, CDV, validation)
python build_site.py                # writes index.html (self-contained; open in any browser)
python make_preview.py              # writes docs/screenshot.svg (README image)
```

`index.html` embeds its data inline, so it opens by double-clicking, with no server or network.

## Files

| file | purpose |
|---|---|
| `build_xcomp.py` | fits xComp, computes CDV and validation (5-fold OOF, chronological, ablation), `fit_scorer()` |
| `build_site.py` | embeds the JSON into a standalone `index.html` (predictor, CDV, amplification, validation) |
| `make_preview.py` | generates `docs/screenshot.svg` |
| `xcomp_outputs.json` | model outputs covering metrics, calibration, grid, chrono, ablation, rate table, CDV, lookup |
| `xcomp_per_play.csv` | one row per pass attempt with its conditions, out-of-fold xComp, COE, CDV |
| `index.html` | generated interactive visualisation |

### Scoring any play from Python

```python
from build_xcomp import fit_scorer
score = fit_scorer()
score("Cover-1", down=3, yardsToGo=8, pressure=1)                 # -> 0.430
score("Cover-3", down=1, yardsToGo=10, pressure=0, with_support=True)  # -> (0.722, 415, False)
```

`with_support=True` returns `(xComp, n_training_plays, used_league_mean_fallback)`, the same
support and fallback info the website's Play Predictor shows. You can also run it from the CLI with
`python build_xcomp.py score "Cover-3" 3 7 1 0`.

## License and attribution

Built for the NFL and AWS Big Data Bowl. Underlying data is owned by NFL Next Gen Stats and Pro
Football Focus, used per competition terms.
