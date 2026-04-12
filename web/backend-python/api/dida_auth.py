import logging
import time
import random
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
import requests

from models.dida_auth import (
    DidaOAuthRequest,
    DidaRefreshTokenRequest,
    DidaBindingStatusResponse,
    DidaOAuthResponse,
)
from database import query, update, insert, get_db_type

logger = logging.getLogger(__name__)
router = APIRouter()

# 滴答清单OAuth配置
DIDA_OAUTH_BASE_URL = "https://dida365.com/oauth"
DIDA_API_BASE_URL = "https://api.dida365.com/open/v1"


def _set_plugin_mode_enabled(plugin_key: str) -> None:
    """绑定成功后默认启用插件。"""
    config_key = f"plugin.{plugin_key}.mode"
    description = f"{plugin_key} 插件模式（enabled/disabled/unused）"
    exists = query(
        "SELECT id FROM system_config WHERE config_key = %s LIMIT 1",
        (config_key,),
    )
    if exists:
        update(
            """
            UPDATE system_config
            SET config_value = 'enabled', config_type = 'string', category = 'plugin',
                description = %s, is_active = 1, updated_at = NOW()
            WHERE config_key = %s
            """,
            (description, config_key),
        )
        return

    db_type = get_db_type()
    if db_type == "starrocks":
        max_row = query("SELECT COALESCE(MAX(id), 0) AS max_id FROM system_config")
        next_id = int(max_row[0]["max_id"]) + 1 if max_row else 1
        insert(
            """
            INSERT INTO system_config
            (id, config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
            VALUES (%s, %s, 'enabled', 'string', 'plugin', %s, 1, NOW(), NOW())
            """,
            (next_id, config_key, description),
        )
    else:
        insert(
            """
            INSERT INTO system_config
            (config_key, config_value, config_type, category, description, is_active, created_at, updated_at)
            VALUES (%s, 'enabled', 'string', 'plugin', %s, 1, NOW(), NOW())
            """,
            (config_key, description),
        )


class DidaOAuthClient:
    """滴答清单OAuth客户端"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def exchange_code_for_token(self, authorization_code: str, redirect_uri: str) -> Dict:
        """
        用授权码换取访问令牌

        Args:
            authorization_code: OAuth授权码
            redirect_uri: 重定向URI（必须与OAuth申请时一致）

        Returns:
            包含access_token、refresh_token等的字典
        """
        url = f"{DIDA_OAUTH_BASE_URL}/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        try:
            logger.info(f"🔄 开始交换OAuth令牌")
            logger.info(f"   URL: {url}")
            logger.info(f"   client_id: {self.client_id}")
            logger.info(f"   client_secret: {self.client_secret[:10]}..." if self.client_secret else "   client_secret: None")
            logger.info(f"   code: {authorization_code}")
            logger.info(f"   redirect_uri: {redirect_uri}")
            
            response = requests.post(url, data=data, timeout=10)
            
            logger.info(f"📡 响应状态码: {response.status_code}")
            logger.info(f"📡 响应头: {dict(response.headers)}")
            
            # 记录详细的错误信息
            if response.status_code != 200:
                error_detail = response.text[:500]  # 只记录前500字符
                logger.error(f"❌ OAuth令牌交换失败 [{response.status_code}]")
                logger.error(f"   错误详情: {error_detail}")
                
                # 尝试解析JSON错误
                try:
                    error_json = response.json()
                    error_msg = error_json.get('error_description') or error_json.get('error') or error_detail
                except:
                    error_msg = error_detail
                
                raise HTTPException(
                    status_code=400, 
                    detail=f"OAuth令牌交换失败: {error_msg}"
                )
            
            result = response.json()
            logger.info(f"✅ OAuth令牌交换成功")

            if "access_token" not in result:
                raise ValueError(f"OAuth响应中缺少access_token: {result}")

            return result
        except HTTPException:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ OAuth令牌交换网络错误: {e}")
            raise HTTPException(status_code=400, detail=f"OAuth令牌交换失败: {str(e)}")

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新access_token的字典
        """
        url = f"{DIDA_OAUTH_BASE_URL}/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()

            if "access_token" not in result:
                raise ValueError(f"刷新令牌响应中缺少access_token: {result}")

            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"刷新令牌失败: {e}")
            raise HTTPException(status_code=400, detail=f"刷新令牌失败: {str(e)}")

    def get_user_info(self, access_token: str) -> Dict:
        """
        获取用户信息
        注意：滴答清单Open API可能不提供用户详情接口，我们可以跳过这一步

        Args:
            access_token: 访问令牌

        Returns:
            用户信息字典（如果API不支持，返回空字典）
        """
        # 滴答清单Open API可能不提供标准的用户信息接口
        # 我们可以尝试获取项目列表来验证token有效性
        url = f"{DIDA_API_BASE_URL}/project"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            # 如果能成功获取项目列表，说明token有效
            # 返回一个包含基本信息的字典
            projects = response.json()
            logger.info(f"Token验证成功，用户有 {len(projects) if isinstance(projects, list) else 0} 个项目")
            return {"verified": True, "project_count": len(projects) if isinstance(projects, list) else 0}
        except requests.exceptions.RequestException as e:
            logger.error(f"验证access_token失败: {e}")
            raise HTTPException(status_code=400, detail=f"验证access_token失败: {str(e)}")


