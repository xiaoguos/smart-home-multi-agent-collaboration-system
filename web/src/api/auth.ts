/**
 * 用户认证 API
 */

import { httpClient } from '@/utils';

/** 用户注册请求 */
export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
  phone?: string;
  nickname?: string;
}

/** 用户登录请求 */
export interface LoginRequest {
  username: string;
  password: string;
}

/** 用户信息 */
export interface UserInfo {
  id: number;
  username: string;
  nickname?: string;
  email?: string;
  phone?: string;
  avatar?: string;
  created_at: string;
}

/** 用户资料更新请求 */
export interface UpdateUserProfileRequest {
  user_id: number;
  nickname?: string;
  email?: string;
  phone?: string;
  avatar?: string;
}

/** 用户资料更新响应 */
export interface UpdateUserProfileResponse {
  success: boolean;
  message: string;
  user: UserInfo;
}

/** 登录响应 */
export interface LoginResponse {
  success: boolean;
  message: string;
  token?: string;
  user?: UserInfo;
  xiaomi_bound?: boolean;
}

/**
 * 用户注册
 */
export const register = async (data: RegisterRequest): Promise<LoginResponse> => {
  return await httpClient.post<LoginResponse>('/api/v1/auth/register', data);
};

/**
 * 用户登录
 */
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  return await httpClient.post<LoginResponse>('/api/v1/auth/login', data);
};

/**
 * 用户登出
 */
export const logout = async (): Promise<{ success: boolean; message: string }> => {
  return await httpClient.post('/api/v1/auth/logout');
};

/**
 * 检查用户名是否可用
 */
export const checkUsername = async (username: string): Promise<{ available: boolean; message: string }> => {
  return await httpClient.get(`/api/v1/auth/check-username/${username}`);
};

/**
 * 更新用户资料
 */
export const updateUserProfile = async (
  data: UpdateUserProfileRequest,
): Promise<UpdateUserProfileResponse> => {
  return await httpClient.put<UpdateUserProfileResponse>("/api/v1/auth/profile", data);
};

/**
 * 保存用户信息到本地存储
 */
export const saveUserInfo = (token: string, user: UserInfo) => {
  localStorage.setItem('user_token', token);
  localStorage.setItem('user_info', JSON.stringify(user));
  // 触发自定义事件通知其他组件
  window.dispatchEvent(new Event('userInfoChanged'));
};

/**
 * 获取用户信息
 */
export const getUserInfo = (): UserInfo | null => {
  const userStr = localStorage.getItem('user_info');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
  return null;
};

/**
 * 获取 token
 */
export const getToken = (): string | null => {
  return localStorage.getItem('user_token');
};

/**
 * 清除用户信息
 */
export const clearUserInfo = () => {
  localStorage.removeItem('user_token');
  localStorage.removeItem('user_info');
  // 触发自定义事件通知其他组件
  window.dispatchEvent(new Event('userInfoChanged'));
};

/**
 * 检查是否已登录
 */
export const isLoggedIn = (): boolean => {
  return !!getToken();
};

