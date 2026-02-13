import time

class RateLimiter:
    def __init__(self):
        self.calls = []

    def allow(self):
        now = time.time()
        self.calls = [t for t in self.calls if now - t < 10]

        if len(self.calls) >= 5:
            return False

        self.calls.append(now)
        return True

LIMITER = RateLimiter()
