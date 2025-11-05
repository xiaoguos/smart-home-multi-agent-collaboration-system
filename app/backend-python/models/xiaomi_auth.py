from typing import Optional
from pydantic import BaseModel, Field

# 小米登录请求
class XiaomiLoginRequest(BaseModel):
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

# 验证码提交请求
class CaptchaSubmitRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    captcha_code: str = Field(..., description="验证码")

# 双因素认证请求
class TwoFactorAuthRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    ticket: str = Field(..., description="2FA验证码")

# 手动输入凭证请求
class ManualCredentialsRequest(BaseModel):
    system_user_id: int = Field(..., description="系统用户ID")
    xiaomi_username: str = Field(..., description="小米账号")
    ssecurity: str = Field(..., description="_ssecurity参数")
    userId: str = Field(..., description="userId参数")
    cUserId: str = Field(..., description="_cUserId参数")
    serviceToken: str = Field(..., description="serviceToken参数")
    server: str = Field(default="cn", description="服务器区域")
    
    class Config:
        json_schema_extra = {
            "example": {
                "system_user_id": 1000000001,
                "xiaomi_username": "13800138000",
                "ssecurity": "R9egnuetTRF9sMP2jy9yJQ==",
                "userId": "3128533266",
                "cUserId": "5suobuxuMCJG7d6Wtp3I28D30l0",
                "serviceToken": "2ib8u26oDE7OoCSawL3M5rvrIR7koVw...",
                "server": "cn"
            }
        }

# 登录步骤响应
class LoginStepResponse(BaseModel):
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

# 绑定状态响应
class BindingStatusResponse(BaseModel):
    is_bound: bool = Field(..., description="是否已绑定")
    username: Optional[str] = Field(None, description="绑定的小米账号")
    bound_at: Optional[str] = Field(None, description="绑定时间")

# 小米设备信息
class XiaomiDeviceInfo(BaseModel):
    name: str
    did: str
    token: Optional[str] = None
    model: Optional[str] = None
    mac: Optional[str] = None
    localip: Optional[str] = None

