from typing import Optional
from pydantic import BaseModel, Field

# 滴答清单OAuth认证请求
class DidaOAuthRequest(BaseModel):
    system_user_id: int = Field(..., description="系统用户ID")
    client_id: str = Field(..., description="滴答清单应用Client ID")
    client_secret: str = Field(..., description="滴答清单应用Client Secret")
    authorization_code: str = Field(..., description="OAuth授权码")
    redirect_uri: str = Field(..., description="OAuth回调地址（必须与授权时一致）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "system_user_id": 1000000001,
                "client_id": "your_client_id",
                "client_secret": "your_client_secret",
                "authorization_code": "auth_code_from_oauth_callback",
                "redirect_uri": "http://localhost:1420/dida-binding"
            }
        }

# 滴答清单凭证刷新请求
class DidaRefreshTokenRequest(BaseModel):
    system_user_id: int = Field(..., description="系统用户ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "system_user_id": 1000000001
            }
        }

# 滴答清单绑定状态响应
class DidaBindingStatusResponse(BaseModel):
    is_bound: bool = Field(..., description="是否已绑定")
    username: Optional[str] = Field(None, description="绑定的滴答清单账号")
    bound_at: Optional[str] = Field(None, description="绑定时间")
    token_expires_at: Optional[str] = Field(None, description="令牌过期时间")

# 滴答清单OAuth响应
class DidaOAuthResponse(BaseModel):
    status: str = Field(..., description="状态: success, error")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="额外数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "滴答清单账号绑定成功！",
                "data": {
                    "username": "user@example.com",
                    "expires_at": "2025-01-09T12:00:00"
                }
            }
        }

