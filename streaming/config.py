"""Settings for the streaming pipeline. Override with environment variables or .env."""
import os

from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_RAW = "sensors.raw"
TOPIC_DLQ = "sensors.dead_letter"
GROUP_ID = os.getenv("KAFKA_GROUP", "metropt-consumer")

WINDOW = "10min"

# A 10-minute window with fewer readings than this is treated as "machine off" and skipped.
# Use the same value as the API. The backfill script prints "min readings per window: N".
MIN_ROWS_PER_WINDOW = int(os.getenv("MIN_ROWS_PER_WINDOW", "25"))

# History kept in memory for scoring: rolling features need 24 h = 144 windows (+ margin).
HISTORY_WINDOWS = 200
BOOTSTRAP_HOURS = 26                 # raw history reloaded from the database at start-up

FLUSH_EVERY_MSGS = 500               # write to the database after this many readings ...
FLUSH_EVERY_SECONDS = 5.0            # ... or after this many seconds, whichever comes first
