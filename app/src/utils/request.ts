import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * HTTP 请求配置接口
 */
export interface HttpClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/**
 * 请求拦截器配置
 */
export interface RequestInterceptor {
  onFulfilled?: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>;
  onRejected?: (error: any) => any;
}

/**
 * 响应拦截器配置
 */
export interface ResponseInterceptor {
  onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>;
  onRejected?: (error: AxiosError) => any;
}

/**
 * HTTP 客户端类 - Axios 二次封装
 */
export class HttpClient {
  private instance: AxiosInstance;
  private config: HttpClientConfig;

  constructor(config: HttpClientConfig = {}) {
    this.config = {
      baseURL: import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:2100',
      timeout: 120000, // 120 秒超时
      headers: {
        'Content-Type': 'application/json',
      },
      ...config,
    };

    this.instance = axios.create(this.config);
    this.setupDefaultInterceptors();
  }

  /**
   * 设置默认拦截器
   */
  private setupDefaultInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        console.log('📤 发送请求:', config.method?.toUpperCase(), config.url);
        return config;
      },
      (error) => {
        console.error('❌ 请求错误:', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response) => {
        console.log('📥 收到响应:', response.status, response.config.url);
        return response;
      },
      (error) => {
        console.error('❌ 响应错误:', error.message);
        return Promise.reject(error);
      }
    );
  }

  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(interceptor: RequestInterceptor): number {
    return this.instance.interceptors.request.use(
      interceptor.onFulfilled,
      interceptor.onRejected
    );
  }

  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): number {
    return this.instance.interceptors.response.use(
      interceptor.onFulfilled,
      interceptor.onRejected
    );
  }

  /**
   * 移除请求拦截器
   */
  removeRequestInterceptor(id: number): void {
    this.instance.interceptors.request.eject(id);
  }

  /**
   * 移除响应拦截器
   */
  removeResponseInterceptor(id: number): void {
    this.instance.interceptors.response.eject(id);
  }

  /**
   * GET 请求
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.get<T>(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * POST 请求
   */
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.post<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * PUT 请求
   */
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.put<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.delete<T>(url, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * PATCH 请求
   */
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.patch<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * 通用请求方法
   */
  async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.request<T>(config);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * 错误处理
   */
  private handleError(error: any): Error {
    // 处理请求取消错误
    if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
      return error; // 直接返回原始的 AbortError，保持 name 属性
    }
    
    if (error.code === 'ECONNREFUSED') {
      return new Error('无法连接到服务器，请确保服务已启动');
    } else if (error.code === 'ETIMEDOUT') {
      return new Error('请求超时');
    } else if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      return new Error(detail.message || detail || '请求失败');
    } else if (error.response?.data?.error) {
      return new Error(`服务器返回错误: ${error.response.data.error.message || '未知错误'}`);
    } else {
      return new Error(error.message || '请求失败');
    }
  }

  /**
   * 获取原始 Axios 实例
   */
  getInstance(): AxiosInstance {
    return this.instance;
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<HttpClientConfig>): void {
    this.config = { ...this.config, ...config };
    this.instance.defaults.baseURL = this.config.baseURL;
    this.instance.defaults.timeout = this.config.timeout;
    if (this.config.headers) {
      this.instance.defaults.headers = { ...this.instance.defaults.headers, ...this.config.headers };
    }
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string): void {
    this.instance.defaults.headers.Authorization = `Bearer ${token}`;
  }

  /**
   * 移除认证令牌
   */
  removeAuthToken(): void {
    delete this.instance.defaults.headers.Authorization;
  }
}

// 创建默认的 HTTP 客户端实例
export const httpClient = new HttpClient();

// 为了向后兼容，导出原来的 backendClient
export const backendClient = httpClient.getInstance();

