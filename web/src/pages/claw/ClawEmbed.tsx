import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useClawSettings } from "@/hooks/useClawSettings";
import "./claw.sass";

export type ClawEmbedVariant = "open" | "zero";

export interface ClawEmbedProps {
  variant: ClawEmbedVariant;
}

const ClawEmbed: React.FC<ClawEmbedProps> = ({ variant }) => {
  const navigate = useNavigate();
  const { openclawUrl, zeroclawUrl, hasOpen, hasZero } = useClawSettings();

  const ok = variant === "open" ? hasOpen : hasZero;
  const src = variant === "open" ? openclawUrl : zeroclawUrl;

  useEffect(() => {
    if (!ok) {
      navigate("/chat", { replace: true });
    }
  }, [ok, navigate]);

  if (!ok) return null;

  const title = variant === "open" ? "OpenClaw" : "ZeroClaw";

  return (
    <div className="claw-embed">
      <iframe className="claw-embed__frame" title={title} src={src} />
    </div>
  );
};

export default ClawEmbed;
