
# 第一阶段: 构建前端应用
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 复制依赖配置文件
COPY package.json pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制项目文件
COPY . .

# 构建应用
# 设置生产环境变量
ENV NODE_ENV=production
RUN pnpm run build

# 第二阶段: 使用 Nginx 部署
FROM nginx:alpine

# 安装必要的工具
RUN apk add --no-cache curl

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 创建一个脚本来处理环境变量
RUN echo '#!/bin/sh' > /docker-entrypoint.d/40-substitute-env.sh && \
    echo 'if [ -n "$VITE_BACKEND_URL" ]; then' >> /docker-entrypoint.d/40-substitute-env.sh && \
    echo '  echo "window.__ENV__ = { VITE_BACKEND_URL: \"$VITE_BACKEND_URL\" };" > /usr/share/nginx/html/env-config.js' >> /docker-entrypoint.d/40-substitute-env.sh && \
    echo 'fi' >> /docker-entrypoint.d/40-substitute-env.sh && \
    chmod +x /docker-entrypoint.d/40-substitute-env.sh

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

