// Module-level (survives across component mount/unmount, not across page
// reloads) stale-while-revalidate cache for already-visited competitions/
// analyses. Switching back to a tab you've already opened this session
// renders instantly from here while a background refetch keeps it fresh
// for *next* time — never a second skeleton for data we already have.
const cache = new Map<string, unknown>();

export function getCached<T>(key: string): T | undefined {
  return cache.get(key) as T | undefined;
}

export function setCached<T>(key: string, value: T): void {
  cache.set(key, value);
}
