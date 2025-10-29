"""
小米认证相关数据模型
"""

from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class XiaomiLoginRequest(BaseModel):
    """小米登录请求"""
    system_user_id: int = Field(..., description="系统用户ID")
    username: str = Field(..., description="小米账号（手机号/邮箱）")
    password: str = Field(..., description="密码")
    server: str = Field(default="cn", description="服务器区域")
    
    class Config:
        json_schema_extra = {
            "example": {
                "system_user_id": 1000000001,
                "username": "13800138000",
                "password": "your_password",
                "server": "cn"
            }
        }


class CaptchaSubmitRequest(BaseModel):
    """验证码提交请求"""
    session_id: str = Field(..., description="会话ID")
    captcha_code: str = Field(..., description="验证码")


class TwoFactorAuthRequest(BaseModel):
    """双因素认证请交"""
    session_id: str = Field(..., description="会话ID")
    ticket: str = Field(..., description="2FA验证码")


# ==================== 响应模型 ====================

class LoginStepResponse(BaseModel):
    """登录步骤响应"""
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态: success, need_captcha, need_2fa, error")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="额外数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "status": "need_captcha",
                "message": "需要验证码",
                "data": {
                    "captcha_url": "/api/v1/xiaomi/captcha/sess_abc123"
                }
            }
        }


class BindingStatusResponse(BaseModel):
    """绑定状态响应"""
    is_bound: bool = Field(..., description="是否已绑定")
    username: Optional[str] = Field(None, description="绑定的小米账号")
    bound_at: Optional[str] = Field(None, description="绑定时间")


class XiaomiDeviceInfo(BaseModel):
    """小米设备信息"""
    name: str
    did: str
    token: Optional[str] = None
    model: Optional[str] = None
    mac: Optional[str] = None
    localip: Optional[str] = None

