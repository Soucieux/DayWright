//! DayWright in the menu bar. Its title names the current task, the time it has taken and its set
//! time, and the next task, as the local service words it; the title is renewed once a minute and
//! whenever the panel reports a task. A click opens a small panel to report either task or open
//! DayWright, and its menu opens the window or quits. Closing the window leaves DayWright here.
//! Nothing here notifies.

use std::io::{self, Read, Write};
use std::net::TcpStream;
use std::sync::mpsc::{self, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent};
use tauri::{
    App, AppHandle, Manager, PhysicalPosition, Rect, Url, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder, WindowEvent,
};

/// The interface's window.
pub const MAIN_WINDOW: &str = "main";
/// The panel's window, and the view it opens its session on: `PANEL_VIEW` in backend/app/desktop.py.
const PANEL: &str = "menubar";
const PANEL_VIEW: &str = "menubar";
/// Where the title comes from: `TITLE_PATH` in backend/app/main.py.
const TITLE_PATH: &str = "/api/now/title";
/// The session cookie the service admits: `SESSION_COOKIE` in backend/app/desktop.py.
const SESSION_COOKIE: &str = "daywright_session";
/// The panel asks the shell for something by opening daywright://open or daywright://refresh.
const SHELL_SCHEME: &str = "daywright";
/// The panel's size, in points, and its gap below the menu bar.
const PANEL_WIDTH: f64 = 380.0;
const PANEL_HEIGHT: f64 = 420.0;
const PANEL_GAP: f64 = 6.0;
/// The menu bar mark's side, in pixels: 18 points at 2x.
const MARK_PIXELS: u32 = 36;
/// How long the title waits for the service before it is left as it was.
const TITLE_TIMEOUT: Duration = Duration::from_secs(10);
/// A click on the mark while the panel shows takes the panel's focus first, which hides it; the click
/// that arrives this soon after is the same one, closing the panel rather than opening it again.
const REOPEN_GUARD: Duration = Duration::from_millis(300);

/// What the menu bar needs from the launch: the service's port once it answers, and the launch secret;
/// and when the panel last hid on losing focus.
pub struct Shell {
    port: Arc<OnceLock<u16>>,
    secret: String,
    tray: TrayIcon,
    wake: Mutex<Option<Sender<()>>>,
    hidden_at: Mutex<Option<Instant>>,
}

/// Put DayWright in the menu bar, with its mark, an empty title until the service answers, and its menu.
pub fn install(app: &App, port: Arc<OnceLock<u16>>, secret: String) -> tauri::Result<()> {
    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "open", "Open DayWright", true, None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "quit", "Quit DayWright", true, None::<&str>)?,
        ],
    )?;
    let tray = TrayIconBuilder::with_id("daywright")
        .icon(Image::new_owned(mark(), MARK_PIXELS, MARK_PIXELS))
        .icon_as_template(true)
        .tooltip("DayWright")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show_main(app),
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                rect,
                ..
            } = event
            {
                toggle_panel(tray.app_handle(), rect);
            }
        })
        .build(app)?;
    app.manage(Shell { port, secret, tray, wake: Mutex::new(None), hidden_at: Mutex::new(None) });
    Ok(())
}

/// Renew the title from the service on `port` at every minute's turn, and whenever the panel asks.
pub fn keep_title(app: &AppHandle, port: u16) {
    let Some(shell) = app.try_state::<Shell>() else { return };
    let (wake, woken) = mpsc::channel();
    *shell.wake.lock().unwrap_or_else(|poisoned| poisoned.into_inner()) = Some(wake);
    let tray = shell.tray.clone();
    let secret = shell.secret.clone();
    thread::spawn(move || loop {
        match fetch_title(port, &secret) {
            Ok(title) => {
                let _ = tray.set_title(Some(title));
            }
            Err(error) => eprintln!("DayWright's menu bar title was not renewed: {error}"),
        }
        if let Err(RecvTimeoutError::Disconnected) = woken.recv_timeout(until_next_minute()) {
            return;
        }
    });
}

