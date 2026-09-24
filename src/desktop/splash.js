import "@fontsource/figtree/400.css";
import "@fontsource/bricolage-grotesque/700.css";
import "../../design/tokens/tokens.css";
import "../bench.css";
import "./splash.css";
import { translate } from "../i18n.jsx";

/** The address fragment the desktop app adds when its local service didn't start. */
const FAILED = "#failed";
/** Where the desktop app writes the service's log (see src-tauri/src/main.rs). */
const LOG_FILE = "~/Library/Logs/DayWright/service.log";

/** Fill every `data-message` element with its text in the element's own language. */
function fillMessages() {
  for (const element of document.querySelectorAll("[data-message]")) {
    const language = element.lang.startsWith("zh") ? "zh" : "en";
    element.textContent = translate(language, element.dataset.message, { log: LOG_FILE });
  }
}

/** Show the starting line, or the failure message once the desktop app reports one. */
function showState() {
  const failed = location.hash === FAILED;
  document.querySelector(".dw-splash-starting").hidden = failed;
  document.querySelector(".dw-splash-failed").hidden = !failed;
}

fillMessages();
showState();
window.addEventListener("hashchange", showState);
