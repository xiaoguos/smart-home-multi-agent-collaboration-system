/**
 * 与 router/index 中声明的合法页面保持一致，用于跳转前校验。
 * 不在此列的路径视为非法，应走 404。
 */
export function isValidAppPath(pathname: string): boolean {
  const p = pathname.replace(/\/+$/, "") || "/";

  const exact = new Set([
    "/",
    "/welcome",
    "/auth/wechat/callback",
    "/chat",
    "/about",
    "/plugins",
    "/account-setting",
    "/xiaomi-binding",
    "/dida-binding",
    "/__app_redirect_404",
  ]);

  if (exact.has(p)) return true;

  if (p === "/setting" || p.startsWith("/setting/")) return true;

  if (p === "/models" || p === "/models/llm") return true;
  if (p === "/agents" || /^\/agents\/(connections|prompts)$/.test(p)) return true;
  if (p === "/devices" || /^\/devices\/(local|mihome)$/.test(p)) return true;

  if (p === "/claw" || /^\/claw\/(open|zero)$/.test(p)) return true;

  if (p === "/knowledge") return true;

  return false;
}
