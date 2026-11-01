"""Tk integration checks; skipped automatically when Tk cannot open a display."""
import time
import tkinter as tk
import unittest
from threading import Event
from unittest.mock import patch
from checkers.app import Application
from checkers.ai import search
from checkers.model import Game


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root=tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.root.withdraw()
        self.app=Application(self.root)

    def tearDown(self):
        if hasattr(self,'app'): self.app.close()

    def pump_until(self,predicate):
        deadline=time.monotonic()+5
        while not predicate() and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.005)
        self.assertTrue(predicate())

    def test_search_completes_and_reports_statistics(self):
        self.app.opponent.set('Computer White')
        self.app.schedule_ai()
        self.pump_until(lambda:self.app.game.turn=='Black')
        self.assertIn('nodes',self.app.analysis.get())
        self.assertFalse(self.app.busy)

    def test_status_remains_visible_at_supported_window_sizes(self):
        # Real Tk geometry is needed: a withdrawn window stays at a dummy size.
        self.root.attributes('-alpha',0)
        self.root.deiconify()
        for width,height in [(960,760),(720,560)]:
            with self.subTest(size=(width,height)):
                self.root.geometry(f'{width}x{height}')
                self.root.update()
                footer=self.app.status_label
                canvas=self.app.view
                self.assertTrue(footer.winfo_ismapped())
                self.assertGreater(footer.winfo_height(),20)
                self.assertLessEqual(footer.winfo_y()+footer.winfo_height(),self.root.winfo_height())
                self.assertLessEqual(canvas.winfo_y()+canvas.winfo_height(),footer.winfo_y())
                self.assertGreater(canvas.winfo_height(),100)

    def test_reset_cancels_worker_and_discards_stale_result(self):
        started,release,finished=Event(),Event(),Event()
        def delayed(game,depth,**kwargs):
            started.set()
            release.wait(3)
            # Deliberately return a stale answer despite cancellation.
            result=search(game,1)
            finished.set()
            return result
        with patch('checkers.app.search',side_effect=delayed):
            self.app.opponent.set('Computer White')
            self.app.schedule_ai()
            self.pump_until(started.is_set)
            old_cancel=self.app.search_cancel
            self.app.opponent.set('Two players')
            self.app.new_game()
            self.assertTrue(old_cancel.is_set())
            release.set()
            self.pump_until(finished.is_set)
            for _ in range(10):
                self.root.update(); time.sleep(.01)
            self.assertEqual(self.app.game,Game.standard())
            self.assertFalse(self.app.busy)


if __name__=='__main__': unittest.main()
