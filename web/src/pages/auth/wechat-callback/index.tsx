import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Spin, message } from 'antd';

const WechatCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleWechatCallback = async () => {
      try {
        // 获取微信回调参数
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        if (error) {
          console.error('微信登录错误:', error, errorDescription);
          message.error('微信登录失败，请重试');
          navigate('/');
          return;
        }

        if (!code || !state) {
          message.error('登录参数错误');
          navigate('/');
          return;
        }

        // 解析state参数
        const stateData = JSON.parse(decodeURIComponent(state));
        const { sceneId } = stateData;

        // 获取微信用户信息
        const userInfo = await getWechatUserInfo(code);
        
        if (userInfo) {
          // 将登录信息保存到本地存储，供主页面轮询使用
          localStorage.setItem(`wechat_login_${sceneId}`, JSON.stringify({
            status: 'success',
            code,
            state,
            ...userInfo
          }));

          // 跳转回主页面
          navigate('/');
        } else {
          message.error('获取用户信息失败');
          navigate('/');
        }
      } catch (error) {
        console.error('处理微信回调失败:', error);
        message.error('登录处理失败，请重试');
        navigate('/');
      }
    };

    handleWechatCallback();
  }, [searchParams, navigate]);

  // 获取微信用户信息
  const getWechatUserInfo = async (code: string) => {
    try {
      // 这里需要调用您的后端API来获取微信用户信息
      // 或者直接使用微信的API（需要access_token）
      const response = await fetch('/api/wechat/user-info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code })
      });

      const result = await response.json();
      
      if (result.success) {
        return {
          openid: result.openid,
          unionid: result.unionid,
          nickname: result.nickname,
          avatar: result.headimgurl
        };
      } else {
        throw new Error(result.message || '获取用户信息失败');
      }
    } catch (error) {
      console.error('获取微信用户信息失败:', error);
      return null;
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: '20px'
    }}>
      <Spin size="large" />
      <p>正在处理微信登录...</p>
    </div>
  );
};

export default WechatCallback;
