/**
 * 小米账号认证 API
 */

import { httpClient } from '../utils/request';

/** 小米登录请求 */
export interface XiaomiLoginRequest {
  system_user_id: number;
  username: string;
  password: string;
  server?: string;
}

/** 验证码提交请求 */
export interface CaptchaSubmitRequest {
  session_id: string;
  captcha_code: string;
}

/** 双因素认证请求 */
export interface TwoFactorAuthRequest {
  session_id: string;
  ticket: string;
}

/** 登录步骤响应 */
export interface LoginStepResponse {
  session_id: string;
  status: 'success' | 'need_captcha' | 'need_2fa' | 'error';
  message: string;
  data?: {
    captcha_url?: string;
    verify_url?: string;
    verify_method?: string;
  };
}

/** 绑定状态响应 */
export interface BindingStatusResponse {
  is_bound: boolean;
  username?: string;
  bound_at?: string;
}

/** 绑定状态类型别名 */
export type BindingStatus = BindingStatusResponse;

/**
 * 开始小米账号登录流程
 */
export const startXiaomiLogin = async (data: XiaomiLoginRequest): Promise<LoginStepResponse> => {
  return await httpClient.post<LoginStepResponse>('/api/v1/xiaomi/login/start', data);
};

/**
 * 获取验证码图片URL
 */
export const getCaptchaUrl = (sessionId: string): string => {
  const baseUrl = import.meta.env.VITE_BACKEND_URL;
  return `${baseUrl}/api/v1/xiaomi/captcha/${sessionId}`;
};

/**
 * 提交验证码
 */
export const submitCaptcha = async (data: CaptchaSubmitRequest): Promise<LoginStepResponse> => {
  return await httpClient.post<LoginStepResponse>('/api/v1/xiaomi/captcha/submit', data);
};

/**
 * 重新发送双因素认证验证码
 */
export const resend2FACode = async (sessionId: string): Promise<LoginStepResponse> => {
  return await httpClient.post<LoginStepResponse>('/api/v1/xiaomi/2fa/resend', { session_id: sessionId });
};

/**
 * 验证双因素认证
 */
export const verify2FA = async (data: TwoFactorAuthRequest): Promise<LoginStepResponse> => {
  return await httpClient.post<LoginStepResponse>('/api/v1/xiaomi/2fa/verify', data);
};

/**
 * 检查绑定状态
 */
export const checkBindingStatus = async (systemUserId: number): Promise<BindingStatusResponse> => {
  return await httpClient.get<BindingStatusResponse>(`/api/v1/xiaomi/binding/status?system_user_id=${systemUserId}`);
};

/**
 * 检查小米账号绑定状态（别名）
 */
export const checkXiaomiBindingStatus = checkBindingStatus;

