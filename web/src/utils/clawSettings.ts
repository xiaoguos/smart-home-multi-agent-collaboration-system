const STORAGE_PREFIX = "claw_settings_";

export type ClawSettings = {
  openclawUrl: string;
  zeroclawUrl: string;
};

function defaultSettings(): ClawSettings {
  return { openclawUrl: "", zeroclawUrl: "" };
}

export function getClawSettings(userId: number): ClawSettings {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${userId}`);
    if (!raw) return defaultSettings();
    const parsed = JSON.parse(raw) as Partial<ClawSettings>;
    return {
      openclawUrl: typeof parsed.openclawUrl === "string" ? parsed.openclawUrl.trim() : "",
      zeroclawUrl: typeof parsed.zeroclawUrl === "string" ? parsed.zeroclawUrl.trim() : "",
    };
  } catch {
    return defaultSettings();
  }
}

export function setClawSettings(userId: number, settings: ClawSettings): void {
  localStorage.setItem(`${STORAGE_PREFIX}${userId}`, JSON.stringify(settings));
  window.dispatchEvent(new Event("clawSettingsChanged"));
}

/** 空字符串视为未配置；非空须为 http(s) */
export function isValidEmbedUrl(url: string): boolean {
  const t = url.trim();
  if (!t) return true;
  try {
    const u = new URL(t);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}
