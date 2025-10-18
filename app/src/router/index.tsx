import { createBrowserRouter, redirect } from "react-router-dom";
import App from "@/App";
import Setting from "@/pages/Setting";
import Chat from "@/pages/Chat";
import About from "@/pages/About";
import Welcome from "@/pages/Welcome";

export const routes = createBrowserRouter([
  {
    path: "/",
    element: <Welcome />,
  },
  {
    path: "/home",
    element: <App />,
    children: [
      {
        index: true,
        loader: () => redirect("/chat"),
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
]);
