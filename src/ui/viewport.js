import { useEffect, useState } from "react";

/**
 * At this window width and below, the app is laid out as on a phone, as bench.css's 640px breakpoint has it: Ava
 * is a sheet from the bottom and can't be moved, and an area's cards make one column.
 */
export const PHONE_WIDTH = 640;

/**
 * The window's size, followed as it changes.
 * @returns {{width: number, height: number}} Its inner width and height, in CSS pixels.
 */
export function useViewport() {
  const [viewport, setViewport] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    /** Keep the window's width and height. */
    const measure = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);
  return viewport;
}
