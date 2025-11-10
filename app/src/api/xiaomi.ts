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

/** 手动输入凭证请求 */
export interface ManualCredentialsRequest {
  system_user_id: number;
  xiaomi_username: string;
  ssecurity: string;
  userId: string;
  cUserId: string;
  serviceToken: string;
  server?: string;
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

/**
 * 手动输入凭证绑定
 */
export const manualBindCredentials = async (data: ManualCredentialsRequest): Promise<LoginStepResponse> => {
  return await httpClient.post<LoginStepResponse>('/api/v1/xiaomi/manual/bind', data);
};

/** 米家设备信息 */
export interface XiaomiDevice {
  home_id: string;
  home_name: string;
  name: string;
  did: string;
  model: string;
  token: string;
  mac: string;
  localip: string;
  parent_id: string;
  parent_model: string;
  show_mode: number;
  isOnline: boolean;
}

/** 米家家庭信息 */
export interface XiaomiHome {
  home_id: string;
  home_name: string;
  home_owner: string;
}

/** 米家设备列表响应 */
export interface XiaomiDevicesResponse {
  code: number;
  message: string;
  result: {
    server: string;
    total_homes: number;
    total_devices: number;
    homes: XiaomiHome[];
    devices: XiaomiDevice[];
  };
}

/**
 * 获取米家设备列表
 */
export const getXiaomiDevices = async (systemUserId: number, server: string = 'cn'): Promise<XiaomiDevicesResponse> => {
  return await httpClient.get<XiaomiDevicesResponse>(`/api/v1/xiaomi/devices?system_user_id=${systemUserId}&server=${server}`);
};

/**
 * 解绑小米账号
 * @param system_user_id 系统用户ID
 * @returns 操作结果
 */
export const unbindXiaomiAccount = async (system_user_id: number): Promise<{ status: string; message: string }> => {
  return httpClient.delete('/api/v1/xiaomi/unbind', {
    params: { system_user_id }
  });
};

