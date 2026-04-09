import { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from "axios";
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
  onFulfilled?: (
    config: InternalAxiosRequestConfig,
  ) => InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>;
  onRejected?: (error: any) => any;
}

/**
 * 响应拦截器配置
 */
export interface ResponseInterceptor {
  onFulfilled?: (
    response: AxiosResponse,
  ) => AxiosResponse | Promise<AxiosResponse>;
  onRejected?: (error: AxiosError) => any;
}
