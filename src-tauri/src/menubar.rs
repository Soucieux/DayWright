//! DayWright in the menu bar: its icon, the title beside it, and one native menu, as the local service words them in
//! the interface's language (`MENU_PATH`; backend/app/menubar.py). The title names the current task, the time it has
//! taken and its set time, and the next task. A left click opens the menu, which is attached to the icon and renewed at
//! every minute's turn and right after any change, so it opens at once; until the service answers, it says DayWright
//! is starting, with Open DayWright, Settings… and Quit working. A right click opens nothing. Closing the window leaves
//! DayWright here. Nothing here notifies.

use std::fs::File;
use std::io::{self, Read, Write};
use std::net::TcpStream;
use std::ptr::NonNull;
use std::sync::mpsc::{self, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex, MutexGuard, OnceLock};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use block2::RcBlock;
use objc2::runtime::AnyObject;
use objc2::MainThreadMarker;
use objc2_app_kit::{NSEvent, NSEventMask};
use serde::Deserialize;
use tauri::image::Image;
use tauri::menu::{IsMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::tray::{TrayIcon, TrayIconBuilder};
use tauri::{App, AppHandle, Manager, Wry};

/// The interface's window.
pub const MAIN_WINDOW: &str = "main";
/// The scheme the window opens to ask the shell for something: daywright://refresh renews the title and menu, as
/// `RENEW_MENU_BAR` in src/api.js asks after any change.
pub const SHELL_SCHEME: &str = "daywright";
/// Where the title and menu come from: `MENU_PATH` in backend/app/main.py.
const MENU_PATH: &str = "/api/now/menu";
/// The session cookie the service admits: `SESSION_COOKIE` in backend/app/desktop.py.
const SESSION_COOKIE: &str = "daywright_session";
/// Every id in the menu starts with this, as Tauri hands a tray's menu events to every menu listener, the app menu's
/// Settings… among them.
const MENU_ID_PREFIX: &str = "menubar:";
/// The menu bar mark's side, in pixels: 18 points at 2x.
const MARK_PIXELS: u32 = 36;
/// How long a request waits for the service.
const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);
/// How long renewing may fail before it is written to the service's log: the service is away for a moment whenever it
/// starts again in place, as a switch of workspace has it do, and that writes nothing. While renewing fails, it is
/// tried again this soon.
const RENEW_GRACE: Duration = Duration::from_secs(10);
/// The menu until the service first answers, before the interface's language is known: the service's own words for it
/// (`_WORDS` in backend/app/menubar.py) take over then.
const STARTING: &str = r#"[{"kind": "line", "text": "DayWright is starting…"}, {"kind": "separator"},
    {"kind": "action", "id": "open", "text": "Open DayWright"},
    {"kind": "action", "id": "settings", "text": "Settings…", "accelerator": "CmdOrCtrl+,"},
    {"kind": "action", "id": "quit", "text": "Quit DayWright", "accelerator": "CmdOrCtrl+Q"}]"#;

/// One item of the menu, as the service gives it.
#[derive(Clone, Debug, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "lowercase")]
enum Item {
    /// A line the menu shows but can't be chosen.
    Line { text: String },
    Separator,
    /// An item chosen by its id, with its keyboard shortcut if it has one.
    Action { id: String, text: String, accelerator: Option<String> },
    Submenu { text: String, items: Vec<Item> },
}

/// The title and menu, and the menu to show while the service doesn't answer, in the same language.
#[derive(Debug, Deserialize)]
struct Model {
    title: String,
    items: Vec<Item>,
    down: Vec<Item>,
}

/// What the menu bar needs from the launch, and keeps from one renewal to the next.
pub struct Shell {
    port: Arc<OnceLock<u16>>,
    secret: String,
    tray: TrayIcon,
    wake: Mutex<Option<Sender<()>>>,
    /// The menu to show while the service doesn't answer, in the language it last answered in.
    down: Mutex<Vec<Item>>,
    /// The service's log, where a failure to renew is written, and the failure under way (see [`failed`]).
    log: Mutex<Option<File>>,
    failure: Mutex<Option<Failing>>,
}

/// A failure to renew the title and menu: why, since when, and whether it was written to the log.
#[derive(Debug)]
struct Failing {
    reason: String,
    since: Instant,
    written: bool,
}

