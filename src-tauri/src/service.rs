//! Starts DayWright's bundled local service and stops it when the app quits.
//!
//! The service is a frozen copy of the Python backend. It gets a secret for this launch and its
//! storage locations in its environment, announces its port on standard output once it accepts
//! requests, and shuts down when its standard input closes. Closing that pipe is how the shell asks
//! it to stop, and the system closes it as well if the shell itself dies.

use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdout, Command, Stdio};
use std::sync::mpsc::{self, RecvTimeoutError};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

/// The prefix of the line that carries the port: `PORT_ANNOUNCEMENT` in backend/app/desktop.py.
const PORT_ANNOUNCEMENT: &str = "DAYWRIGHT_PORT=";
/// How long a launch may take, including macOS checking every bundled library on the first one.
const READY_TIMEOUT: Duration = Duration::from_secs(180);
/// How long the service may take to stop its model servers before it is killed.
const STOP_GRACE: Duration = Duration::from_secs(15);

/// Where the service runs from, and where it keeps its data and its log.
pub struct Launch {
    pub executable: PathBuf,
    pub client_directory: PathBuf,
    pub data_directory: PathBuf,
    pub log_file: PathBuf,
}

/// The running service, kept so the app can stop it when it quits.
pub struct Service {
    child: Mutex<Option<Child>>,
}

impl Service {
    /// Start the service with the launch `secret`. Returns it with its standard output, which
    /// [`wait_for_port`] reads, and the log that output is copied to. The log starts empty on every
    /// launch and also receives the service's error output.
    pub fn spawn(launch: &Launch, secret: &str) -> io::Result<(Service, ChildStdout, File)> {
        fs::create_dir_all(&launch.data_directory)?;
        if let Some(folder) = launch.log_file.parent() {
            fs::create_dir_all(folder)?;
        }
        let log = File::create(&launch.log_file)?;
        let mut child = Command::new(&launch.executable)
            .env("DAYWRIGHT_SESSION_TOKEN", secret)
            .env("DAYWRIGHT_CLIENT_DIR", &launch.client_directory)
            .env("DAYWRIGHT_DATABASE", launch.data_directory.join("daywright.sqlite3"))
            .env("DAYWRIGHT_RUNTIME_DIR", launch.data_directory.join("runtime"))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(log.try_clone()?)
            .spawn()?;
        let output = child
            .stdout
            .take()
            .ok_or_else(|| io::Error::other("the service's output was not captured"))?;
        Ok((Service { child: Mutex::new(Some(child)) }, output, log))
    }

    /// Ask the service to stop by closing its standard input, and kill it if it is still running
    /// after [`STOP_GRACE`].
    pub fn stop(&self) {
        let taken = self.child.lock().unwrap_or_else(|poisoned| poisoned.into_inner()).take();
        let Some(mut child) = taken else { return };
        drop(child.stdin.take());
        let deadline = Instant::now() + STOP_GRACE;
        while Instant::now() < deadline {
            match child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => thread::sleep(Duration::from_millis(100)),
                Err(_) => break,
            }
        }
        // Already exited or already reaped is the outcome wanted, so these results carry nothing.
        let _ = child.kill();
        let _ = child.wait();
    }
}

/// Read the service's `output` until it announces its port. Every other line, before and after,
/// is copied to `log`, which also keeps the pipe from filling while the service runs.
///
/// Returns the port, or why the service is not ready: it stopped first, or it did not announce a
/// port within [`READY_TIMEOUT`].
pub fn wait_for_port(output: ChildStdout, mut log: File) -> Result<u16, String> {
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let mut sender = Some(sender);
        for line in BufReader::new(output).lines().map_while(Result::ok) {
            match line.strip_prefix(PORT_ANNOUNCEMENT).map(str::parse::<u16>) {
                Some(Ok(port)) => {
                    if let Some(sender) = sender.take() {
                        let _ = sender.send(port);
                    }
                }
                _ => {
                    let _ = writeln!(log, "{line}");
                }
            }
        }
    });
    receiver.recv_timeout(READY_TIMEOUT).map_err(|error| match error {
        RecvTimeoutError::Timeout => {
            format!("it did not answer within {} seconds", READY_TIMEOUT.as_secs())
        }
        RecvTimeoutError::Disconnected => "it stopped before it was ready".to_string(),
    })
}

/// Add the shell's own account of a failed start to the end of `log_file`.
pub fn note_failure(log_file: &Path, reason: &str) {
    let written = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_file)
        .and_then(|mut log| writeln!(log, "DayWright's local service did not start: {reason}."));
    if let Err(error) = written {
        eprintln!("DayWright's local service did not start: {reason}; the log was not written: {error}");
    }
}

/// A new random secret for this launch, as 64 hexadecimal characters.
pub fn launch_secret() -> io::Result<String> {
    let mut bytes = [0u8; 32];
    File::open("/dev/urandom")?.read_exact(&mut bytes)?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}
