"""A credential the client cannot use is an auth kind, not INTERNAL (mise-nodavu).

The sync client raises token_store.CredentialsUnavailable — a FileNotFoundError
subclass carrying the remedy — for every designed credential failure. Unconverted,
with_retry made it UNKNOWN and run_operation's catch-all INTERNAL, so a caller
could not tell a missing token from a bug. Only that subclass converts: a plain
FileNotFoundError from the same call (httpx's client constructor reading an
SSL_CERT_FILE that isn't there) is not an auth problem and keeps its own kind.

Split from adapters/calendar.py, which sits at the 500-line cap; any adapter may
use it.
"""

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from models import ErrorKind, MiseError
from token_store import CredentialsUnavailable

_P = ParamSpec("_P")
_T = TypeVar("_T")


def credentials_as_auth(func: Callable[_P, _T]) -> Callable[_P, _T]:
    """CredentialsUnavailable becomes MiseError(AUTH_EXPIRED), marked
    details.credentials_unavailable so callers can skip scope advice.
    Goes UNDER with_retry, which passes a MiseError through unretried."""
    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        try:
            return func(*args, **kwargs)
        except CredentialsUnavailable as e:
            raise MiseError(ErrorKind.AUTH_EXPIRED, str(e),
                            details={"credentials_unavailable": True}) from e
    return wrapper
