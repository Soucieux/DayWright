/**
 * A connected folder's readable files as a tree of tick boxes: each folder in it, in path order, with
 * its own files under it by name. The folder itself comes first, as "".
 * @param {{path: string, ticked: boolean, reason: string|null}[]} files - The files, as the folder's preview lists them.
 * @returns {{folder: string, files: {path: string, name: string, ticked: boolean, reason: string|null}[]}[]} The tree.
 */
export function folderTree(files) {
  const folders = new Map();
  for (const file of files) {
    const cut = file.path.lastIndexOf("/");
    const folder = cut < 0 ? "" : file.path.slice(0, cut);
    if (!folders.has(folder)) folders.set(folder, []);
    folders.get(folder).push({ ...file, name: file.path.slice(cut + 1) });
  }
  return [...folders.keys()].sort((one, other) => one.localeCompare(other))
    .map((folder) => ({ folder, files: folders.get(folder).sort((one, other) => one.name.localeCompare(other.name)) }));
}
