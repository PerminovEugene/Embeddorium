# Release process

The repository currently declares version `0.1.0` in `pyproject.toml`. It has no
Git tags, release automation, changelog generation, build/publish workflow, or
documented compatibility policy.

Before any release, the checks in [Testing](testing.md) can validate the current
tree, and [changelog.md](../changelog.md) can record verified user-facing
changes. PostgreSQL major-version changes require explicit operator migration;
the current image is PostgreSQL 17 and cannot start on a volume initialized by
PostgreSQL 16 without `pg_dump`/restore or `pg_upgrade`.

The authoritative steps for choosing a version, tagging, building artifacts,
publishing images/packages, signing, and supporting upgrades are not defined:
{MISSED_INFO}
