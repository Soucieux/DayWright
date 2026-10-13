/**
 * Opening the demo, going back to the user's own data, and resetting the demo. The service stops once it has
 * answered and starts again in place in the workspace asked for (see backend/app/workspace.py), making the demo first
 * when it isn't made yet or is being reset; the window says which, waits for the new start to answer, then loads
 * again, so every screen reads the workspace now open.
 */

/** How often the window asks whether the service has started again, in milliseconds. */
export const SWITCH_POLL_MS = 1000;
/** How long the window waits for it, in milliseconds: making the demo takes up to a minute. */
export const SWITCH_WAIT_MS = 180000;

/**
 * What a switch says while under way, by what was asked and whether the demo is made already.
 * @param {"demo"|"own"} workspace - The workspace asked for.
 * @param {boolean} reset - Whether the demo is being made anew.
 * @param {boolean} made - Whether the demo is made already.
 * @returns {"demoResetting"|"demoMaking"|"demoOpening"|"demoReturning"} The message key.
 */
export function switchingKey(workspace, reset, made) {
  if (reset) return "demoResetting";
  if (workspace === "own") return "demoReturning";
  return made ? "demoOpening" : "demoMaking";
}

/**
 * Ask the service to switch workspace, then wait for a new start of it to answer in the workspace asked for.
 * @param {"demo"|"own"} workspace - The workspace to open.
 * @param {boolean} reset - Whether the demo is deleted first and made anew, ending today.
 * @param {object} io - How the service is reached, time passes and the window is told.
 * @param {() => Promise<{started: string, demoMode: boolean, demoMade: boolean, demoFailed?: boolean}>} io.health -
 *   Read the service's health.
 * @param {(choice: {workspace: string, reset: boolean}) => Promise<unknown>} io.ask - Ask for the switch.
 * @param {(ms: number) => Promise<void>} io.sleep - Wait.
 * @param {() => number} io.now - The time in milliseconds.
 * @param {(key: string) => void} io.phase - Told what to say: the switch's own words, then "demoStarting".
 * @returns {Promise<"done"|"demoFailed"|"timeout">} The new start answered in the workspace asked for; or, asked for
 *   the demo, in the user's own, as the demo couldn't be made; or none answered within SWITCH_WAIT_MS.
 */
export async function switchWorkspace(workspace, reset, { health, ask, sleep, now, phase }) {
  const before = await health();
  phase(switchingKey(workspace, reset, before.demoMade));
  await ask({ workspace, reset });
  const deadline = now() + SWITCH_WAIT_MS;
  while (now() < deadline) {
    await sleep(SWITCH_POLL_MS);
    let answer;
    try {
      answer = await health();
    } catch {
      continue; // The service is stopping, making the demo, or starting again; the next poll asks again.
    }
    if (answer.started === before.started) continue;
    if (answer.demoMode === (workspace === "demo")) {
      phase("demoStarting");
      return "done";
    }
    if (answer.demoFailed) return "demoFailed";
  }
  return "timeout";
}
