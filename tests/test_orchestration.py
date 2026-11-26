import unittest
from threading import Event, Thread
from human3d.orchestration import Coordinator


class CoordinatorTests(unittest.TestCase):
    def test_lifecycle(self):
        c = Coordinator("project")
        c.invalidate({"photo": "a"})
        first = c.submit("body")
        c.start(first.id)
        c.progress(first.id, 1, 2)
        self.assertTrue(c.finish(first.id, "valid", lambda _: True))
        second = c.submit("body")
        c.start(second.id)
        c.cancel(second.id)
        self.assertTrue(c.cancellation_requested(second.id))
        self.assertFalse(c.finish(second.id, "bad", lambda _: True))
        third = c.retry(second.id)
        c.start(third.id)
        self.assertFalse(c.finish(third.id, "bad", lambda _: False))
        self.assertEqual(c.snapshot()[1]["body"][1], "valid")

    def test_invalidation_during_validation(self):
        c = Coordinator("project")
        job = c.submit("body")
        c.start(job.id)
        entered, release = Event(), Event()
        results = []
        def validate(_):
            entered.set()
            return release.wait(5)
        worker = Thread(target=lambda: results.append(c.finish(job.id, "old", validate)))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            c.invalidate({"photo": "new"})
        finally:
            release.set()
            worker.join(5)
        self.assertEqual(results, [False])
        self.assertEqual(c.snapshot()[1], {})

    def test_superseded(self):
        c = Coordinator("project")
        old = c.submit("body")
        c.start(old.id)
        new = c.submit("body")
        c.start(new.id)
        self.assertTrue(c.finish(new.id, "new", lambda _: True))
        self.assertFalse(c.finish(old.id, "old", lambda _: True))
        self.assertEqual(c.snapshot()[1]["body"][1], "new")
