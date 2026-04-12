import logging
import hashlib
import time
import random
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from database import query, insert, update

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    nickname: Optional[str] = Field(None, description="昵称")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    created_at: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[UserResponse] = None
    xiaomi_bound: bool = False  # 是否已绑定小米账号


class UserProfileUpdateRequest(BaseModel):
    """用户资料更新请求"""
    user_id: int = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")
    phone: Optional[str] = Field(None, max_length=32, description="手机号")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")


class UserProfileUpdateResponse(BaseModel):
    """用户资料更新响应"""
    success: bool
    message: str
    user: UserResponse


# ==================== 辅助函数 ====================

def hash_password(password: str) -> str:
    """密码加密"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token(user_id: int) -> str:
    """生成简单的token（生产环境应使用JWT）"""
    import uuid
    return f"{user_id}_{uuid.uuid4().hex}"


def generate_user_id() -> int:
    """生成用户ID"""
    return int(time.time() * 1000) + random.randint(1000, 9999)


def _normalize_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


# ==================== API 端点 ====================

@router.post("/register", response_model=LoginResponse)
async def register(data: UserRegisterRequest):
    """
    用户注册
    """
    try:
        # 检查用户名是否已存在
        check_sql = "SELECT id FROM users WHERE username = %s"
        existing_user = query(check_sql, (data.username,))
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        if data.email:
            check_email_sql = "SELECT id FROM users WHERE email = %s"
            existing_email = query(check_email_sql, (data.email,))
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
        
        # 生成用户ID
        user_id = generate_user_id()
        
        # 加密密码
        hashed_password = hash_password(data.password)
        
        # 插入用户记录
        insert_sql = """
            INSERT INTO users 
            (id, username, password, email, phone, nickname, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
        """
        insert(insert_sql, (
            user_id,
            data.username,
            hashed_password,
            data.email,
            data.phone,
            data.nickname or data.username
        ))
        
        # 生成token
        token = generate_token(user_id)
        
        # 返回用户信息
        user_info = UserResponse(
            id=user_id,
            username=data.username,
            nickname=data.nickname or data.username,
            email=data.email,
            phone=data.phone,
            avatar=None,
            created_at=str(time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        
        logger.info(f"用户注册成功: {data.username}")
        
        return LoginResponse(
            success=True,
            message="注册成功",
            token=token,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(data: UserLoginRequest):
    """
    用户登录
    """
    try:
        # 查询用户
        sql = """
            SELECT id, username, password, nickname, email, phone, avatar, 
                   status, created_at
            FROM users 
            WHERE username = %s
        """
        users = query(sql, (data.username,))
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        user = users[0]
        
        # 检查状态
        if user.get("status") != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用"
            )
        
        # 验证密码
        hashed_password = hash_password(data.password)
        if user.get("password") != hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 注意：StarRocks DUPLICATE KEY 表不支持 UPDATE，跳过更新最后登录时间
        # TODO: 如果需要记录登录时间，可以改用 PRIMARY KEY 表或单独的登录日志表
        
        # 生成token
        token = generate_token(user["id"])
        
        # 仅 is_active=1 视为已绑定（与 /xiaomi/binding/status、解绑一致）
        xiaomi_check_sql = "SELECT id, xiaomi_username, is_active FROM xiaomi_account WHERE system_user_id = %s AND is_active = 1"
        xiaomi_result = query(xiaomi_check_sql, (user["id"],))
        xiaomi_bound = len(xiaomi_result) > 0
        logger.info(f"🔍 用户 {user['id']} 小米绑定 (is_active=1): {xiaomi_result}, xiaomi_bound={xiaomi_bound}")
        
        # 返回用户信息
        user_info = UserResponse(
            id=user["id"],
            username=user["username"],
            nickname=user.get("nickname"),
            email=user.get("email"),
            phone=user.get("phone"),
            avatar=user.get("avatar"),
            created_at=str(user.get("created_at", ""))
        )
        
        logger.info(f"用户登录成功: {data.username}, 小米绑定状态: {xiaomi_bound}")
        
        return LoginResponse(
            success=True,
            message="登录成功",
            token=token,
            user=user_info,
            xiaomi_bound=xiaomi_bound
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/logout")
async def logout():
    """
    用户登出
    """
    return {
        "success": True,
        "message": "登出成功"
    }


@router.get("/check-username/{username}")
async def check_username(username: str):
    """
    检查用户名是否可用
    """
    try:
        sql = "SELECT id FROM users WHERE username = %s"
        result = query(sql, (username,))
        
        return {
            "available": len(result) == 0,
            "message": "用户名可用" if len(result) == 0 else "用户名已存在"
        }
    except Exception as e:
        logger.error(f"检查用户名失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/profile", response_model=UserProfileUpdateResponse)
async def update_profile(data: UserProfileUpdateRequest):
    """
    更新用户基本资料
    """
    try:
        user_sql = """
            SELECT id, username, nickname, email, phone, avatar, created_at
            FROM users
            WHERE id = %s
            LIMIT 1
        """
        user_rows = query(user_sql, (data.user_id,))
        if not user_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        update_payload = data.model_dump(exclude_unset=True)
        update_payload.pop("user_id", None)

        normalized_updates = {}
        for field_name, raw_value in update_payload.items():
            normalized_updates[field_name] = _normalize_optional_string(raw_value)

        if "email" in normalized_updates and normalized_updates["email"] is not None:
            email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            if not email_pattern.fullmatch(normalized_updates["email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱格式不正确"
                )

            email_check_sql = "SELECT id FROM users WHERE email = %s AND id <> %s LIMIT 1"
            same_email_users = query(email_check_sql, (normalized_updates["email"], data.user_id))
            if same_email_users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该邮箱已被其他账号使用"
                )

        if "phone" in normalized_updates and normalized_updates["phone"] is not None:
            phone_pattern = re.compile(r"^[0-9+\-\s]{6,20}$")
            if not phone_pattern.fullmatch(normalized_updates["phone"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="手机号格式不正确"
                )

        if "avatar" in normalized_updates and normalized_updates["avatar"] is not None:
            if not (
                normalized_updates["avatar"].startswith("http://")
                or normalized_updates["avatar"].startswith("https://")
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="头像地址需以 http:// 或 https:// 开头"
                )

        if normalized_updates:
            set_parts = [f"{field_name} = %s" for field_name in normalized_updates.keys()]
            update_sql = f"""
                UPDATE users
                SET {", ".join(set_parts)}, updated_at = NOW()
                WHERE id = %s
            """
            update_params = tuple(normalized_updates.values()) + (data.user_id,)
            update(update_sql, update_params)

        refreshed_rows = query(user_sql, (data.user_id,))
        if not refreshed_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        refreshed = refreshed_rows[0]
        return UserProfileUpdateResponse(
            success=True,
            message="用户资料更新成功",
            user=UserResponse(
                id=refreshed["id"],
                username=refreshed["username"],
                nickname=refreshed.get("nickname"),
                email=refreshed.get("email"),
                phone=refreshed.get("phone"),
                avatar=refreshed.get("avatar"),
                created_at=str(refreshed.get("created_at", "")),
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户资料失败: {str(e)}"
        )

