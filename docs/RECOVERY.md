# SQL Connectome Recovery V1

## Purpose

SQL Connectome recovery is provider-independent. A database backup must remain restorable when the
managed PostgreSQL provider changes.

V1 uses PostgreSQL's native logical archive path instead of a provider snapshot API:

```text
live PostgreSQL
  -> exported REPEATABLE READ snapshot
  -> pg_dump custom archive
  -> checksum-bound manifest
  -> blank PostgreSQL database
  -> pg_restore single transaction
  -> structural + migration readback
  -> restore qualification receipt
```

Provider snapshots may be retained as additional recovery evidence, but they are never the only
recovery path.

## Backup contract

`scripts/backup_database.py` creates a PostgreSQL custom-format archive and a neighboring
`<archive>.manifest.json`.

The backup transaction exports a PostgreSQL snapshot before collecting source metadata. `pg_dump`
is bound to that same snapshot, so the catalog/migration evidence and archive are taken from one
consistent database view.

The manifest records:

- schema `SQL_CONNECTOME_BACKUP_MANIFEST_V1`;
- creation timestamp;
- archive SHA-256 and byte length;
- exact source runtime identity;
- PostgreSQL server version;
- pg_dump version/major;
- exported snapshot identifier;
- user-catalog digest and object counts;
- SQL Connectome migration digest/count;
- bounded pg_dump stderr;
- explicit ownership/privilege portability flags;
- canonical manifest digest.

Passwords are removed from the connection string passed in the process argument list and supplied
through `PGPASSWORD` to the PostgreSQL client process.

## Portability boundary

V1 uses a whole-database custom archive and intentionally restores with `--no-owner` and
`--no-privileges`. Object ownership and ACLs are therefore not portable backup state in this
profile; the restore operator becomes the owner of restored objects and access policy must be
reconstructed by source-controlled platform/provider policy.

`pg_dump` backs up one database. Cluster-global objects such as roles and tablespaces are outside
this archive and must be reconstructed separately from source or another explicitly governed
global-object backup.

V1 fails closed when the pg_dump major version is older than the source server major version.

## Restore contract

`scripts/restore_database.py` restores only into an already-created blank target database. It never
creates, drops, cleans, truncates, or overwrites a target database.

The operator must pass `--trusted-source`. PostgreSQL warns that restoring a dump can execute code
chosen by the source database's superusers. The SQL Connectome manifest proves archive integrity,
not source authenticity. A matching SHA-256 does not make an untrusted dump safe.

Before restore, V1 verifies:

1. manifest schema and canonical manifest digest;
2. archive byte length and SHA-256;
3. explicit trusted-source acknowledgement;
4. blank target state;
5. pg_restore major is not older than the backup tool major;
6. target PostgreSQL major is not older than the source PostgreSQL major.

Restore runs with:

- `--single-transaction`;
- `--exit-on-error`;
- `--no-owner`;
- `--no-privileges`.

After restore, SQL Connectome recomputes the user-catalog digest and migration digest/count. A PASS
receipt is emitted only when those cross-bind to the backup manifest.

## What V1 qualification proves

The CI qualification uses PostgreSQL 17 client tools against PostgreSQL 17, inserts fixture data,
creates a backup, restores it into a separate blank database, verifies the catalog/migration
cross-bindings, verifies the fixture rows, and then proves that a second restore is refused because
the target is no longer blank.

That is behavioral qualification of the recovery path against the exact CI subject. It is not a
claim that every extension or every future PostgreSQL/provider combination has been qualified.

## Operator usage

Create a backup:

```bash
export SQL_CONNECTOME_DATABASE_URL='postgresql://...'
python scripts/backup_database.py --output ./backups/database.dump
```

Restore into a separately created blank database:

```bash
export SQL_CONNECTOME_RESTORE_DATABASE_URL='postgresql://.../blank_target'
python scripts/restore_database.py \
  --archive ./backups/database.dump \
  --trusted-source
```

A durable environment should use PostgreSQL client binaries at least as new as the source server and
store the archive + manifest in independently durable storage.
