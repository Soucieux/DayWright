import unittest

from backend.app.planner import PlanItem, build_recorded_variants, build_variants, has_collisions, minutes_by_domain


class PlannerTests(unittest.TestCase):
    def test_each_variant_has_no_overlapping_items(self):
        for variant in build_variants():
            self.assertFalse(has_collisions(variant["items"]), variant["name"])

    def test_each_variant_represents_all_core_domains(self):
        for variant in build_variants():
            totals = minutes_by_domain(variant["items"])
            self.assertGreater(totals["learning"], 0)
            self.assertGreater(totals["life"], 0)
            self.assertGreater(totals["finance"], 0)

    def test_variants_make_materially_different_tradeoffs(self):
        totals = {variant["slug"]: minutes_by_domain(variant["items"]) for variant in build_variants()}
        self.assertGreater(totals["focused"]["learning"], totals["gentle"]["learning"])
        self.assertGreater(totals["gentle"]["life"], totals["focused"]["life"])

    def test_short_flexible_task_can_still_have_feasible_variations(self):
        owned = (PlanItem("09:00", "Practice French", "", "learning", 30),
                 PlanItem("12:00", "Dentist", "", "life", 30, "fixed"))
        variants = build_recorded_variants(owned)
        self.assertEqual({variant["slug"] for variant in variants},
                         {"balanced", "focused", "gentle"})
        self.assertEqual([variant["items"][0].duration_minutes for variant in variants],
                         [30, 45, 15])
        self.assertTrue(all(not has_collisions(variant["items"]) for variant in variants))

    def test_repeated_shorten_request_prevents_reextending_disliked_task(self):
        owned = (PlanItem("09:00", "Practice French", "", "learning", 45, protected=True),)
        variants = build_recorded_variants(owned, [{"taskTitle": "Practice French",
                                                     "domain": "learning", "shortenRequests": 2}])
        self.assertEqual(variants[0]["items"][0].duration_minutes, 30)
        self.assertNotIn("focused", [variant["slug"] for variant in variants])
        self.assertEqual(variants[-1]["items"][0].duration_minutes, 15)

    def test_active_summary_size_guidance_prioritizes_gentler_domain(self):
        owned = (PlanItem("09:00", "Study", "", "learning", 60),
                 PlanItem("12:00", "Home care", "", "life", 60))
        guidance = [{"domain": "life", "priority": "soft",
                     "content": "Review the size or timing of life work before the next plan."}]
        gentle = next(variant for variant in build_recorded_variants(
            owned, guidance=guidance) if variant["slug"] == "gentle")
        self.assertEqual([(item.title, item.duration_minutes) for item in gentle["items"]],
                         [("Study", 60), ("Home care", 45)])

    def test_task_cannot_extend_beyond_midnight(self):
        self.assertTrue(has_collisions([PlanItem("23:50", "Late block", "", "life", 30)]))


if __name__ == "__main__":
    unittest.main()
