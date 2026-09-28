// The entity's name, remembered in this browser tab only, so the assessment page can show it
// before the report arrives. It never goes into the URL, where browser history, server logs and
// referrers would keep it.

const key = (reportId: string) => `argus:entity:${reportId}`;

function tabStorage(): Storage | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined; // storage blocked by the browser
  }
}

export function rememberEntityName(
  reportId: string,
  name: string,
  storage: Storage | undefined = tabStorage(),
): void {
  try {
    storage?.setItem(key(reportId), name);
  } catch {
    // Storage full or blocked: the page shows the name once the report arrives.
  }
}

export function recalledEntityName(
  reportId: string,
  storage: Storage | undefined = tabStorage(),
): string | undefined {
  try {
    return storage?.getItem(key(reportId)) ?? undefined;
  } catch {
    return undefined;
  }
}
