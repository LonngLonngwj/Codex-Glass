import math
import unittest
from quota import Window, Lifecycle, parse_snapshot, choose_bucket, alert_key, desktop_kind, observed_consumption, tone
from geometry import CARD, BUBBLE, contour, inside_card, settle_offset


class QuotaTests(unittest.TestCase):
    def test_multibucket_preferred_over_legacy(self):
        s = parse_snapshot({"rateLimits": {"primary": {"usedPercent": 1}}, "rateLimitsByLimitId": {
            "extra": {"primary": {"usedPercent": 98}}, "codex": {"primary": {"usedPercent": 53, "windowDurationMins": 300}}}})
        self.assertEqual(choose_bucket(s)["primary"].remaining, 47)
        self.assertEqual(choose_bucket(s, "extra")["primary"].remaining, 2)
        self.assertEqual(choose_bucket(s, "unknown")["id"], "codex")

    def test_unknown_not_full(self):
        for value in (None, {}, {"usedPercent": None}, {"usedPercent": "0"}, {"usedPercent": True}):
            s = parse_snapshot({"rateLimits": {"primary": value}})
            self.assertIsNone(choose_bucket(s)["primary"])

    def test_clamping_and_expiry(self):
        self.assertEqual(Window(-2, 300, 100).remaining, 100)
        self.assertEqual(Window(120, 300, 100).remaining, 0)
        view = Window(25, 300, 100).view(101)
        self.assertEqual(view["number"], "—")
        self.assertFalse(view["valid"])
        self.assertEqual(view["fraction"], 0)

    def test_duration_and_countdown(self):
        self.assertEqual(Window(1, 300, None).label, "5 小时")
        self.assertEqual(Window(1, 10080, None).label, "每周")
        self.assertEqual(Window(1, 60, None).label, "1 小时")
        self.assertEqual(Window(1, 60, 61).countdown(1), "1分钟后")
        self.assertEqual(Window(1, 60, None).countdown(1), "重置时间未知")

    def test_empty_response_rejected(self):
        for data in ({}, {"result": {}}, {"error": {"message": "failure"}}):
            with self.assertRaises(ValueError):
                parse_snapshot(data)

    def test_low_alert_drift_and_escalation(self):
        first = alert_key(Window(82, 300, 5000), "codex", "primary", 100, [])
        self.assertIsNotNone(first)
        self.assertIsNone(alert_key(Window(83, 300, 5001), "codex", "primary", 100, [first]))
        self.assertIsNotNone(alert_key(Window(92, 300, 5000), "codex", "primary", 100, [first]))
        self.assertIsNone(alert_key(Window(99, 300, 5000), "codex", "primary", 5001, []))


class FollowTests(unittest.TestCase):
    def test_current_codex_renamed_chatgpt(self):
        self.assertEqual(desktop_kind("ChatGPT.exe", r"C:\Program Files\WindowsApps\OpenAI.Codex_26.9\app\ChatGPT.exe"), "codex")
        self.assertEqual(desktop_kind("ChatGPT.exe", r"C:\Program Files\WindowsApps\OpenAI.ChatGPT_1.0\app\ChatGPT.exe"), "chatgpt")
        self.assertIsNone(desktop_kind("codex.exe", r"C:\Users\A\AppData\Local\OpenAI\Codex\bin\hash\codex.exe"))

    def test_show_hide_restart(self):
        state = Lifecycle()
        self.assertFalse(state.update(False)[0])
        self.assertTrue(state.update(True)[0])
        state.hide()
        self.assertFalse(state.update(True)[0])
        self.assertFalse(state.update(False)[0])
        self.assertTrue(state.update(True)[0])

    def test_manual_reveal_without_host(self):
        state = Lifecycle()
        state.reveal()
        self.assertTrue(state.update(False)[0])
        self.assertTrue(state.update(True)[0])
        self.assertFalse(state.update(False)[0])


class ShapeTests(unittest.TestCase):
    def test_squircle_transparent_corners_and_full_center(self):
        self.assertFalse(inside_card(0, 0))
        self.assertFalse(inside_card(CARD, 0))
        self.assertTrue(inside_card(CARD/2, 0))
        self.assertTrue(inside_card(CARD/2, CARD/2))
        for x, y in contour():
            self.assertTrue(math.isfinite(x) and math.isfinite(y))
            self.assertTrue(0 <= x <= CARD and 0 <= y <= CARD)

    def test_inertia_bounded_even_at_high_velocity(self):
        for vx, vy in ((0, 0), (1000, 1000), (-10000, 0), (120, -80)):
            x, y = settle_offset(vx, vy)
            self.assertLessEqual(math.hypot(x, y), 10.7)  # <= 10 before pixel rounding

    def test_bubble_hit_shape_excludes_corners(self):
        self.assertFalse(inside_card(0, 0, size=BUBBLE, radius=23))
        self.assertTrue(inside_card(BUBBLE/2, BUBBLE/2, size=BUBBLE, radius=23))

    def test_quota_tint_thresholds(self):
        for remaining, expected in ((100, "blue"), (50, "blue"), (49, "cream"), (11, "cream"), (10, "peach"), (0, "peach")):
            self.assertEqual(tone(Window(100-remaining, 300, 200), 100), expected)
        self.assertEqual(tone(Window(99, 300, 99), 100), "blue")

    def test_observed_consumption_ignores_resets(self):
        prev = {"primary": Window(20, 300, 2000)}
        self.assertTrue(observed_consumption(prev, {"primary": Window(21, 300, 2001)}))
        self.assertFalse(observed_consumption(prev, {"primary": Window(21, 300, 6000)}))

    def test_reset_credit_metadata_is_read_only_and_unknown_preserved(self):
        source = {"rateLimits": {"planType": "plus", "primary": {"usedPercent": 30}},
                  "rateLimitResetCredits": {"availableCount": 1, "credits": [{"status": "available", "expiresAt": 300, "id": "private"}]}}
        bucket = choose_bucket(parse_snapshot(source))
        self.assertEqual(bucket["plan"], "plus")
        self.assertEqual(bucket["resetCredits"], {"availableCount": 1, "expires": [300.]})
        self.assertIsNone(choose_bucket(parse_snapshot({"rateLimits": {}}))["resetCredits"])


if __name__ == "__main__":
    unittest.main()
