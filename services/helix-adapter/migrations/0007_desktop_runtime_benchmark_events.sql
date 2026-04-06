ALTER TABLE helix.desktop_runtime_events
    DROP CONSTRAINT IF EXISTS desktop_runtime_events_event_kind_check;

ALTER TABLE helix.desktop_runtime_events
    ADD CONSTRAINT desktop_runtime_events_event_kind_check
    CHECK (event_kind IN ('ready', 'fallback', 'disconnect', 'benchmark'));
