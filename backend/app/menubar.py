"""What DayWright's menu bar shows: the title beside its icon, and the one native menu a left click on it opens, in the
interface's language. The desktop shell builds the menu from this as it is (src-tauri/src/menubar.rs), so the menu is
there at once, even before the service answers again; each of its actions goes through the same route as the app's.
Nothing here notifies."""

from .time_taken import demo_title

# The menu's words in the interface's two languages.
_WORDS = {
    "en": {"now": "Now", "next": "Next", "nothingNow": "Nothing planned now", "nothingNext": "Nothing next today",
           "taken": "{taken} min of {minutes} min ({whose})", "yours": "you set", "estimated": "estimated",
           "nextLine": "{title} · {start} · {minutes} min", "untimed": "Untimed", "setStatus": "Set status",
           "done": "Done", "partial": "Partly done", "skipped": "Skipped", "pause": "Pause the day",
           "resume": "Resume the day", "paused": "Paused since {time}", "open": "Open DayWright", "settings": "Settings…",
           "quit": "Quit DayWright", "starting": "DayWright is starting…"},
    "zh": {"now": "当前", "next": "下一项", "nothingNow": "现在没有安排", "nothingNext": "今天没有下一项",
           "taken": "已用 {taken} 分钟，共 {minutes} 分钟（{whose}）", "yours": "你设定", "estimated": "估计",
           "nextLine": "{title} · {start} · {minutes} 分钟", "untimed": "未定时", "setStatus": "设置状态",
           "done": "已完成", "partial": "部分完成", "skipped": "已跳过", "pause": "暂停今天", "resume": "继续今天",
           "paused": "{time} 起已暂停", "open": "打开 DayWright", "settings": "设置…", "quit": "退出 DayWright",
           "starting": "DayWright 正在启动…"},
}
# The statuses Set status offers, in their order.
_STATUSES = ("done", "partial", "skipped")
_SEPARATOR = {"kind": "separator"}


def _line(text: str) -> dict:
    """A line the menu shows but can't be chosen."""
    return {"kind": "line", "text": text}


def _action(action_id: str, text: str, accelerator: str | None = None) -> dict:
    """An item the menu acts on when chosen, by its id, with its keyboard shortcut if it has one."""
    return {"kind": "action", "id": action_id, "text": text, **({"accelerator": accelerator} if accelerator else {})}


def _set_status(task: dict, words: dict) -> dict:
    """Set status ▸ for one task: each status, chosen as from the app."""
    return {"kind": "submenu", "text": words["setStatus"],
            "items": [_action(f"status:{task['id']}:{status}", words[status]) for status in _STATUSES]}


def _app_actions(words: dict) -> list[dict]:
    """The menu's last items, which work whatever the day holds and whether or not the service answers."""
    return [_action("open", words["open"]), _action("settings", words["settings"], "CmdOrCtrl+,"),
            _action("quit", words["quit"], "CmdOrCtrl+Q")]


def menu_model(now: dict, language: str, demo: bool = False) -> dict:
    """Return the menu bar's title and menu for what `now` holds.

    The menu: Now, the current task's full title, its time taken of its set time and whose that time is, and Set
    status ▸; Next, the next task with its start (or Untimed) and length, and its own Set status ▸; or a line saying
    there is none. Then Pause the day, or, while paused, when it was paused and Resume the day; then Open DayWright,
    Settings… and Quit DayWright.

    Args:
        now: What Database.now gives: "current", "next", "taken", "pausedSince" and "title".
        language: The interface's language, "en" or "zh".
        demo: Whether the demo workspace is open, which the title then says first.

    Returns:
        {"title", "items", "down"}: the title beside the icon ("" for the icon alone); the menu's items in order, each
        {"kind": "line" | "submenu" | "action" | "separator"} with its "text", an action's "id" and "accelerator", a
        submenu's "items"; and the menu to show while the service doesn't answer, in the same language.
    """
    words = _WORDS[language]
    current, upcoming = now["current"], now["next"]
    items = [_line(words["now"])]
    if current:
        whose = words["yours"] if current["durationSource"] == "user" else words["estimated"]
        items += [_line(current["title"]), _line(words["taken"].format(taken=now["taken"], minutes=current["minutes"], whose=whose)),
                  _set_status(current, words)]
    else:
        items.append(_line(words["nothingNow"]))
    items.append(_line(words["next"]))
    if upcoming:
        items += [_line(words["nextLine"].format(title=upcoming["title"], start=upcoming["start"] or words["untimed"],
                                                 minutes=upcoming["minutes"])), _set_status(upcoming, words)]
    else:
        items.append(_line(words["nothingNext"]))
    items.append(_SEPARATOR)
    if now["pausedSince"]:
        items += [_line(words["paused"].format(time=now["pausedSince"])), _action("resume", words["resume"])]
    else:
        items.append(_action("pause", words["pause"]))
    return {"title": demo_title(now["title"], language) if demo else now["title"],
            "items": [*items, _SEPARATOR, *_app_actions(words)],
            "down": [_line(words["starting"]), _SEPARATOR, *_app_actions(words)]}
