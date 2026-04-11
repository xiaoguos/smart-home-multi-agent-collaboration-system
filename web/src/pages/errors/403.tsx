import React from "react";
import { useNavigate } from "react-router-dom";
import "./errors.sass";
import { Button, Result } from "antd";

const ForbiddenPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="error-page error-page--full">
      <Result
        status="403"
        title="403"
        subTitle="需要登录后才能访问该页面，请先登录。"
        extra={
          <Button type="primary" onClick={() => navigate("/welcome", { replace: true })}>
            去登录
          </Button>
        }
      />
    </div>
  );
};

export default ForbiddenPage;
