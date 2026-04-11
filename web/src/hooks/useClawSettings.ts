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
    userId ? getClawSettings(userId) : { openclawUrl: "", zeroclawUrl: "" },
  );

  useEffect(() => {
    if (!userId) {
      setSettings({ openclawUrl: "", zeroclawUrl: "" });
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

  const hasOpen = Boolean(settings.openclawUrl);
  const hasZero = Boolean(settings.zeroclawUrl);

  return {
    ...settings,
    hasOpen,
    hasZero,
    hasAny: hasOpen || hasZero,
    userId,
  };
}