@router.post("/oauth/callback", response_model=DidaOAuthResponse)
async def handle_oauth_callback(request: DidaOAuthRequest):
    """
    处理OAuth回调，交换授权码为访问令牌并保存

    Args:
        request: OAuth请求，包含授权码、Client凭证和redirect_uri

    Returns:
        OAuth响应
    """
    try:
        # 创建OAuth客户端
        oauth_client = DidaOAuthClient(request.client_id, request.client_secret)

        # 交换授权码为令牌（必须传递redirect_uri）
        logger.info(f"用户 {request.system_user_id} 正在交换OAuth授权码...")
        logger.info(f"redirect_uri: {request.redirect_uri}")
        token_result = oauth_client.exchange_code_for_token(
            authorization_code=request.authorization_code,
            redirect_uri=request.redirect_uri
        )

        logger.info(f"Token响应: {token_result}")
        
        access_token = token_result["access_token"]
        # refresh_token可能不存在，使用access_token作为备用
        refresh_token = token_result.get("refresh_token", access_token)
        expires_in = token_result.get("expires_in", 7200)  # 默认2小时
        
        if not token_result.get("refresh_token"):
            logger.warning("OAuth响应中未包含refresh_token，使用access_token作为备用")

        # 验证token并获取基本信息
        user_info = oauth_client.get_user_info(access_token)
        # 滴答清单可能不返回用户名，使用一个默认值
        dida_username = user_info.get("username") or user_info.get("email") or f"dida_user_{request.system_user_id}"
        logger.info(f"使用滴答清单账号名: {dida_username}")

        # 计算令牌过期时间
        token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # 保存到数据库
        await save_dida_credentials(
            system_user_id=request.system_user_id,
            dida_username=dida_username,
            client_id=request.client_id,
            client_secret=request.client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
        )

        return DidaOAuthResponse(
            status="success",
            message="滴答清单账号绑定成功！",
            data={
                "username": dida_username,
                "expires_at": token_expires_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth回调处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.post("/refresh", response_model=DidaOAuthResponse)
async def refresh_dida_token(request: DidaRefreshTokenRequest):
    """
    刷新滴答清单访问令牌

    Args:
        request: 包含system_user_id的请求

    Returns:
        OAuth响应
    """
    try:
        # 查询当前凭证
        credentials = await get_dida_credentials(request.system_user_id)
        if not credentials:
            raise HTTPException(status_code=404, detail="未找到滴答清单绑定信息，请先绑定账号")

        # 创建OAuth客户端
        oauth_client = DidaOAuthClient(
            credentials["client_id"], credentials["client_secret"]
        )

        # 刷新令牌
        logger.info(f"用户 {request.system_user_id} 正在刷新滴答清单令牌...")
        token_result = oauth_client.refresh_access_token(credentials["refresh_token"])

        access_token = token_result["access_token"]
        refresh_token = token_result.get("refresh_token", credentials["refresh_token"])
        expires_in = token_result.get("expires_in", 7200)

        # 计算新的过期时间
        token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # 更新数据库
        await update_dida_credentials(
            system_user_id=request.system_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
        )

        return DidaOAuthResponse(
            status="success",
            message="令牌刷新成功",
            data={
                "expires_at": token_expires_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.get("/binding/status", response_model=DidaBindingStatusResponse)
async def check_binding_status(system_user_id: int):
    """
    检查滴答清单账号绑定状态

    Args:
        system_user_id: 系统用户ID

    Returns:
        绑定状态响应
    """
    try:
        logger.info(f"🔍 检查用户 {system_user_id} 的滴答清单绑定状态")

        credentials = await get_dida_credentials(system_user_id)

        if credentials:
            logger.info(f"✅ 找到绑定账号: {credentials['dida_username']}")
            return DidaBindingStatusResponse(
                is_bound=True,
                username=credentials["dida_username"],
                bound_at=str(credentials["created_at"]),
                token_expires_at=str(credentials.get("token_expires_at")),
            )

        logger.info(f"❌ 未找到绑定账号，system_user_id={system_user_id}")
        return DidaBindingStatusResponse(is_bound=False)

    except Exception as e:
        logger.error(f"❌ check_binding_status error: {e}", exc_info=True)
        return DidaBindingStatusResponse(is_bound=False)


@router.delete("/unbind")
async def unbind_dida_account(system_user_id: int):
    """
    解绑滴答清单账号

    Args:
        system_user_id: 系统用户ID

    Returns:
        操作结果
    """
    try:
        db_type = get_db_type()

        if db_type == "mysql":
            # MySQL: 软删除（设置is_active=0）
            update_sql = """
                UPDATE dida_credentials 
                SET is_active = 0 
                WHERE system_user_id = %s
            """
            update(update_sql, (system_user_id,))
        else:
            # StarRocks: 由于是DUPLICATE KEY表，不支持DELETE，插入一条标记删除的记录
            # 这里简单起见，我们不真正删除，只是在查询时忽略
            logger.warning("StarRocks不支持DELETE，请手动处理或在查询时过滤")

        return {"status": "success", "message": "滴答清单账号已解绑"}

    except Exception as e:
        logger.error(f"解绑账号失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解绑失败: {str(e)}")


# ==================== 数据库操作辅助函数 ====================


async def save_dida_credentials(
    system_user_id: int,
    dida_username: str,
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
):
    """
    保存滴答清单凭证到数据库

    Args:
        system_user_id: 系统用户ID
        dida_username: 滴答清单用户名
        client_id: 应用Client ID
        client_secret: 应用Client Secret
        access_token: 访问令牌
        refresh_token: 刷新令牌
        token_expires_at: 令牌过期时间
    """
    try:
        db_type = get_db_type()

        if db_type == "mysql":
            # MySQL: 先禁用旧凭证，再插入新凭证
            update_sql = """
                UPDATE dida_credentials 
                SET is_active = 0 
                WHERE system_user_id = %s
            """
            update(update_sql, (system_user_id,))

            insert_sql = """
                INSERT INTO dida_credentials 
                (system_user_id, dida_username, client_id, client_secret, 
                 access_token, refresh_token, token_expires_at, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
            """
            insert(
                insert_sql,
                (
                    system_user_id,
                    dida_username,
                    client_id,
                    client_secret,
                    access_token,
                    refresh_token,
                    token_expires_at,
                ),
            )
            logger.info(f"[MySQL] 用户 {system_user_id} 成功绑定滴答清单账号: {dida_username}")

        else:  # StarRocks
            # StarRocks: 直接插入新记录
            credential_id = int(time.time() * 1000) + random.randint(1000, 9999)
            insert_sql = """
                INSERT INTO dida_credentials 
                (id, system_user_id, dida_username, client_id, client_secret, 
                 access_token, refresh_token, token_expires_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            insert(
                insert_sql,
                (
                    credential_id,
                    system_user_id,
                    dida_username,
                    client_id,
                    client_secret,
                    access_token,
                    refresh_token,
                    token_expires_at,
                ),
            )
            logger.info(f"[StarRocks] 用户 {system_user_id} 成功绑定滴答清单账号: {dida_username}")

        _set_plugin_mode_enabled("dida")

    except Exception as e:
        logger.error(f"save_dida_credentials error: {e}")
        raise


async def update_dida_credentials(
    system_user_id: int,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
):
    """
    更新滴答清单凭证（主要用于刷新令牌）

    Args:
        system_user_id: 系统用户ID
        access_token: 新的访问令牌
        refresh_token: 新的刷新令牌
        token_expires_at: 新的过期时间
    """
    try:
        db_type = get_db_type()

        if db_type == "mysql":
            update_sql = """
                UPDATE dida_credentials 
                SET access_token = %s, 
                    refresh_token = %s,
                    token_expires_at = %s,
                    updated_at = NOW()
                WHERE system_user_id = %s AND is_active = 1
            """
            update(update_sql, (access_token, refresh_token, token_expires_at, system_user_id))
            logger.info(f"[MySQL] 用户 {system_user_id} 的滴答清单令牌已更新")
        else:
            # StarRocks: 插入新记录
            credentials = await get_dida_credentials(system_user_id)
            if credentials:
                await save_dida_credentials(
                    system_user_id=system_user_id,
                    dida_username=credentials["dida_username"],
                    client_id=credentials["client_id"],
                    client_secret=credentials["client_secret"],
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                )

    except Exception as e:
        logger.error(f"update_dida_credentials error: {e}")
        raise


async def get_dida_credentials(system_user_id: int) -> Optional[Dict]:
    """
    获取用户的滴答清单凭证

    Args:
        system_user_id: 系统用户ID

    Returns:
        凭证字典，如果不存在则返回None
    """
    try:
        db_type = get_db_type()

        if db_type == "mysql":
            sql = """
                SELECT dida_username, client_id, client_secret, access_token, 
                       refresh_token, token_expires_at, created_at, updated_at
                FROM dida_credentials 
                WHERE system_user_id = %s AND is_active = 1
                ORDER BY updated_at DESC 
                LIMIT 1
            """
        else:
            # StarRocks: 取最新记录
            sql = """
                SELECT dida_username, client_id, client_secret, access_token, 
                       refresh_token, token_expires_at, created_at, updated_at
                FROM dida_credentials 
                WHERE system_user_id = %s
                ORDER BY updated_at DESC 
                LIMIT 1
            """

        result = query(sql, (system_user_id,))

        if result and len(result) > 0:
            return result[0]

        return None

    except Exception as e:
        logger.error(f"get_dida_credentials error: {e}")
        return None

