import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useClawSettings } from "@/hooks/useClawSettings";

/** /claw 无子路径时跳到已配置的首个子页，否则回对话 */
const ClawIndexRedirect: React.FC = () => {
  const navigate = useNavigate();
  const { hasOpen, hasZero } = useClawSettings();

  useEffect(() => {
    if (hasOpen) navigate("/claw/open", { replace: true });
    else if (hasZero) navigate("/claw/zero", { replace: true });
    else navigate("/chat", { replace: true });
  }, [hasOpen, hasZero, navigate]);

  return null;
};

export default ClawIndexRedirect;