/// Put DayWright in the menu bar, with its mark, no title, and the menu saying DayWright is starting.
pub fn install(app: &App, port: Arc<OnceLock<u16>>, secret: String) -> tauri::Result<()> {
    let starting: Vec<Item> = serde_json::from_str(STARTING).expect("the starting menu is written as the service writes one");
    let tray = TrayIconBuilder::with_id("daywright")
        .icon(Image::new_owned(mark(), MARK_PIXELS, MARK_PIXELS))
        .icon_as_template(true)
        .tooltip("DayWright")
        .menu(&build_menu(app, &starting)?)
        .show_menu_on_left_click(true)
        .on_menu_event(|app, event| choose(app, event.id().as_ref()))
        .build(app)?;
    tray.with_inner_tray_icon(|inner| inner.set_show_menu_on_right_click(false))?;
    hold_right_clicks();
    app.manage(Shell {
        port,
        secret,
        tray,
        wake: Mutex::new(None),
        down: Mutex::new(starting),
        log: Mutex::new(None),
        failure: Mutex::new(None),
    });
    Ok(())
}

/// Renew the title and menu from the service on `port` at every minute's turn, and whenever something changes;
/// a failure to renew is written to `log`.
pub fn keep_menu(app: &AppHandle, port: u16, log: Option<File>) {
    let Some(shell) = app.try_state::<Shell>() else { return };
    *lock(&shell.log) = log;
    let (wake, woken) = mpsc::channel();
    *lock(&shell.wake) = Some(wake);
    let handle = app.clone();
    thread::spawn(move || loop {
        let renewed = show(&handle, port);
        if let Err(RecvTimeoutError::Disconnected) = woken.recv_timeout(next_try(renewed, until_next_minute())) {
            return;
        }
    });
}

/// Renew the title and menu now, as the window asks after a change and the menu after its own.
pub fn renew(app: &AppHandle) {
    if let Some(shell) = app.try_state::<Shell>() {
        if let Some(wake) = lock(&shell.wake).as_ref() {
            let _ = wake.send(());
        }
    }
}

