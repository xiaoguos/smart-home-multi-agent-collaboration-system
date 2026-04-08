// 微信登录配置
export const WECHAT_CONFIG = {
  // 微信开放平台应用ID（请替换为您的真实AppID）
  APP_ID: 'wx8917cf17d78c56e1',
  
  // 微信登录回调地址
  REDIRECT_URI: `${window.location.origin}/auth/wechat/callback`,
  
  // 授权作用域
  SCOPE: 'snsapi_login',
  
  // 二维码有效期（毫秒）
  QR_CODE_EXPIRE_TIME: 5 * 60 * 1000, // 5分钟
  
  // 轮询间隔（毫秒）
  POLLING_INTERVAL: 2000, // 2秒
};

// 生成微信登录URL
export const generateWechatLoginUrl = (sceneId: string): string => {
  const { APP_ID, REDIRECT_URI, SCOPE } = WECHAT_CONFIG;
  
  const state = encodeURIComponent(JSON.stringify({ 
    sceneId, 
    timestamp: Date.now() 
  }));
  
  return `https://open.weixin.qq.com/connect/qrconnect?appid=${APP_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=${SCOPE}&state=${state}#wechat_redirect`;
};

// 生成场景ID
export const generateSceneId = (): string => {
  return `login_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};
