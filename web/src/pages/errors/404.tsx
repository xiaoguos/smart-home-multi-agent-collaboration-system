import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./errors.sass";
import { Button, Result, Space } from "antd";
import { useAppNavigate } from "@/router/useAppNavigate";

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  const appNavigate = useAppNavigate();
  const [canGoBack, setCanGoBack] = useState(false);

  useEffect(() => {
    setCanGoBack(typeof window !== "undefined" && window.history.length > 1);
  }, []);

  return (
    <div className="error-page error-page--full">
      <Result
        status="404"
        title="404"
        subTitle="访问的页面不存在。"
        extra={
          <Space wrap>
            {canGoBack && (
              <Button onClick={() => navigate(-1)}>返回上一页</Button>
            )}
            <Button type="primary" onClick={() => appNavigate("/", { replace: true })}>
              返回首页
            </Button>
          </Space>
        }
      />
    </div>
  );
};

export default NotFoundPage;
