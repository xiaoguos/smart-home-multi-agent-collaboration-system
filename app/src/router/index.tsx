import { createBrowserRouter } from "react-router-dom";
import App from "@/App";
import Setting from "@/pages/Setting";
import Chat from "@/pages/Chat";
import About from "@/pages/About";

export const routes = createBrowserRouter([
  {
    path: "/",
    element: <App />,
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
        element: <Setting />,
      },
      {
        path: "",
        element: <Chat />, // 默认显示聊天页面
      },
    ],
  },
]);
