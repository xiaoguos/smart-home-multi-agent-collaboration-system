import { createBrowserRouter, redirect, Outlet } from "react-router-dom";
import { RootLayout } from "@/layout";
import RequireAuth from "@/components/RequireAuth";
import {
  ConfigLayout,
  ModelSettings,
  AgentConnections,
  LocalDeviceSettings,
  MihomeDeviceSettings,
  PluginMenuSettings,
  KnowledgeSettings,
} from "@/pages/settings";
import Chat from "@/pages/chat";
import About from "@/pages/about";
import Welcome from "@/pages/Welcome";
import WechatCallback from "@/pages/auth/wechat-callback";
import XiaomiBinding from "@/pages/bindings/xiaomi";
import DidaBinding from "@/pages/bindings/dida";
import AccountSetting from "@/pages/account-setting";
import ClawEmbed from "@/pages/claw/ClawEmbed";
import ClawIndexRedirect from "@/pages/claw/ClawIndexRedirect";
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
                loader: () => redirect("/models"),
              },
              {
                path: "setting/*",
                loader: () => redirect("/models"),
              },
              {
                path: "models",
                element: <ConfigLayout />,
                children: [
                  {
                    index: true,
                    element: <ModelSettings />,
                  },
                  {
                    path: "llm",
                    loader: () => redirect("/models"),
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
                    element: <AgentConnections />,
                  },
                  {
                    path: "connections",
                    loader: () => redirect("/agents"),
                  },
                  {
                    path: "prompts",
                    loader: () => redirect("/agents"),
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
                path: "plugins",
                element: <ConfigLayout />,
                children: [
                  {
                    index: true,
                    element: <PluginMenuSettings />,
                  },
                  {
                    path: "*",
                    ...notFoundRoute,
                  },
                ],
              },
              {
                path: "knowledge",
                element: <ConfigLayout />,
                children: [
                  {
                    index: true,
                    element: <KnowledgeSettings />,
                  },
                  {
                    path: "*",
                    ...notFoundRoute,
                  },
                ],
              },
              {
                path: "claw",
                children: [
                  {
                    index: true,
                    element: <ClawIndexRedirect />,
                  },
                  {
                    path: "open",
                    element: <ClawEmbed variant="open" />,
                  },
                  {
                    path: "zero",
                    element: <ClawEmbed variant="zero" />,
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
