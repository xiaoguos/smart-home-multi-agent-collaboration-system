import { create } from "zustand";
import { clearUserInfo, getToken, getUserInfo, saveUserInfo } from "@/api/auth";
import type { UserInfo } from "@/api/auth";

export type AuthState = {
  token: string | null;
  user: UserInfo | null;
  /** 登录成功：写入 localStorage 并更新内存 */
  setAuth: (token: string, user: UserInfo) => void;
  /** 退出：清空 localStorage 与内存 */
  clearAuth: () => void;
  /** 从 localStorage 重新同步（跨标签页、或其它模块直接改了 storage 时） */
  hydrate: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: getToken(),
  user: getUserInfo(),

  setAuth: (token, user) => {
    saveUserInfo(token, user);
    set({ token, user });
  },

  clearAuth: () => {
    clearUserInfo();
    set({ token: null, user: null });
  },

  hydrate: () => {
    set({ token: getToken(), user: getUserInfo() });
  },
}));

function syncAuthFromStorage() {
  useAuthStore.getState().hydrate();
}

if (typeof window !== "undefined") {
  window.addEventListener("userInfoChanged", syncAuthFromStorage);
  window.addEventListener("storage", (event) => {
    if (event.key === "user_token" || event.key === "user_info") {
      syncAuthFromStorage();
    }
  });
}
