import { createBrowserRouter } from "react-router";
import App from "@/App";
import Setting from "@/pages/Setting";
import Chat from "@/pages/Chat";
import About from "@/pages/About";

export const routes = createBrowserRouter([
  {
    path: "/",
    element: <App />,
  },
  {
    path: "/setting",
    element: <Setting />,
  },
]);