/// Bring the window back, as the menu and the Dock do.
pub fn show_main(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW) {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

/// Ask the service for the title and menu, and show them; or, when it doesn't answer, no title and the menu saying
/// DayWright is starting, with the reason written to the service's log once it has lasted (see [`note`]).
///
/// Returns whether the title and menu were renewed.
fn show(app: &AppHandle, port: u16) -> bool {
    let Some(shell) = app.try_state::<Shell>() else { return false };
    let answer = request(port, &shell.secret, "GET", MENU_PATH, None)
        .and_then(|body| serde_json::from_str::<Model>(&body).map_err(io::Error::other));
    let (title, items, mut renewed) = match answer {
        Ok(model) => {
            *lock(&shell.down) = model.down;
            *lock(&shell.failure) = None;
            (model.title, model.items, true)
        }
        Err(error) => {
            note(&shell, &error.to_string());
            (String::new(), lock(&shell.down).clone(), false)
        }
    };
    match build_menu(app, &items) {
        Ok(menu) => {
            let _ = shell.tray.set_menu(Some(menu));
        }
        Err(error) => {
            note(&shell, &error.to_string());
            renewed = false;
        }
    }
    let _ = shell.tray.set_title(Some(title));
    renewed
}

/// Do what the chosen item says: open the window or Settings, quit, or set a status, pause or resume through the same
/// route the app uses, away from the main thread, then renew the title and menu.
fn choose(app: &AppHandle, id: &str) {
    let Some(action) = id.strip_prefix(MENU_ID_PREFIX) else { return };
    match action {
        "open" => show_main(app),
        "settings" => crate::show_settings(app),
        "quit" => app.exit(0),
        _ => {
            let Some((method, path, body)) = service_request(action) else { return };
            let handle = app.clone();
            thread::spawn(move || {
                if let Some(shell) = handle.try_state::<Shell>() {
                    if let Some(port) = shell.port.get() {
                        if let Err(error) = request(*port, &shell.secret, method, &path, body.as_deref()) {
                            note(&shell, &error.to_string());
                        }
                    }
                }
                renew(&handle);
            });
        }
    }
}

/// The request to the service a menu item makes, exactly as the app makes it: a task's status, or a pause or resume.
///
/// Returns its method, path and body, or None for an item that asks nothing of the service.
fn service_request(action: &str) -> Option<(&'static str, String, Option<String>)> {
    match action {
        "pause" => Some(("POST", "/api/day/pause".to_string(), None)),
        "resume" => Some(("POST", "/api/day/resume".to_string(), None)),
        _ => {
            let (task, status) = action.strip_prefix("status:")?.rsplit_once(':')?;
            let body = serde_json::json!({ "status": status }).to_string();
            Some(("PATCH", format!("/api/daily-items/{task}/status"), Some(body)))
        }
    }
}

/// Send one request to the service on the loopback address, with the session cookie, and answer its body.
fn request(port: u16, secret: &str, method: &str, path: &str, body: Option<&str>) -> io::Result<String> {
    let mut stream = TcpStream::connect(("127.0.0.1", port))?;
    stream.set_read_timeout(Some(REQUEST_TIMEOUT))?;
    stream.write_all(request_text(port, secret, method, path, body).as_bytes())?;
    let mut response = Vec::new();
    stream.read_to_end(&mut response)?;
    let response = String::from_utf8_lossy(&response);
    let (head, body) = response
        .split_once("\r\n\r\n")
        .ok_or_else(|| io::Error::other("the service's answer had no body"))?;
    if !head.starts_with("HTTP/1.1 2") {
        return Err(io::Error::other(head.lines().next().unwrap_or_default().to_string()));
    }
    Ok(body.to_string())
}

/// One HTTP/1.1 request as the shell writes it: closed after the answer, its body JSON.
fn request_text(port: u16, secret: &str, method: &str, path: &str, body: Option<&str>) -> String {
    let body = body.unwrap_or("");
    format!(
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nCookie: {SESSION_COOKIE}={secret}\r\n\
         Content-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )
}

/// The native menu for `items`, each action's id given the prefix; a line can't be chosen.
fn build_menu<M: Manager<Wry>>(app: &M, items: &[Item]) -> tauri::Result<Menu<Wry>> {
    let menu = Menu::new(app)?;
    for item in items {
        menu.append(&*menu_item(app, item)?)?;
    }
    Ok(menu)
}

/// One item of the native menu, a submenu with its own.
fn menu_item<M: Manager<Wry>>(app: &M, item: &Item) -> tauri::Result<Box<dyn IsMenuItem<Wry>>> {
    Ok(match item {
        Item::Line { text } => Box::new(MenuItem::new(app, text, false, None::<&str>)?),
        Item::Separator => Box::new(PredefinedMenuItem::separator(app)?),
        Item::Action { id, text, accelerator } => {
            Box::new(MenuItem::with_id(app, format!("{MENU_ID_PREFIX}{id}"), text, true, accelerator.as_deref())?)
        }
        Item::Submenu { text, items } => {
            let submenu = Submenu::new(app, text, true)?;
            for item in items {
                submenu.append(&*menu_item(app, item)?)?;
            }
            Box::new(submenu)
        }
    })
}

/// Hold back a right click on the menu bar's icon before AppKit sees it, so it opens nothing. A status item with a
/// menu shows it on any click AppKit handles itself, as 5.4–5.6's showed theirs on a left click their click handler
/// never saw; tray-icon's own view keeps a right click from it too (set_show_menu_on_right_click). DayWright has one
/// status item, so a right click in any status bar window of its own is on its icon.
fn hold_right_clicks() {
    let Some(main_thread) = MainThreadMarker::new() else { return };
    let handler = RcBlock::new(move |event: NonNull<NSEvent>| -> *mut NSEvent {
        // SAFETY: AppKit hands the monitor a valid event, on the main thread.
        let window = unsafe { event.as_ref() }.window(main_thread);
        let on_icon = window.is_some_and(|window| {
            let object: &AnyObject = &window;
            object.class().name().to_bytes().starts_with(b"NSStatusBar")
        });
        if on_icon {
            std::ptr::null_mut()
        } else {
            event.as_ptr()
        }
    });
    // SAFETY: called on the main thread; the handler returns the event, or nothing to hold it back.
    let monitor = unsafe {
        NSEvent::addLocalMonitorForEventsMatchingMask_handler(
            NSEventMask::RightMouseDown | NSEventMask::RightMouseUp,
            &handler,
        )
    };
    // The monitor holds for as long as DayWright runs.
    std::mem::forget(monitor);
}

/// Keep that the menu bar couldn't be renewed, for `reason`, and write it to the service's log as [`failed`] says.
fn note(shell: &Shell, reason: &str) {
    let mut failure = lock(&shell.failure);
    let (failing, line) = failed(failure.take(), reason, Instant::now());
    *failure = Some(failing);
    if let (Some(line), Some(log)) = (line, lock(&shell.log).as_mut()) {
        let _ = writeln!(log, "{line}");
    }
}

/// The failure after a try at `now` failed for `reason`, and the line to write to the log, if any: none until the
/// failure has lasted [`RENEW_GRACE`], then one, and another only for another reason.
fn failed(before: Option<Failing>, reason: &str, now: Instant) -> (Failing, Option<String>) {
    let mut failing = before.unwrap_or_else(|| Failing { reason: reason.to_string(), since: now, written: false });
    if failing.reason != reason {
        failing = Failing { reason: reason.to_string(), written: false, ..failing };
    }
    let due = !failing.written && now.duration_since(failing.since) >= RENEW_GRACE;
    failing.written |= due;
    (failing, due.then(|| format!("DayWright's menu bar couldn't be renewed: {reason}")))
}

/// How long to wait before renewing again: until the minute's turn, or while renewing fails, [`RENEW_GRACE`] at most.
fn next_try(renewed: bool, until_minute: Duration) -> Duration {
    if renewed {
        until_minute
    } else {
        until_minute.min(RENEW_GRACE)
    }
}

/// A shared value, even after a thread panicked while holding it.
fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(|poisoned| poisoned.into_inner())
}

