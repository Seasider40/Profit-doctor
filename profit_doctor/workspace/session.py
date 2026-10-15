"""Request-bound local operator sessions; opaque secrets never persisted."""
from dataclasses import dataclass, field
import secrets
import time
from threading import RLock


def matches(value, expected):
    return isinstance(value, str) and isinstance(expected, str) and secrets.compare_digest(value.encode(), expected.encode())


class SessionRefused(PermissionError):
    """The request's authenticated session is no longer live."""


@dataclass(frozen=True, eq=False)
class SessionBinding:
    token: str = field(repr=False)
    csrf: str = field(repr=False)


class OperatorSession:
    IDLE = 3600
    ABSOLUTE = 28800

    def __init__(self, *, clock=None):
        self.clock = clock or time.monotonic
        self.lock = RLock()
        self._active = None
        self.started = self.last_activity = 0

    def _require(self, binding):
        current = self.clock()
        if (binding is None or binding is not self._active or
                current - self.started >= self.ABSOLUTE or current - self.last_activity >= self.IDLE):
            raise SessionRefused('Operator session required')
        return current

    def login(self):
        with self.lock:
            self._active = SessionBinding(secrets.token_urlsafe(32), secrets.token_urlsafe(32))
            self.started = self.last_activity = self.clock()
            return self._active

    def authenticate(self, token, *, csrf=None, touch=False):
        with self.lock:
            binding = self._active
            if binding is None or not matches(token, binding.token):
                raise SessionRefused('Operator session required')
            current = self._require(binding)
            if csrf is not None and not matches(csrf, binding.csrf):
                raise PermissionError('Request token required')
            if touch:
                self.last_activity = current
            return binding

    def metadata(self, binding, *, renew=False):
        with self.lock:
            current = self._require(binding)
            if renew:
                self.last_activity = current
            return {'csrf': binding.csrf, 'idle_seconds': max(0, int(self.IDLE - (current - self.last_activity))),
                'absolute_seconds': max(0, int(self.ABSOLUTE - (current - self.started)))}

    def end(self, binding):
        with self.lock:
            self._require(binding)
            self._active = None
