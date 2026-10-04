import { useEffect, useState } from "react";
import { getDay } from "../api";

/** A day with nothing loaded: no tasks, and no meals to keep free. */
const NOTHING_LOADED = { tasks: [], meals: [] };

/**
 * Load a day's tasks and its lunch and dinner, so a form can offer only the start times nothing else
 * takes. Without the local service there is nothing to load, and the service refuses a taken time
 * itself on save.
 * @param {string} date - The YYYY-MM-DD day.
 * @param {boolean} backendConnected - Whether the local service answered.
 * @returns {{tasks: object[], meals: object[]}} The day's tasks and meals, both empty until they load.
 */
export function useDayTasks(date, backendConnected) {
  const [loaded, setLoaded] = useState(NOTHING_LOADED);
  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    getDay(date).then((day) => live && setLoaded({ tasks: day.dayItems || [], meals: day.meals || [] }))
      .catch(() => live && setLoaded(NOTHING_LOADED));
    return () => { live = false; };
  }, [date, backendConnected]);
  return loaded;
}
