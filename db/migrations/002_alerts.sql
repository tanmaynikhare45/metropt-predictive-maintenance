-- Phase 6: delivery tracking and duplicate protection for alerts.
-- Safe to run more than once. init.sql already contains this for NEW databases.
--
--   docker exec -i metropt-db psql -U postgres -d metropt < db/migrations/002_alerts.sql
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS delivered BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS alerts_kind_time_uq ON alerts (kind, time);
