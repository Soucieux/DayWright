import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.menubar import menu_model
from backend.tests.test_time_record import TimeDay


def task(title, start, minutes=60, source="user", task_id="item_review"):
    return {"id": task_id, "title": title, "start": start, "minutes": minutes, "durationSource": source, "domain": "work",
            "status": "planned"}


def now(current=None, upcoming=None, taken=0, paused=None, title=""):
    return {"current": current, "next": upcoming, "taken": taken, "pausedSince": paused, "title": title}


def lines(items):
    """Each item as a short line: its text, a submenu's items after ▸, a separator as ---, an action's id in brackets."""
    shown = []
    for item in items:
        if item["kind"] == "separator":
            shown.append("---")
        elif item["kind"] == "submenu":
            shown.append(f"{item['text']} ▸ " + " · ".join(f"{entry['text']} [{entry['id']}]" for entry in item["items"]))
        elif item["kind"] == "action":
            shown.append(f"{item['text']} [{item['id']}]" + (f" {item['accelerator']}" if item.get("accelerator") else ""))
        else:
            shown.append(item["text"])
    return shown


class MenuModelTests(unittest.TestCase):
    """The menu a left click on the menu bar's icon opens, from fixed data, in either language."""

    def test_now_and_next_each_with_their_lines_and_set_status(self):
        review = task("Review the quarterly figures with Anna", "14:00")
        email = task("Email Anna", "15:00", 20, "agent", "item_email")
        model = menu_model(now(review, email, 32, title="Review the quar… · 32 / 60 min · next: Email Anna"), "en")

        self.assertEqual(model["title"], "Review the quar… · 32 / 60 min · next: Email Anna")
        self.assertEqual(lines(model["items"]), [
            "Now",
            "Review the quarterly figures with Anna",
            "32 min of 60 min (you set)",
            "Set status ▸ Done [status:item_review:done] · Partly done [status:item_review:partial] · Skipped [status:item_review:skipped]",
            "Next",
            "Email Anna · 15:00 · 20 min",
            "Set status ▸ Done [status:item_email:done] · Partly done [status:item_email:partial] · Skipped [status:item_email:skipped]",
            "---",
            "Pause the day [pause]",
            "---",
            "Open DayWright [open]",
            "Settings… [settings] CmdOrCtrl+,",
            "Quit DayWright [quit] CmdOrCtrl+Q",
        ])
        self.assertTrue(all("id" not in item for item in model["items"] if item["kind"] == "line"), "lines are disabled")

    def test_an_estimated_length_and_an_untimed_next_task(self):
        model = menu_model(now(task("Read", None, 45, "agent"), task("Walk", None, 30, task_id="item_walk"), 10), "en")

        self.assertIn("10 min of 45 min (estimated)", lines(model["items"]))
        self.assertIn("Walk · Untimed · 30 min", lines(model["items"]))

    def test_nothing_now_or_next_says_so_and_the_rest_works(self):
        model = menu_model(now(), "en")

        self.assertEqual(lines(model["items"])[:4], ["Now", "Nothing planned now", "Next", "Nothing next today"])
        self.assertIn("Pause the day [pause]", lines(model["items"]))
        self.assertEqual(model["title"], "", "the icon alone")

    def test_while_paused_resume_comes_with_when_it_was_paused(self):
        model = menu_model(now(paused="14:10", title="Paused since 14:10"), "en")

        shown = lines(model["items"])
        self.assertEqual(shown[shown.index("---") + 1:shown.index("---") + 3], ["Paused since 14:10", "Resume the day [resume]"])
        self.assertNotIn("Pause the day [pause]", shown)
        self.assertEqual(model["title"], "Paused since 14:10")

    def test_while_the_service_doesnt_answer_the_menu_says_daywright_is_starting(self):
        model = menu_model(now(), "en")

        self.assertEqual(lines(model["down"]), ["DayWright is starting…", "---", "Open DayWright [open]",
                                                "Settings… [settings] CmdOrCtrl+,", "Quit DayWright [quit] CmdOrCtrl+Q"])

    def test_in_chinese(self):
        model = menu_model(now(task("复习季度数字", "14:00"), None, 5, title="复习季度数字 · 5 / 60 分钟"), "zh")

        self.assertEqual(lines(model["items"])[:4], ["当前", "复习季度数字", "已用 5 分钟，共 60 分钟（你设定）",
                                                     "设置状态 ▸ 已完成 [status:item_review:done] · 部分完成 [status:item_review:partial] · "
                                                     "已跳过 [status:item_review:skipped]"])
        self.assertIn("今天没有下一项", lines(model["items"]))
        self.assertEqual(lines(model["down"])[0], "DayWright 正在启动…")
        self.assertIn("退出 DayWright [quit] CmdOrCtrl+Q", lines(model["items"]))

    def test_in_the_demo_the_title_says_so_first(self):
        self.assertEqual(menu_model(now(title="Next: Email Anna"), "en", demo=True)["title"], "Demo · Next: Email Anna")
        self.assertEqual(menu_model(now(), "zh", demo=True)["title"], "演示")


class MenuRouteTests(TimeDay):
    """The shell reads the title and menu at one address, with the session cookie, once a minute and after each change."""

    def test_the_menu_holds_the_days_tasks_and_a_status_from_it_records_as_from_the_app(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        with self.at("14:32"):
            menu = self.client.get("/api/now/menu").json()
        self.assertEqual(menu["title"], "Review · 32 / 60 min · next: Email Anna")
        self.assertIn("Review", lines(menu["items"]))
        self.assertIn("Email Anna · 15:30 · 30 min", lines(menu["items"]))
        status = next(item for item in menu["items"] if item["kind"] == "submenu")["items"][0]
        self.assertEqual(status["id"], f"status:{review['id']}:done")

        self.report(review, "done", "14:40")
        with self.at("14:41"):
            after = self.client.get("/api/now/menu").json()
        self.assertEqual(self.timing(review), ("done", "14:40", "14:00", "14:40"))
        self.assertEqual(lines(after["items"])[:4], ["Now", "Nothing planned now", "Next", "Email Anna · 15:30 · 30 min"],
                         "done, Review leaves Now; Email Anna isn't under way until 15:30")

    def test_the_menu_speaks_the_interface_language(self):
        self.add("Review", "14:00")
        self.client.put("/api/interface-language", json={"language": "zh"})
        with self.at("14:05"):
            menu = self.client.get("/api/now/menu").json()
        self.assertEqual(menu["title"], "Review · 5 / 60 分钟")
        self.assertEqual(lines(menu["items"])[0], "当前")