/// The time left until the next minute's turn, by the clock.
fn until_next_minute() -> Duration {
    let into = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() % 60_000;
    Duration::from_millis((60_000 - into) as u64)
}

/// The menu bar mark as a template image, black on clear for macOS to tint: the app icon's ring, open
/// at the bottom, around its check. Each pixel's coverage is sampled on a 4 × 4 grid.
fn mark() -> Vec<u8> {
    const SAMPLES: u32 = 4;
    let unit = f64::from(MARK_PIXELS) / 24.0;
    let mut pixels = Vec::with_capacity((MARK_PIXELS * MARK_PIXELS * 4) as usize);
    for y in 0..MARK_PIXELS {
        for x in 0..MARK_PIXELS {
            let mut covered = 0;
            for sample in 0..SAMPLES * SAMPLES {
                let u = (f64::from(x) + (f64::from(sample % SAMPLES) + 0.5) / f64::from(SAMPLES)) / unit;
                let v = (f64::from(y) + (f64::from(sample / SAMPLES) + 0.5) / f64::from(SAMPLES)) / unit;
                covered += u32::from(on_mark(u, v));
            }
            pixels.extend([0, 0, 0, (covered * 255 / (SAMPLES * SAMPLES)) as u8]);
        }
    }
    pixels
}

/// Whether a point of the 24-unit icon grid is on the mark's strokes, 2 units wide.
fn on_mark(u: f64, v: f64) -> bool {
    let (dx, dy) = (u - 12.0, v - 12.0);
    let ring = ((dx * dx + dy * dy).sqrt() - 9.5).abs() <= 1.0 && !(dy > 0.0 && dx.abs() < dy);
    ring || near_segment(u, v, (7.6, 12.2), (10.6, 15.2)) || near_segment(u, v, (10.6, 15.2), (16.4, 9.0))
}

