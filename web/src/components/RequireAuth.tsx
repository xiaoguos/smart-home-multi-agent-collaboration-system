import React from "react";
import { getToken } from "@/api/auth";
import ForbiddenPage from "@/pages/errors/403";

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (!getToken()) {
    return <ForbiddenPage />;
  }
  return <>{children}</>;
};

export default RequireAuth;
