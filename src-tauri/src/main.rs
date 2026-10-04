//! DayWright's desktop shell. It opens one window on a start screen, starts the bundled local
//! service, and then shows the interface that service serves. Quitting the app stops the service.

mod service;

use std::error::Error;
use std::process::Command;
use std::sync::{Arc, OnceLock};
use std::thread;

use service::{Launch, Service};
use tauri::webview::NewWindowResponse;
use tauri::{
    App, LogicalPosition, Manager, RunEvent, TitleBarStyle, Url, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder,
};

/// The folder DayWright's data and logs live in, under Application Support and Logs.
const APP_FOLDER: &str = "DayWright";
/// Where the window opens a session: `SESSION_PATH` in backend/app/desktop.py.
const SESSION_PATH: &str = "/desktop/session";
/// The start screen, built with the interface, and the same screen saying the service did not start.
const START_PAGE: &str = "splash.html";
const FAILED_PAGE: &str = "tauri://localhost/splash.html#failed";
/// The window's opening and smallest size, in points, chosen by resizing the app to taste.
const WINDOW_WIDTH: f64 = 1412.0;
const WINDOW_HEIGHT: f64 = 938.0;

fn main() {
    let app = tauri::Builder::default()
        .setup(open)
        .build(tauri::generate_context!())
        .expect("DayWright's window could not be created");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(service) = handle.try_state::<Service>() {
                service.stop();
            }
        }
    });
}

/// Open the window on the start screen, start the service, and show the interface once it answers,
/// or the start screen's failure message when it does not.
fn open(app: &mut App) -> Result<(), Box<dyn Error>> {
    let service_port = Arc::new(OnceLock::new());
    let window = main_window(app, Arc::clone(&service_port))?;
    let launch = launch_paths(app)?;
    let secret = service::launch_secret()?;
    let (running, output, log) = match Service::spawn(&launch, &secret) {
        Ok(started) => started,
        Err(error) => {
            service::note_failure(&launch.log_file, &error.to_string());
            show(&window, FAILED_PAGE);
            return Ok(());
        }
    };
    app.manage(running);
    thread::spawn(move || match service::wait_for_port(output, log) {
        Ok(port) => {
            let _ = service_port.set(port);
            show(&window, &format!("http://127.0.0.1:{port}{SESSION_PATH}?token={secret}"));
        }
        Err(reason) => {
            service::note_failure(&launch.log_file, &reason);
            show(&window, FAILED_PAGE);
        }
    });
    Ok(())
}

/// The one window. DayWright's own 60 px title bar holds the window buttons, and any address other
/// than the start screen and the service opens in the default browser instead.
fn main_window(app: &App, service_port: Arc<OnceLock<u16>>) -> tauri::Result<WebviewWindow> {
    WebviewWindowBuilder::new(app, "main", WebviewUrl::App(START_PAGE.into()))
        .title("DayWright")
        .inner_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        .min_inner_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        .center()
        .title_bar_style(TitleBarStyle::Overlay)
        .hidden_title(true)
        // Centres the buttons in the title bar; bench.css leaves the same room at the bar's start.
        .traffic_light_position(LogicalPosition::new(20.0, 32.0))
        .initialization_script("window.daywrightShell = 'desktop';")
        .on_navigation(move |url| {
            let own = url.scheme() == "tauri"
                || (url.scheme() == "http"
                    && url.host_str() == Some("127.0.0.1")
                    && service_port.get().is_some_and(|port| url.port() == Some(*port)));
            if !own {
                open_in_browser(url);
            }
            own
        })
        .on_new_window(|url, _| {
            open_in_browser(&url);
            NewWindowResponse::Deny
        })
        .build()
}

/// Where the bundled service and interface are, and where the service keeps its data and log.
fn launch_paths(app: &App) -> tauri::Result<Launch> {
    let resources = app.path().resource_dir()?;
    Ok(Launch {
        executable: resources.join("service/daywright-service"),
        client_directory: resources.join("client"),
        data_directory: app.path().data_dir()?.join(APP_FOLDER),
        log_file: app.path().home_dir()?.join("Library/Logs").join(APP_FOLDER).join("service.log"),
    })
}

/// Point the window at `address`.
fn show(window: &WebviewWindow, address: &str) {
    let shown = address
        .parse::<Url>()
        .map_err(|error| error.to_string())
        .and_then(|url| window.navigate(url).map_err(|error| error.to_string()));
    if let Err(error) = shown {
        eprintln!("DayWright's window could not open its page: {error}");
    }
}

/// Hand a web address to the default browser. Addresses of any other kind are not opened.
fn open_in_browser(url: &Url) {
    if !matches!(url.scheme(), "http" | "https") {
        return;
    }
    if let Err(error) = Command::new("/usr/bin/open").arg(url.as_str()).spawn() {
        eprintln!("DayWright could not open a link in the browser: {error}");
    }
}