/// Bring the window back, as the menu, the panel and the Dock do.
pub fn show_main(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW) {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

/// The time left until the next minute's turn, by the clock.
fn until_next_minute() -> Duration {
    let into = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() % 60_000;
    Duration::from_millis((60_000 - into) as u64)
}

/// Ask the service for the title, as one plain-text line, with the session cookie.
fn fetch_title(port: u16, secret: &str) -> io::Result<String> {
    let mut stream = TcpStream::connect(("127.0.0.1", port))?;
    stream.set_read_timeout(Some(TITLE_TIMEOUT))?;
    write!(
        stream,
        "GET {TITLE_PATH} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nCookie: {SESSION_COOKIE}={secret}\r\nConnection: close\r\n\r\n"
    )?;
    let mut response = Vec::new();
    stream.read_to_end(&mut response)?;
    let response = String::from_utf8_lossy(&response);
    let (head, body) = response
        .split_once("\r\n\r\n")
        .ok_or_else(|| io::Error::other("the service's answer had no body"))?;
    if !head.starts_with("HTTP/1.1 200") {
        return Err(io::Error::other(head.lines().next().unwrap_or_default().to_string()));
    }
    Ok(body.trim().to_string())
}

/// Show the panel below the mark, or hide it when it shows. It opens once the service answers.
fn toggle_panel(app: &AppHandle, rect: Rect) {
    let panel = match app.get_webview_window(PANEL) {
        Some(panel) => panel,
        None => match open_panel(app) {
            Some(panel) => panel,
            None => return,
        },
    };
    if panel.is_visible().unwrap_or(false) {
        let _ = panel.hide();
        return;
    }
    if app.try_state::<Shell>().is_some_and(|shell| {
        shell.hidden_at.lock().unwrap_or_else(|poisoned| poisoned.into_inner()).is_some_and(|at| at.elapsed() < REOPEN_GUARD)
    }) {
        return;
    }
    let scale = panel.scale_factor().unwrap_or(1.0);
    let at = rect.position.to_physical::<f64>(scale);
    let size = rect.size.to_physical::<f64>(scale);
    let _ = panel.set_position(PhysicalPosition::new(
        at.x + size.width / 2.0 - PANEL_WIDTH * scale / 2.0,
        at.y + size.height + PANEL_GAP * scale,
    ));
    let _ = panel.show();
    let _ = panel.set_focus();
}

/// Make the panel: a small borderless window at the service's panel view, hidden when it loses focus.
/// It reaches the shell only through daywright:// addresses; any other site opens in the browser.
fn open_panel(app: &AppHandle) -> Option<WebviewWindow> {
    let shell = app.try_state::<Shell>()?;
    let port = *shell.port.get()?;
    let address = format!(
        "http://127.0.0.1:{port}{}?token={}&view={PANEL_VIEW}",
        crate::SESSION_PATH,
        shell.secret
    );
    let handle = app.clone();
    let panel = WebviewWindowBuilder::new(app, PANEL, WebviewUrl::External(address.parse().ok()?))
        .title("DayWright")
        .inner_size(PANEL_WIDTH, PANEL_HEIGHT)
        .resizable(false)
        .decorations(false)
        .always_on_top(true)
        .visible_on_all_workspaces(true)
        .skip_taskbar(true)
        .visible(false)
        .initialization_script("window.daywrightShell = 'menubar';")
        .on_navigation(move |url| {
            if url.scheme() == SHELL_SCHEME {
                answer_panel(&handle, url);
                return false;
            }
            let own = url.scheme() == "http"
                && url.host_str() == Some("127.0.0.1")
                && url.port() == Some(port);
            if !own {
                crate::open_in_browser(url);
            }
            own
        })
        .build()
        .map_err(|error| eprintln!("DayWright's menu bar panel could not be made: {error}"))
        .ok()?;
    let hidden = panel.clone();
    let hider = app.clone();
    panel.on_window_event(move |event| {
        if let WindowEvent::Focused(false) = event {
            let _ = hidden.hide();
            if let Some(shell) = hider.try_state::<Shell>() {
                *shell.hidden_at.lock().unwrap_or_else(|poisoned| poisoned.into_inner()) = Some(Instant::now());
            }
        }
    });
    Some(panel)
}

/// Do what the panel asked: open DayWright's window, or renew the title after a report.
fn answer_panel(app: &AppHandle, url: &Url) {
    match url.host_str() {
        Some("open") => {
            if let Some(panel) = app.get_webview_window(PANEL) {
                let _ = panel.hide();
            }
            show_main(app);
        }
        Some("refresh") => {
            if let Some(shell) = app.try_state::<Shell>() {
                if let Some(wake) = shell.wake.lock().unwrap_or_else(|poisoned| poisoned.into_inner()).as_ref() {
                    let _ = wake.send(());
                }
            }
        }
        _ => {}
    }
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
