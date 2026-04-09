import { createBrowserRouter, redirect } from "react-router-dom";
import { RootLayout } from "@/layout";
import Setting from "@/pages/Setting";
import Chat from "@/pages/Chat";
import About from "@/pages/About";
import Welcome from "@/pages/Welcome";
import WechatCallback from "@/pages/WechatCallback";
import XiaomiBinding from "@/pages/XiaomiBinding";
import DidaBinding from "@/pages/DidaBinding";
import AccountSetting from "@/pages/AccountSetting";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        loader: () => redirect("/welcome"),
      },
      {
        path: "welcome",
        element: <Welcome />,
      },
      {
        path: "chat",
        element: <Chat />,
      },
      {
        path: "about",
        element: <About />,
      },
      {
        path: "setting",
        element: <Setting />,
      },
    ],
  },
  {
    path: "/account-setting",
    element: <AccountSetting />,
  },
  {
    path: "/xiaomi-binding",
    element: <XiaomiBinding />,
  },
  {
    path: "/dida-binding",
    element: <DidaBinding />,
  },
  {
    path: "/auth/wechat/callback",
    element: <WechatCallback />,
  },
]);

export default router;
