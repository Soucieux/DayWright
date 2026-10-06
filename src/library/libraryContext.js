import { createContext, useContext } from "react";

/**
 * What any screen showing a Library item needs to brief and open it, or to make learning tasks from it:
 * the items and the connected folders, whether the local service answers, a way to reload the Library
 * after a briefing is confirmed or a folder connected, and a way to reload the day, naming them, after
 * Learning tasks are made from a source.
 */
export const LibraryContext = createContext({ items: [], folders: [], backendConnected: false, refresh: async () => {},
  tasksMade: async () => {} });

/**
 * The Library's items and connected folders, the service's state and its reloads, wherever an item is shown.
 * @returns {{items: object[], folders: object[], backendConnected: boolean, refresh: () => Promise<void>,
 *   tasksMade: (tasks: object[]) => Promise<void>}} The Library's context.
 */
export function useLibrary() {
  return useContext(LibraryContext);
}
