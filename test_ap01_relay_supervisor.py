import unittest
from ap01_relay_supervisor import HealthWatch, healthy_relay


class RelayHealthTests(unittest.TestCase):
    def test_online_tunnel_is_withdrawn_on_first_failure_and_recycled(self):
        watch = HealthWatch(0)
        self.assertEqual(watch.observe(True, 5), (True, False))
        self.assertEqual(watch.observe(False, 25), (False, False))
        self.assertEqual(watch.observe(False, 45), (False, False))
        self.assertEqual(watch.observe(False, 65), (False, True))

    def test_recovery_clears_previous_failures(self):
        watch = HealthWatch(0)
        watch.observe(True, 5)
        watch.observe(False, 25)
        self.assertEqual(watch.observe(True, 45), (True, False))
        self.assertEqual(watch.observe(False, 65), (False, False))

    def test_never_ready_tunnel_has_startup_deadline(self):
        watch = HealthWatch(0, startup_timeout=180)
        self.assertEqual(watch.observe(False, 179), (False, False))
        self.assertEqual(watch.observe(False, 180), (False, True))

    def test_http_success_is_not_enough(self):
        self.assertFalse(healthy_relay({'ok': True}))
        self.assertFalse(healthy_relay('<html>portal</html>'))
        self.assertTrue(healthy_relay({'ok': True, 'service': 'cuktech-ap01-fds-relay',
                                      'api_version': 1, 'firmware': '1.0.2_0031'}))


if __name__ == '__main__':
    unittest.main()
