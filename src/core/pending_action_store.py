class PendingActionStore:
    def __init__(self):
        self.pending = None

    def set(self, intent):
        self.pending = intent

    def get(self):
        return self.pending

    def clear(self):
        self.pending = None

STORE = PendingActionStore()
