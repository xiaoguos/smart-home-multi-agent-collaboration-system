import { useEffect, useState } from "react";
import { getUserInfo } from "@/api/auth";
import { getClawSettings, type ClawSettings } from "@/utils/clawSettings";

export function useClawSettings(): ClawSettings & {
  hasOpen: boolean;
  hasZero: boolean;
  hasAny: boolean;
  userId: number | undefined;
} {
  const user = getUserInfo();
  const userId = user?.id;

  const [settings, setSettings] = useState<ClawSettings>(() =>
    userId
      ? getClawSettings(userId)
      : { openclawUrl: "", zeroclawUrl: "", openclawEnabled: false, zeroclawEnabled: false },
  );

  useEffect(() => {
    if (!userId) {
      setSettings({ openclawUrl: "", zeroclawUrl: "", openclawEnabled: false, zeroclawEnabled: false });
      return;
    }
    const sync = () => setSettings(getClawSettings(userId));
    sync();
    window.addEventListener("clawSettingsChanged", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("clawSettingsChanged", sync);
      window.removeEventListener("storage", sync);
    };
  }, [userId]);

  const hasOpen = Boolean(settings.openclawUrl) && settings.openclawEnabled;
  const hasZero = Boolean(settings.zeroclawUrl) && settings.zeroclawEnabled;

  return {
    ...settings,
    hasOpen,
    hasZero,
    hasAny: hasOpen || hasZero,
    userId,
  };
}
