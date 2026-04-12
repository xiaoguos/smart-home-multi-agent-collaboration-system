import React from "react";
import { getUserInfo } from "../../../api/auth";
import BindingSection from "../../account-setting/BindingSection";
import "../styles/setting.sass";

const PluginMenuSettings: React.FC = () => {
  const userInfo = getUserInfo();

  return (
    <>
      <div className="setting-section">
        <h2 className="setting-page-title">插件菜单</h2>
        <p className="setting-page-desc">插件系统生成一级菜单，统一管理账号绑定与嵌入配置。</p>
      </div>
      <BindingSection userInfo={userInfo} />
    </>
  );
};

export default PluginMenuSettings;
