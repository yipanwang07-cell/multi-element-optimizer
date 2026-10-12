"""Replace generated files without truncating the previous successful save."""
import errno
import os
from pathlib import Path
import tempfile
import time


def atomic_write_bytes(path, data):
    path = Path(path)
    for attempt in range(5):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".save-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            return
        except OSError as error:
            transient = error.errno in (errno.EINVAL, errno.EACCES, errno.EBUSY, errno.EAGAIN) or getattr(error, "winerror", None) in (32, 33)
            if not transient or attempt == 4:
                raise OSError(error.errno, f"Could not save {path}. The previous file was preserved; check folder access or sync status. {error}", str(path)) from error
            time.sleep(.1 * 2 ** attempt)
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


def atomic_write_text(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))
