import type { FC } from "react";
import { useEffect } from "react";
import { useLocation, useMatches, useNavigate } from "react-router-dom";
import { isValidAppPath } from "./pathValidation";
import { NOT_FOUND_HANDLE } from "./handles";

const REDIRECT_404_PATH = "/__app_redirect_404";

/**
 * 非 404 视图下，若地址栏为非法路径则统一替换到受控 404；
 * 404 视图内不拦截（由 useAppNavigate 负责跳转前校验）。
 */
const NavigationGuard: FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const matches = useMatches();

  const is404View = matches.some((m) => (m.handle as typeof NOT_FOUND_HANDLE | undefined)?.notFound === true);

  useEffect(() => {
    if (is404View) return;
    if (!isValidAppPath(location.pathname)) {
      navigate(REDIRECT_404_PATH, { replace: true, state: { from: location.pathname } });
    }
  }, [location.pathname, is404View, navigate]);

  return null;
};

export default NavigationGuard;
