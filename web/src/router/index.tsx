import { createBrowserRouter, redirect } from "react-router-dom";
import { RootLayout } from "@/layout";
import {
  ConfigLayout,
  ModelSettings,
  AgentConnections,
  AgentPrompts,
  LocalDeviceSettings,
  MihomeDeviceSettings,
} from "@/pages/settings";
import Chat from "@/pages/chat";
import About from "@/pages/about";
import Welcome from "@/pages/Welcome";
import WechatCallback from "@/pages/auth/wechat-callback";
import XiaomiBinding from "@/pages/bindings/xiaomi";
import DidaBinding from "@/pages/bindings/dida";
import AccountSetting from "@/pages/account-setting";

export const router = createBrowserRouter([
  {
    path: "/welcome",
    element: <Welcome />,
  },
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        loader: () => redirect("/welcome"),
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
        loader: () => redirect("/models/llm"),
      },
      {
        path: "setting/*",
        loader: () => redirect("/models/llm"),
      },
      {
        path: "models",
        element: <ConfigLayout />,
        children: [
          {
            index: true,
            loader: () => redirect("/models/llm"),
          },
          {
            path: "llm",
            element: <ModelSettings />,
          },
        ],
      },
      {
        path: "agents",
        element: <ConfigLayout />,
        children: [
          {
            index: true,
            loader: () => redirect("/agents/connections"),
          },
          {
            path: "connections",
            element: <AgentConnections />,
          },
          {
            path: "prompts",
            element: <AgentPrompts />,
          },
        ],
      },
      {
        path: "devices",
        element: <ConfigLayout />,
        children: [
          {
            index: true,
            loader: () => redirect("/devices/local"),
          },
          {
            path: "local",
            element: <LocalDeviceSettings />,
          },
          {
            path: "mihome",
            element: <MihomeDeviceSettings />,
          },
        ],
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
