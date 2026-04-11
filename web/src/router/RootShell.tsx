import React from "react";
import { Outlet } from "react-router-dom";
import NavigationGuard from "./NavigationGuard";

/**
 * 包裹全部路由，使 NavigationGuard 能使用 useLocation/useMatches
 */
const RootShell: React.FC = () => (
  <>
    <NavigationGuard />
    <Outlet />
  </>
);

export default RootShell;
