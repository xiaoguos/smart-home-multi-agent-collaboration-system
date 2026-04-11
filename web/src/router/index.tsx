import { createBrowserRouter, redirect, Outlet } from "react-router-dom";
import { RootLayout } from "@/layout";
import RequireAuth from "@/components/RequireAuth";
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
import NotFoundPage from "@/pages/errors/404";
import RootShell from "@/router/RootShell";
import { NOT_FOUND_HANDLE } from "@/router/handles";

const notFoundRoute = {
  element: <NotFoundPage />,
  handle: NOT_FOUND_HANDLE,
};

export const router = createBrowserRouter([
  {
    element: <RootShell />,
    children: [
      {
        path: "/welcome",
        element: <Welcome />,
      },
      {
        path: "/auth/wechat/callback",
        element: <WechatCallback />,
      },
      {
        path: "/",
        element: <Outlet />,
        children: [
          {
            index: true,
            loader: () => redirect("/welcome"),
          },
          {
            element: (
              <RequireAuth>
                <RootLayout />
              </RequireAuth>
            ),
            children: [
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
                  {
                    path: "*",
                    ...notFoundRoute,
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
                  {
                    path: "*",
                    ...notFoundRoute,
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
                  {
                    path: "*",
                    ...notFoundRoute,
                  },
                ],
              },
              {
                path: "*",
                ...notFoundRoute,
              },
            ],
          },
        ],
      },
      {
        path: "/account-setting",
        element: (
          <RequireAuth>
            <AccountSetting />
          </RequireAuth>
        ),
      },
      {
        path: "/xiaomi-binding",
        element: (
          <RequireAuth>
            <XiaomiBinding />
          </RequireAuth>
        ),
      },
      {
        path: "/dida-binding",
        element: (
          <RequireAuth>
            <DidaBinding />
          </RequireAuth>
        ),
      },
      {
        path: "/__app_redirect_404",
        ...notFoundRoute,
      },
      {
        path: "*",
        ...notFoundRoute,
      },
    ],
  },
]);

export default router;
