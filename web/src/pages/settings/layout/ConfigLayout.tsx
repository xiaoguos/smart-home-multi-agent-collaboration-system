import React from "react";
import { Outlet } from "react-router-dom";
import "../styles/setting.sass";

const ConfigLayout: React.FC = () => (
  <div className="setting-container">
    <Outlet />
  </div>
);

export default ConfigLayout;