/// Whether (u, v) lies within 1 unit of the segment from `a` to `b`.
fn near_segment(u: f64, v: f64, a: (f64, f64), b: (f64, f64)) -> bool {
    let (ex, ey) = (b.0 - a.0, b.1 - a.1);
    let along = (((u - a.0) * ex + (v - a.1) * ey) / (ex * ex + ey * ey)).clamp(0.0, 1.0);
    let (px, py) = (a.0 + along * ex - u, a.1 + along * ey - v);
    px * px + py * py <= 1.0
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A menu as backend/app/menubar.py writes one, from its test's fixed data.
    const SERVICE_MENU: &str = r#"{"title": "Review the quar… · 32 / 60 min · next: Email Anna",
        "items": [{"kind": "line", "text": "Now"}, {"kind": "line", "text": "Review the quarterly figures with Anna"},
            {"kind": "line", "text": "32 min of 60 min (you set)"},
            {"kind": "submenu", "text": "Set status", "items": [
                {"kind": "action", "id": "status:item_review:done", "text": "Done"},
                {"kind": "action", "id": "status:item_review:partial", "text": "Partly done"},
                {"kind": "action", "id": "status:item_review:skipped", "text": "Skipped"}]},
            {"kind": "line", "text": "Next"}, {"kind": "line", "text": "Nothing next today"}, {"kind": "separator"},
            {"kind": "action", "id": "pause", "text": "Pause the day"}, {"kind": "separator"},
            {"kind": "action", "id": "open", "text": "Open DayWright"},
            {"kind": "action", "id": "settings", "text": "Settings…", "accelerator": "CmdOrCtrl+,"},
            {"kind": "action", "id": "quit", "text": "Quit DayWright", "accelerator": "CmdOrCtrl+Q"}],
        "down": [{"kind": "line", "text": "DayWright is starting…"}]}"#;

    #[test]
    fn the_services_menu_reads_whole_with_its_submenu_and_shortcuts() {
        let model: Model = serde_json::from_str(SERVICE_MENU).unwrap();
        assert_eq!(model.title, "Review the quar… · 32 / 60 min · next: Email Anna");
        assert_eq!(model.items.len(), 12);
        assert_eq!(model.items[0], Item::Line { text: "Now".into() });
        let Item::Submenu { text, items } = &model.items[3] else { panic!("Set status is a submenu") };
        assert_eq!((text.as_str(), items.len()), ("Set status", 3));
        assert_eq!(
            model.items[11],
            Item::Action { id: "quit".into(), text: "Quit DayWright".into(), accelerator: Some("CmdOrCtrl+Q".into()) }
        );
        assert_eq!(model.down, vec![Item::Line { text: "DayWright is starting…".into() }]);
    }

    #[test]
    fn until_the_service_answers_the_menu_says_daywright_is_starting_and_the_rest_works() {
        let starting: Vec<Item> = serde_json::from_str(STARTING).unwrap();
        assert_eq!(starting[0], Item::Line { text: "DayWright is starting…".into() });
        let ids: Vec<&str> = starting
            .iter()
            .filter_map(|item| match item {
                Item::Action { id, .. } => Some(id.as_str()),
                _ => None,
            })
            .collect();
        assert_eq!(ids, ["open", "settings", "quit"]);
    }

    #[test]
    fn a_status_pause_or_resume_from_the_menu_is_the_apps_own_request() {
        // The app: api(`/api/daily-items/${task.id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }).
        assert_eq!(
            service_request("status:item_review:partial"),
            Some(("PATCH", "/api/daily-items/item_review/status".to_string(), Some(r#"{"status":"partial"}"#.to_string())))
        );
        // The app: api("/api/day/pause", { method: "POST" }) and api("/api/day/resume", { method: "POST" }).
        assert_eq!(service_request("pause"), Some(("POST", "/api/day/pause".to_string(), None)));
        assert_eq!(service_request("resume"), Some(("POST", "/api/day/resume".to_string(), None)));
        assert_eq!(service_request("open"), None);
        assert_eq!(service_request("status:nothing"), None);
    }

    #[test]
    fn each_request_carries_the_session_cookie_and_its_bodys_length() {
        let text = request_text(8425, "secret", "PATCH", "/api/daily-items/item_a/status", Some(r#"{"status":"done"}"#));
        assert!(text.starts_with("PATCH /api/daily-items/item_a/status HTTP/1.1\r\nHost: 127.0.0.1:8425\r\n"));
        assert!(text.contains("\r\nCookie: daywright_session=secret\r\n"));
        assert!(text.contains("\r\nContent-Length: 17\r\nConnection: close\r\n\r\n{\"status\":\"done\"}"));
        assert!(request_text(8425, "secret", "GET", MENU_PATH, None).ends_with("Content-Length: 0\r\nConnection: close\r\n\r\n"));
    }

    const REFUSED: &str = "Connection refused (os error 61)";

    #[test]
    fn a_refusal_shorter_than_the_grace_as_a_restart_in_place_makes_writes_nothing() {
        let start = Instant::now();
        let (failing, line) = failed(None, REFUSED, start);
        assert_eq!(line, None);
        let (_, line) = failed(Some(failing), REFUSED, start + RENEW_GRACE - Duration::from_secs(1));
        assert_eq!(line, None);
    }

    #[test]
    fn a_refusal_lasting_past_the_grace_is_written_once_and_again_only_for_another_reason() {
        let start = Instant::now();
        let (failing, line) = failed(None, REFUSED, start);
        assert_eq!(line, None);
        let (failing, line) = failed(Some(failing), REFUSED, start + RENEW_GRACE);
        assert_eq!(line.as_deref(), Some("DayWright's menu bar couldn't be renewed: Connection refused (os error 61)"));
        let (failing, line) = failed(Some(failing), REFUSED, start + RENEW_GRACE * 6);
        assert_eq!(line, None);
        let (_, line) = failed(Some(failing), "timed out", start + RENEW_GRACE * 7);
        assert_eq!(line.as_deref(), Some("DayWright's menu bar couldn't be renewed: timed out"));
    }

    #[test]
    fn while_renewing_fails_the_next_try_comes_within_the_grace() {
        assert_eq!(next_try(false, Duration::from_secs(50)), RENEW_GRACE);
        assert_eq!(next_try(false, Duration::from_secs(3)), Duration::from_secs(3));
        assert_eq!(next_try(true, Duration::from_secs(50)), Duration::from_secs(50));
    }
}
