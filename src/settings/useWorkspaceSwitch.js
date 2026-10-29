import { createContext, useState } from "react";
import { api } from "../api";
import { switchWorkspace, switchingKey } from "./workspaceSwitch";

/** The window's one switch of workspace (see useWorkspaceSwitch), for the controls that start it. */
export const WorkspaceSwitchContext = createContext({ active: false, switching: null, failed: null, start: () => {}, close: () => {} });

/** What a switch that didn't end in the workspace asked for says, and whether Continue loads the window again. */
const OUTCOMES = {
  demoFailed: { key: "demoMakeFailed", reload: true },
  timeout: { key: "demoSwitchFailed", reload: false },
};

/**
 * The window's one switch of workspace (see workspaceSwitch), kept by the app so nothing that closes, as Settings
 * does, ends it: while it is under way, or once it failed, `active` holds and the app shows SwitchOverlay. Done, the
 * window loads again in the workspace asked for.
 * @returns {{active: boolean, switching: string|null, failed: {key?: string, text?: string, reload: boolean}|null,
 *   start: (workspace: "demo"|"own", reset?: boolean) => Promise<void>, close: () => void}} Whether it shows; the
 *   message key while under way; why it failed, as a message key or the service's words; the switch; and Close.
 */
export function useWorkspaceSwitch() {
  const [switching, setSwitching] = useState(null);
  const [failed, setFailed] = useState(null);

  /**
   * Switch to `workspace`, the demo made afresh when `reset`; once done the window loads again, else the failure
   * stays on show. A second start while one is under way does nothing.
   */
  async function start(workspace, reset = false) {
    if (switching) return;
    setFailed(null);
    setSwitching(switchingKey(workspace, reset, true));
    try {
      const outcome = await switchWorkspace(workspace, reset, {
        health: () => api("/api/health"),
        ask: (choice) => api("/api/workspace", { method: "POST", body: JSON.stringify(choice) }),
        sleep: (ms) => new Promise((resolve) => { window.setTimeout(resolve, ms); }),
        now: () => Date.now(),
        phase: setSwitching,
      });
      if (outcome === "done") {
        window.location.reload();
        return;
      }
      setFailed(OUTCOMES[outcome]);
    } catch (caught) {
      // Refused before anything switched: the workspace open stays as it was.
      setFailed({ text: caught.message, reload: false });
    }
    setSwitching(null);
  }

  /** Close a failed switch's message: the window loads again when the service started again in another workspace. */
  function close() {
    if (failed?.reload) {
      window.location.reload();
      return;
    }
    setFailed(null);
  }

  return { active: Boolean(switching || failed), switching, failed, start, close };
}
