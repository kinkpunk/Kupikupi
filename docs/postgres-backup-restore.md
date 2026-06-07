# PostgreSQL Backup And Restore

Status date: 2026-06-07

This procedure is required before closed user testing. It covers manual backups, restore drills,
and minimum retention expectations for Kupikupi staging.

## Scope

Back up the PostgreSQL database that stores:

- users and Telegram identities;
- shopping requests and parsed constraints;
- products, stores, source configs, offers, and price history;
- watchlists, deals, notifications, FX rates, and sync runs.

Redis is treated as cache/queue infrastructure and is not part of the data backup scope.

## Environment

Set these variables in the shell that runs backup commands:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/kupikupi"
export BACKUP_DIR="./backups"
```

Use a PostgreSQL URL supported by `pg_dump`. If the application URL uses SQLAlchemy's
`postgresql+asyncpg://` scheme, convert it to `postgresql://` for CLI tools.

## Manual Backup

Create a compressed custom-format dump:

```bash
mkdir -p "$BACKUP_DIR"
pg_dump "$DATABASE_URL" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --file="$BACKUP_DIR/kupikupi-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Validate that the dump can be inspected:

```bash
pg_restore --list "$BACKUP_DIR/kupikupi-YYYYMMDDTHHMMSSZ.dump" > /tmp/kupikupi-restore-list.txt
```

## Restore Drill

Run restore drills into an empty database, never into active staging/production first.

```bash
export RESTORE_DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/kupikupi_restore"
createdb "$RESTORE_DATABASE_URL"
pg_restore "$BACKUP_DIR/kupikupi-YYYYMMDDTHHMMSSZ.dump" \
  --dbname="$RESTORE_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner
```

After restore, point a temporary backend instance at `RESTORE_DATABASE_URL` and verify:

```bash
curl https://api-restore-check.staging.kupikupi.example/v1/ready
```

Then run a smoke check against restored data:

1. list stores and source configs through admin API;
2. list recent shopping requests for a test user;
3. list watchlists and notifications;
4. verify that price history exists for imported products.

## Retention

Minimum staging retention:

- daily backups for 7 days;
- weekly backups for 4 weeks;
- monthly backups for 3 months before public beta.

For managed PostgreSQL, enable provider-native automated backups and point-in-time recovery when
available. Keep manual `pg_dump` backups as a deploy-time safety net before migrations.

## Migration Safety

Before every staging deploy that runs migrations:

1. create a fresh manual backup;
2. confirm `pg_restore --list` succeeds;
3. deploy backend with `RUN_MIGRATIONS=1` on one instance;
4. check `/v1/ready`;
5. keep the pre-migration dump until the next successful backup cycle.

## Security

- Store backups in encrypted storage.
- Do not commit dumps to git.
- Restrict backup access to deployment operators only.
- Rotate database credentials if a dump is exposed.
- Treat restored databases as sensitive because they contain Telegram user identifiers.

## Recovery Time Expectations

For closed user testing, target:

- Recovery Point Objective: 24 hours.
- Recovery Time Objective: 4 hours.

Tighten both values before public beta.
