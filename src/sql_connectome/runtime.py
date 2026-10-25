from __future__ import annotations

import atexit
import base64
import os
import stat
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class RuntimeConfigurationError(RuntimeError):
    pass


_owned_ca_files: dict[Path, tuple[int, int, int]] = {}


def _cleanup_owned_ca_files() -> None:
    """Remove only still-identical temporary CA files from this process."""
    for path, (pid, device, inode) in list(_owned_ca_files.items()):
        if pid != os.getpid():
            continue
        try:
            current = path.lstat()
            if (
                stat.S_ISREG(current.st_mode)
                and (current.st_dev, current.st_ino) == (device, inode)
            ):
                path.unlink()
        except FileNotFoundError:
            pass
        finally:
            _owned_ca_files.pop(path, None)


atexit.register(_cleanup_owned_ca_files)


def _write_private_ca(ca_bytes: bytes, ca_path: Path | None) -> Path:
    if ca_path is None:
        descriptor, name = tempfile.mkstemp(prefix="sql-connectome-ca-", suffix=".pem")
        path = Path(name)
        generated = True
    else:
        path = ca_path
        # An explicit path must have an existing trusted parent directory.
        # Never follow a pre-positioned target symlink or truncate an existing
        # file. O_EXCL also closes the check/open race for the final component.
        if any(parent.is_symlink() for parent in path.parents):
            raise RuntimeConfigurationError("PROJECT_CA_PATH_UNSAFE")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except OSError as exc:
            raise RuntimeConfigurationError("PROJECT_CA_PATH_UNSAFE") from exc
        generated = False

    created = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "wb") as target:
            if hasattr(os, "fchmod"):
                os.fchmod(target.fileno(), 0o600)
            target.write(ca_bytes)
            target.flush()
            os.fsync(target.fileno())
    except Exception:
        # We exclusively created the file; clean up a partial CA only if the
        # original inode still occupies the path.
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                path.unlink()
        except FileNotFoundError:
            pass
        raise

    if generated:
        _owned_ca_files[path] = (os.getpid(), created.st_dev, created.st_ino)
    return path


def configure_database_environment(
    *,
    ca_path: Path | None = None,
) -> str:
    """Normalize managed-PostgreSQL environment variables.

    SQL Connectome remains provider-neutral. When a host injects a base64 project CA,
    this helper upgrades the injected PostgreSQL URI to certificate-verifying TLS.
    """

    database_url = os.getenv("SQL_CONNECTOME_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeConfigurationError("DATABASE_URL_MISSING")

    encoded_ca = os.getenv("PROJECT_CA_CERT")
    if not encoded_ca:
        os.environ["SQL_CONNECTOME_DATABASE_URL"] = database_url
        return database_url

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeConfigurationError("DATABASE_URL_MUST_BE_POSTGRES_URI")

    try:
        ca_bytes = base64.b64decode(encoded_ca, validate=True)
    except Exception as exc:
        raise RuntimeConfigurationError("PROJECT_CA_CERT_INVALID_BASE64") from exc

    if not ca_bytes:
        raise RuntimeConfigurationError("PROJECT_CA_CERT_EMPTY")

    private_ca_path = _write_private_ca(ca_bytes, ca_path)

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"sslmode", "sslrootcert"}
    ]
    query.extend(
        [
            ("sslmode", "verify-full"),
            ("sslrootcert", str(private_ca_path)),
        ]
    )
    secure_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )
    os.environ["SQL_CONNECTOME_DATABASE_URL"] = secure_url
    return secure_url
