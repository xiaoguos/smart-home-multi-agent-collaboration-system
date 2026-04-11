import { useCallback } from "react";
import { useNavigate, type NavigateOptions, type To } from "react-router-dom";
import { isValidAppPath } from "./pathValidation";

const REDIRECT_404_PATH = "/__app_redirect_404";

function toPathname(to: To): string {
  if (typeof to === "string") {
    return to.split("?")[0].split("#")[0] || "/";
  }
  return to.pathname ?? "/";
}

/**
 * 带合法路径校验的 navigate：目标非法时改为进入统一 404，不发起非法跳转。
 * 数字（含 -1）交给原生 navigate，由 NavigationGuard 在落地后纠正非法页。
 */
export function useAppNavigate() {
  const navigate = useNavigate();

  return useCallback(
    (to: To | number, options?: NavigateOptions) => {
      if (typeof to === "number") {
        // 历史步进仅支持 navigate(delta)，与 NavigateOptions 无关
        navigate(to);
        return;
      }
      const pathname = toPathname(to);
      if (!isValidAppPath(pathname)) {
        navigate(REDIRECT_404_PATH, {
          replace: true,
          ...options,
          state: { ...options?.state, blockedTarget: pathname },
        });
        return;
      }
      navigate(to, options);
    },
    [navigate],
  );
}
