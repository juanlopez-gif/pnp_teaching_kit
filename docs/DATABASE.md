# Database

The vision logger (module 06) writes snapshots to **PostgreSQL**.

## Connection

Set with `PG*` environment variables (read in [`../config.py`](../config.py)):

| Variable | Meaning | Default |
|----------|---------|---------|
| `PGHOST` | host/IP | `127.0.0.1` |
| `PGPORT` | port | `5432` |
| `PGUSER` | user | `twin_mes_db` |
| `PGPASSWORD` | password | `postgres` |
| `PGDATABASE` | database | `twin_mes_db` |
| `PGSCHEMA` | schema | `shipyard_pnp_ws` |

```bash
export PGHOST=127.0.0.1 PGUSER=twin_mes_db PGPASSWORD=secret PGDATABASE=twin_mes_db
```

> Never hardcode real passwords in the source. The kit reads them from the
> environment on purpose.

## Tables

See [`../06_system_integration/db_schema.sql`](../06_system_integration/db_schema.sql)
for the exact DDL. The logger auto-creates them on startup.

### `vision_slot_snapshot`
One row per "initial stack settled" event. Columns `s1_1 … s3_6` (the 3×6 grid)
each hold the detected piece class in that cell, or `NULL` if empty. `run_id`
and `ts` identify the run and time.

### `vision_conveyor_snapshot`
One row whenever the belts' content changes. Columns `conveyor1 … conveyor4`
and `ibs` each hold a **JSON array** of detected class names, e.g.
`["red_square","blue_circle"]`, or `NULL` when empty.

## How rows map to vision

- ROI **names** in `rois.json` decide which column a detection lands in:
  a detection inside the ROI named `conveyor2` fills the `conveyor2` column;
  one inside `s2_3` fills the `s2_3` slot column.
- Only detections with confidence ≥ `config.CONF_THRESHOLD` count.
- The logger de-duplicates: it writes a conveyor row only when the serialized
  content actually changed, to avoid flooding the table.

## Useful queries

```sql
-- latest belt state
SELECT * FROM shipyard_pnp_ws.vision_conveyor_snapshot ORDER BY ts DESC LIMIT 1;

-- everything for one run
SELECT * FROM shipyard_pnp_ws.vision_slot_snapshot WHERE run_id = '20260910_120000';

-- how often did conveyor3 have something, per run?
SELECT run_id, count(*) FROM shipyard_pnp_ws.vision_conveyor_snapshot
WHERE conveyor3 IS NOT NULL GROUP BY run_id;
```
