"""Score the historical data with the saved models and store the results in `predictions`.

Run from the project root (after load_sensors.py):
    python scripts/backfill_predictions.py            # needs torch for the LSTM
    python scripts/backfill_predictions.py --no-lstm  # skip the LSTM (no torch needed)

IMPORTANT: the saved models were trained on parts of this same data, so these scores are
IN-SAMPLE. They are fine for a dashboard demo. Never quote them as model performance:
the honest numbers come from the leave-one-failure-out results in the notebooks.
"""
import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import psycopg
from dotenv import load_dotenv

from ml.features import ANALOG, WINDOW, build_rolling_features, build_window_features
from ml.inference import load_models, predict_anomaly, predict_failure_risk

load_dotenv(ROOT / ".env")


def to_long(model_name, score, flag):
    out = pd.DataFrame({"time": score.index, "model": model_name,
                        "score": score.values, "flag": flag.reindex(score.index).values})
    return out.dropna(subset=["score"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=str(ROOT / "data/processed/metropt3.parquet"))
    ap.add_argument("--no-lstm", action="store_true")
    ap.add_argument("--truncate", action="store_true", help="empty the predictions table first")
    args = ap.parse_args()

    models = load_models(load_lstm=not args.no_lstm)
    if models.anomaly_cfg is None:
        sys.exit("No saved models found in ml/models/. Run notebook 02 first.")

    raw = pd.read_parquet(args.parquet).sort_index()
    raw = raw[~raw.index.duplicated(keep="first")]

    # one global threshold for "machine off" windows, so every chunk is treated the same
    counts = raw[ANALOG[0]].resample(WINDOW).count()
    min_rows = 0.5 * counts[counts > 0].median()
    print(f"Raw rows: {len(raw):,} | min readings per window: {min_rows:.0f}")

    with psycopg.connect(os.environ["DATABASE_URL"], options="-c timezone=UTC") as conn:
        cur = conn.cursor()
        if args.truncate:
            cur.execute("TRUNCATE predictions")

        # monthly chunks with 1 day of overlap: the rolling features need 24 h of history
        for period in pd.period_range(raw.index.min(), raw.index.max(), freq="M"):
            start, end = period.start_time, period.end_time
            chunk = raw.loc[start - pd.Timedelta("1D"): end]
            if len(chunk) == 0:
                continue
            feat = build_window_features(chunk, min_rows=min_rows)
            if len(feat) == 0:
                continue

            parts = []
            an = predict_anomaly(models, feat)
            parts.append(to_long("iforest", an["if_score"], an["if_flag"]))
            if an["lstm_score"].notna().any():
                parts.append(to_long("lstm_ae", an["lstm_score"], an["lstm_flag"]))

            if models.failure is not None:
                rf = predict_failure_risk(models, build_rolling_features(feat))
                parts.append(to_long("failure_risk", rf["risk"], rf["flag"]))

            long_df = pd.concat(parts, ignore_index=True)
            long_df = long_df[(long_df["time"] >= start) & (long_df["time"] <= end)]   # drop the overlap day

            buf = io.StringIO()
            long_df.to_csv(buf, header=False, index=False, na_rep="")
            cur.execute("CREATE TEMP TABLE IF NOT EXISTS _pred_stage (LIKE predictions INCLUDING DEFAULTS) ON COMMIT DROP")
            with cur.copy("COPY _pred_stage (time, model, score, flag) FROM STDIN WITH (FORMAT csv)") as cp:
                cp.write(buf.getvalue())
            cur.execute("INSERT INTO predictions SELECT * FROM _pred_stage ON CONFLICT DO NOTHING")
            conn.commit()
            print(f"  {period}: {len(long_df):,} prediction rows")

        for model, n in cur.execute("SELECT model, count(*) FROM predictions GROUP BY model ORDER BY model").fetchall():
            print(f"predictions[{model}] = {n:,}")


if __name__ == "__main__":
    main()
