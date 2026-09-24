export const LOCAL_USER_DATA_KEYS = [
  "llm_settings_cache",
  "akh_maas_assessments_v2",
  "akh_jd_records_v1",
  "akh_last_page_v1",
  "akh_local_owner_v1",
] as const;

const LOCAL_OWNER_KEY = "akh_local_owner_v1";

export function clearLocalUserData(): void {
  if (typeof localStorage === "undefined") return;
  for (const key of LOCAL_USER_DATA_KEYS) {
    try {
      localStorage.removeItem(key);
    } catch {
      // Server deletion remains complete when browser storage is unavailable.
    }
  }
}

export function bindLocalUserDataOwner(userId: string): void {
  if (typeof localStorage === "undefined") return;
  try {
    const currentOwner = localStorage.getItem(LOCAL_OWNER_KEY);
    if (currentOwner && currentOwner !== userId) {
      clearLocalUserData();
    }
    localStorage.setItem(LOCAL_OWNER_KEY, userId);
  } catch {
    // The app remains usable when browser storage is unavailable.
  }
}
