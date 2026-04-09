import { httpClient } from '@/utils';

// 滴答清单OAuth请求
export interface DidaOAuthRequest {
  system_user_id: number;
  client_id: string;
  client_secret: string;
  authorization_code: string;
  redirect_uri: string;
}

// 滴答清单OAuth响应
export interface DidaOAuthResponse {
  status: string;
  message: string;
  data?: {
    username?: string;
    expires_at?: string;
  };
}

// 滴答清单绑定状态响应
export interface DidaBindingStatusResponse {
  is_bound: boolean;
  username?: string;
  bound_at?: string;
  token_expires_at?: string;
}

/**
 * 处理滴答清单OAuth回调
 * @param data OAuth请求数据
 * @returns OAuth响应
 */
export const handleDidaOAuthCallback = async (data: DidaOAuthRequest): Promise<DidaOAuthResponse> => {
  return httpClient.post<DidaOAuthResponse>('/api/v1/dida/oauth/callback', data);
};

/**
 * 刷新滴答清单访问令牌
 * @param system_user_id 系统用户ID
 * @returns OAuth响应
 */
export const refreshDidaToken = async (system_user_id: number): Promise<DidaOAuthResponse> => {
  return httpClient.post<DidaOAuthResponse>('/api/v1/dida/refresh', { system_user_id });
};

/**
 * 检查滴答清单绑定状态
 * @param system_user_id 系统用户ID
 * @returns 绑定状态
 */
export const checkDidaBindingStatus = async (system_user_id: number): Promise<DidaBindingStatusResponse> => {
  return httpClient.get<DidaBindingStatusResponse>('/api/v1/dida/binding/status', {
    params: { system_user_id }
  });
};

/**
 * 解绑滴答清单账号
 * @param system_user_id 系统用户ID
 * @returns 操作结果
 */
export const unbindDidaAccount = async (system_user_id: number): Promise<{ status: string; message: string }> => {
  return httpClient.delete('/api/v1/dida/unbind', {
    params: { system_user_id }
  });
};

/**
 * 获取滴答清单OAuth授权URL
 * @param client_id Client ID
 * @param redirect_uri 重定向URI
 * @returns 授权URL
 */
export const getDidaOAuthUrl = (client_id: string, redirect_uri?: string): string => {
  // 默认使用当前前端应用的URL作为回调地址
  const defaultRedirectUri = `${window.location.origin}/dida-binding`;
  const finalRedirectUri = redirect_uri || defaultRedirectUri;
  const scope = 'tasks:write tasks:read';
  return `https://dida365.com/oauth/authorize?client_id=${encodeURIComponent(client_id)}&redirect_uri=${encodeURIComponent(finalRedirectUri)}&scope=${encodeURIComponent(scope)}&response_type=code`;
};

