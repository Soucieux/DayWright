import { useEffect, useState } from "react";
import { getDay } from "../api";

/**
 * Load a day's tasks, so a form can offer only the start times nothing else takes. Without the
 * local service there is nothing to load, and the service refuses a taken time itself on save.
 * @param {string} date - The YYYY-MM-DD day.
 * @param {boolean} backendConnected - Whether the local service answered.
 * @returns {object[]} The day's tasks, empty until they load.
 */
export function useDayTasks(date, backendConnected) {
  const [tasks, setTasks] = useState([]);
  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    getDay(date).then((day) => live && setTasks(day.dayItems || [])).catch(() => live && setTasks([]));
    return () => { live = false; };
  }, [date, backendConnected]);
  return tasks;
}
