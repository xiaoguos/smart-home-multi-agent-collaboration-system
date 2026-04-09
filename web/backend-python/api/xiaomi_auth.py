import logging
import uuid
import base64
import hashlib
import hmac
import json
import os
import random
import time
from typing import Dict, Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import requests

try:
    from Crypto.Cipher import ARC4
except ModuleNotFoundError:
    from Cryptodome.Cipher import ARC4

from models.xiaomi_auth import (
    XiaomiLoginRequest,
    CaptchaSubmitRequest,
    TwoFactorAuthRequest,
    ManualCredentialsRequest,
    LoginStepResponse,
    BindingStatusResponse,
)
from database import query, update, insert, get_db_type

logger = logging.getLogger(__name__)
router = APIRouter()

# 会话存储（生产环境应使用 Redis）
SESSIONS: Dict[str, dict] = {}


class XiaomiCloudConnector:
    """小米云连接器（基于 token_extractor.py）"""

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session = requests.session()
        self._sign = None
        self._ssecurity = ""
        self.userId = ""
        self._cUserId = ""
        self._passToken = None
        self._location = None
        self._code = None
        self._serviceToken = ""
        self._captcha_url = None

    def login_step_1(self) -> dict:
        """登录步骤1：获取 sign"""
        logger.debug("login_step_1")
        url = "https://account.xiaomi.com/pass/serviceLogin?sid=xiaomiio&_json=true"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        cookies = {"userId": self._username}
        
        try:
            response = self._session.get(url, headers=headers, cookies=cookies, timeout=10)
            json_resp = self.to_json(response.text)
            
            if response.status_code == 200:
                if "_sign" in json_resp:
                    self._sign = json_resp["_sign"]
                    return {"success": True}
                elif "ssecurity" in json_resp:
                    self._ssecurity = json_resp["ssecurity"]
                    self.userId = json_resp["userId"]
                    self._cUserId = json_resp["cUserId"]
                    self._passToken = json_resp["passToken"]
                    self._location = json_resp["location"]
                    self._code = json_resp["code"]
                    return {"success": True}
            
            return {"success": False, "error": "登录步骤1失败"}
        except Exception as e:
            logger.error(f"login_step_1 error: {e}")
            return {"success": False, "error": str(e)}

    def login_step_2(self, captcha_code: Optional[str] = None) -> dict:
        """登录步骤2：提交密码"""
        url = "https://account.xiaomi.com/pass/serviceLoginAuth2"
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        fields = {
            "sid": "xiaomiio",
            "hash": hashlib.md5(str.encode(self._password)).hexdigest().upper(),
            "callback": "https://sts.api.io.mi.com/sts",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "user": self._username,
            "_sign": self._sign,
            "_json": "true"
        }
        
        if captcha_code:
            fields["captCode"] = captcha_code
        
        try:
            response = self._session.post(url, headers=headers, params=fields, 
                                         allow_redirects=False, timeout=10)
            
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            json_resp = self.to_json(response.text)
            
            # 需要验证码
            if "captchaUrl" in json_resp and json_resp["captchaUrl"]:
                self._captcha_url = json_resp["captchaUrl"]
                if self._captcha_url.startswith("/"):
                    self._captcha_url = "https://account.xiaomi.com" + self._captcha_url
                return {
                    "success": False,
                    "need_captcha": True,
                    "captcha_url": self._captcha_url
                }
            
            # 验证码错误
            if "code" in json_resp and json_resp["code"] == 87001:
                return {"success": False, "error": "验证码无效"}
            
            # 登录成功
            if "ssecurity" in json_resp and len(str(json_resp["ssecurity"])) > 4:
                self._ssecurity = json_resp["ssecurity"]
                self.userId = json_resp.get("userId", "")
                self._cUserId = json_resp.get("cUserId", "")
                self._passToken = json_resp.get("passToken", "")
                self._location = json_resp.get("location", "")
                self._code = json_resp.get("code", "")
                return {"success": True}
            
            # 需要双因素认证
            if "notificationUrl" in json_resp:
                verify_url = json_resp["notificationUrl"]
                return {
                    "success": False,
                    "need_2fa": True,
                    "verify_url": verify_url
                }
            
            return {"success": False, "error": f"登录失败: {json_resp}"}
            
        except Exception as e:
            logger.error(f"login_step_2 error: {e}")
            return {"success": False, "error": str(e)}

    def trigger_2fa_send_simple(self, verify_url: str) -> dict:
        """简单版：让前端处理发送（废弃）"""
        return {"success": True, "verify_method": "手机或邮箱", "flag": 4}
    
    def trigger_2fa_send(self, verify_url: str) -> dict:
        """
        触发发送双因素认证验证码
        由于小米的安全机制，自动发送可能失败，建议用户手动操作
        """
        path = 'identity/authStart'
        if path not in verify_url:
            return {"success": False, "error": "无效的验证URL"}
        
        try:
            # 1. 访问 authStart 页面
            logger.info(f"Step 1: Visiting authStart: {verify_url}")
            resp = self._session.get(verify_url, timeout=10)
            
            if resp.status_code != 200:
                logger.warning(f"Failed to visit authStart: {resp.status_code}")
                return {"success": False, "error": f"访问验证页面失败: {resp.status_code}"}
            
            # 尝试从第一次请求获取 identity_session
            identity_session = resp.cookies.get('identity_session')
            logger.info(f"identity_session from authStart: {identity_session}")
            
            # 2. 获取验证方式
            list_url = verify_url.replace(path, 'identity/list')
            logger.info(f"Step 2: Getting verification method from: {list_url}")
            resp2 = self._session.get(list_url, timeout=10)
            
            if resp2.status_code != 200:
                logger.warning(f"Failed to get identity/list: {resp2.status_code}")
                return {"success": False, "error": "获取验证方式失败"}
            
            # 尝试从第二次请求获取 identity_session（如果第一次没有）
            if not identity_session:
                identity_session = resp2.cookies.get('identity_session')
                logger.info(f"identity_session from list: {identity_session}")
            
            # 检查所有 cookies
            logger.info(f"All cookies: {list(self._session.cookies.keys())}")
            
            if not identity_session:
                logger.warning("No identity_session cookie found in either request")
                # 尝试从 session.cookies 获取
                identity_session = self._session.cookies.get('identity_session', domain='account.xiaomi.com')
                if identity_session:
                    logger.info(f"Found identity_session in session cookies: {identity_session}")
                else:
                    # 无法获取 identity_session，但仍然返回成功，让用户手动操作
                    logger.warning("Cannot get identity_session, user needs manual operation")
            
            # 尝试解析响应
            try:
                data = self.to_json(resp2.text) or {}
                flag = data.get('flag', 4)
                options = data.get('options', [flag])
            except Exception as e:
                logger.warning(f"Failed to parse list response as JSON: {e}")
                logger.debug(f"Response text: {resp2.text[:500]}")
                # 使用默认值
                flag = 4
                options = [4]
            
            logger.info(f"Verification options: {options}, selected flag: {flag}")
            
            # 保存 identity_session 供后续使用
            self._identity_session = identity_session
            
            # 3. 尝试多种方式发送验证码
            for flag_option in options:
                verify_method = {
                    4: '手机短信',
                    8: '邮箱',
                }.get(flag_option, '手机或邮箱')
                
                # 方式1: 尝试 sendPhoneCode/sendEmailCode
                api_paths = [
                    f'/identity/auth/sendPhoneCode' if flag_option == 4 else '/identity/auth/sendEmailCode',
                    f'/identity/auth/send' if flag_option == 4 else '/identity/auth/sendEmail',
                ]
                
                for api_path in api_paths:
                    send_url = 'https://account.xiaomi.com' + api_path
                    logger.info(f"Step 3: Trying to send via: {send_url}")
                    
                    try:
                        # 尝试发送请求
                        post_data = {
                            '_json': 'true',
                            '_dc': str(int(time.time() * 1000)),
                        }
                        
                        resp3 = self._session.post(
                            send_url,
                            data=post_data,
                            cookies={
                                'identity_session': identity_session,
                            },
                            headers={
                                'User-Agent': self._agent,
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Referer': verify_url,
                                'Origin': 'https://account.xiaomi.com',
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'X-Requested-With': 'XMLHttpRequest',
                            },
                            timeout=10
                        )
                        
                        logger.info(f"Response status: {resp3.status_code}")
                        logger.info(f"Response: {resp3.text[:500]}")
                        
                        if resp3.status_code == 200:
                            result = self.to_json(resp3.text)
                            if result:
                                logger.info(f"Parsed result: {result}")
                                
                                # 检查是否成功
                                if result.get('code') == 0 or result.get('result') == 'ok':
                                    logger.info(f"✅ Verification code sent successfully to {verify_method}")
                                    return {
                                        "success": True, 
                                        "verify_method": verify_method,
                                        "flag": flag_option
                                    }
                                else:
                                    logger.warning(f"Send failed: {result}")
                        
                    except Exception as e:
                        logger.error(f"Error with {api_path}: {e}")
                        continue
            
            # 如果所有方式都失败，返回成功但提示用户手动操作
            logger.warning("Auto-send failed, user needs to manually click")
            return {
                "success": True,  # 仍返回成功，让用户手动处理
                "verify_method": "手机或邮箱", 
                "flag": 4,
                "manual": True  # 标记需要手动操作
            }
            
        except Exception as e:
            logger.error(f"trigger_2fa_send error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def verify_2fa(self, verify_url: str, ticket: str, saved_identity_session: str = None) -> dict:
        """验证双因素认证"""
        logger.info(f"verify_2fa called with ticket: {ticket}")
        path = 'identity/authStart'
        if path not in verify_url:
            return {"success": False, "error": "无效的验证URL"}
        
        try:
            # 优先使用保存的 identity_session
            identity_session = saved_identity_session
            
            if not identity_session:
                # 尝试获取新的 identity_session
                list_url = verify_url.replace(path, 'identity/list')
                logger.info(f"Getting identity/list from: {list_url}")
                resp = self._session.get(list_url, timeout=10)
                
                # 尝试从多个地方获取 identity_session
                identity_session = resp.cookies.get('identity_session')
                if not identity_session:
                    identity_session = self._session.cookies.get('identity_session', domain='account.xiaomi.com')
                
                logger.info(f"identity_session from request: {identity_session}")
            else:
                logger.info(f"Using saved identity_session: {identity_session}")
            
            logger.info(f"All cookies: {list(self._session.cookies.keys())}")
            
            if not identity_session:
                return {"success": False, "error": "会话已过期，请重新开始绑定流程"}
            
            # 获取验证方式
            if identity_session:
                # 如果有 identity_session，重新获取list以获取验证方式
                list_url = verify_url.replace(path, 'identity/list')
                resp_list = self._session.get(list_url, timeout=10)
                try:
                    data = self.to_json(resp_list.text) or {}
                except Exception as e:
                    logger.warning(f"Failed to parse list response: {e}")
                    data = {}
            else:
                data = {}
            
            flag = data.get('flag', 4)
            options = data.get('options', [flag])
            
            logger.info(f"Verification options: {options}, flag: {flag}")
            
            for flag_option in options:
                api = {
                    4: '/identity/auth/verifyPhone',
                    8: '/identity/auth/verifyEmail',
                }.get(flag_option)
                
                if not api:
                    logger.warning(f"Unknown flag: {flag_option}")
                    continue
                
                verify_api_url = 'https://account.xiaomi.com' + api
                logger.info(f"Verifying ticket via: {verify_api_url}")
                
                resp = self._session.post(
                    verify_api_url,
                    params={'_dc': int(time.time() * 1000)},
                    data={
                        '_flag': flag_option,
                        'ticket': ticket,
                        'trust': 'true',
                        '_json': 'true',
                    },
                    cookies={'identity_session': identity_session},
                    headers={
                        'User-Agent': self._agent,
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': verify_url,
                        'Origin': 'https://account.xiaomi.com',
                    },
                    timeout=10
                )
                
                logger.info(f"Verify response status: {resp.status_code}")
                logger.info(f"Verify response: {resp.text}")
                
                result = self.to_json(resp.text)
                logger.info(f"Parsed result: {result}")
                
                if result and result.get('code') == 0:
                    logger.info("✅ Verification successful!")
                    location = result.get("location")
                    if location:
                        logger.info(f"Following location: {location}")
                        self._session.get(location, allow_redirects=True, timeout=10)
                        # 重新执行步骤1
                        self.login_step_1()
                    return {"success": True}
                else:
                    error_desc = result.get('desc', '未知错误') if result else '响应解析失败'
                    logger.warning(f"Verification failed: code={result.get('code') if result else 'N/A'}, desc={error_desc}")
            
            return {"success": False, "error": "验证码错误或已过期，请重新发送"}
            
        except Exception as e:
            logger.error(f"verify_2fa error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def login_step_3(self) -> dict:
        """登录步骤3：获取服务令牌"""
        if not self._location:
            return {"success": False, "error": "没有 location"}
        
        headers = {
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = self._session.get(self._location, headers=headers, timeout=10)
            if response.status_code == 200:
                self._serviceToken = response.cookies.get("serviceToken")
                return {"success": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"login_step_3 error: {e}")
            return {"success": False, "error": str(e)}

    def get_captcha_image(self) -> Optional[bytes]:
        """获取验证码图片"""
        if not self._captcha_url:
            return None
        
        try:
            response = self._session.get(self._captcha_url, stream=True, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            logger.error(f"get_captcha_image error: {e}")
            return None

    @staticmethod
    def generate_agent():
        agent_id = "".join(chr(random.randint(65, 69)) for _ in range(13))
        random_text = "".join(chr(random.randint(97, 122)) for _ in range(18))
        return f"{random_text}-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"

    @staticmethod
    def generate_device_id():
        return "".join(chr(random.randint(97, 122)) for _ in range(6))

    @staticmethod
    def to_json(response_text):
        return json.loads(response_text.replace("&&&START&&&", ""))
    
    def get_homes(self, country: str = "cn") -> Optional[dict]:
        """获取家庭列表"""
        url = self.get_api_url(country) + "/v2/homeroom/gethome"
        params = {
            "data": '{"fg": true, "fetch_share": true, "fetch_share_dev": true, "limit": 300, "app_ver": 7}'
        }
        return self.execute_api_call_encrypted(url, params)
    
    def get_devices(self, country: str, home_id: str, owner_id: str) -> Optional[dict]:
        """获取指定家庭的设备列表"""
        url = self.get_api_url(country) + "/v2/home/home_device_list"
        params = {
            "data": '{"home_owner": ' + str(owner_id) +
            ',"home_id": ' + str(home_id) +
            ',  "limit": 200,  "get_split_device": true, "support_smart_home": true}'
        }
        return self.execute_api_call_encrypted(url, params)
    
    def get_dev_cnt(self, country: str = "cn") -> Optional[dict]:
        """获取设备数量"""
        url = self.get_api_url(country) + "/v2/user/get_device_cnt"
        params = {
            "data": '{ "fetch_own": true, "fetch_share": true}'
        }
        return self.execute_api_call_encrypted(url, params)
    
    def execute_api_call_encrypted(self, url: str, params: dict) -> Optional[dict]:
        """执行加密的API调用"""
        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self.userId),
            "yetAnotherServiceToken": str(self._serviceToken),
            "serviceToken": str(self._serviceToken),
            "locale": "en_GB",
            "timezone": "GMT+02:00",
            "is_daylight": "1",
            "dst_offset": "3600000",
            "channel": "MI_APP_STORE"
        }
        
        millis = round(time.time() * 1000)
        nonce = self.generate_nonce(millis)
        signed_nonce = self.signed_nonce(nonce)
        fields = self.generate_enc_params(url, "POST", signed_nonce, nonce, params, self._ssecurity)
        
        try:
            response = self._session.post(url, headers=headers, cookies=cookies, params=fields, timeout=10)
            if response.status_code == 200:
                decoded = self.decrypt_rc4(self.signed_nonce(fields["_nonce"]), response.text)
                return json.loads(decoded)
        except Exception as e:
            logger.error(f"execute_api_call_encrypted error: {e}")
        return None
    
    @staticmethod
    def get_api_url(country: str) -> str:
        """获取API URL"""
        return "https://" + ("" if country == "cn" else (country + ".")) + "api.io.mi.com/app"
    
    def signed_nonce(self, nonce: str) -> str:
        """签名nonce"""
        hash_object = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode('utf-8')
    
    @staticmethod
    def generate_nonce(millis: int) -> str:
        """生成nonce"""
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder='big')
        return base64.b64encode(nonce_bytes).decode()
    
    @staticmethod
    def generate_enc_signature(url: str, method: str, signed_nonce: str, params: dict) -> str:
        """生成加密签名"""
        signature_params = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_params.append(signed_nonce)
        signature_string = "&".join(signature_params)
        return base64.b64encode(hashlib.sha1(signature_string.encode('utf-8')).digest()).decode()
    
    @staticmethod
    def generate_enc_params(url: str, method: str, signed_nonce: str, nonce: str, params: dict, ssecurity: str) -> dict:
        """生成加密参数"""
        params['rc4_hash__'] = XiaomiCloudConnector.generate_enc_signature(url, method, signed_nonce, params)
        for k, v in params.items():
            params[k] = XiaomiCloudConnector.encrypt_rc4(signed_nonce, v)
        params.update({
            'signature': XiaomiCloudConnector.generate_enc_signature(url, method, signed_nonce, params),
            'ssecurity': ssecurity,
            '_nonce': nonce,
        })
        return params
    
    @staticmethod
    def encrypt_rc4(password: str, payload: str) -> str:
        """RC4加密"""
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return base64.b64encode(r.encrypt(payload.encode())).decode()
    
    @staticmethod
    def decrypt_rc4(password: str, payload: str) -> bytes:
        """RC4解密"""
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return r.encrypt(base64.b64decode(payload))


@router.post("/login/start", response_model=LoginStepResponse)
async def start_xiaomi_login(request: XiaomiLoginRequest):
    """
    开始小米账号登录流程
    """
    try:
        # 创建会话
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        connector = XiaomiCloudConnector(request.username, request.password)
        
        # 设置 cookies
        connector._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="mi.com")
        connector._session.cookies.set("sdkVersion", "accountsdk-18.8.15", domain="xiaomi.com")
        connector._session.cookies.set("deviceId", connector._device_id, domain="mi.com")
        connector._session.cookies.set("deviceId", connector._device_id, domain="xiaomi.com")
        
        # 步骤1
        result1 = connector.login_step_1()
        if not result1.get("success"):
            raise HTTPException(status_code=400, detail=result1.get("error", "登录步骤1失败"))
        
        # 步骤2
        result2 = connector.login_step_2()
        
        # 保存会话
        SESSIONS[session_id] = {
            "connector": connector,
            "system_user_id": request.system_user_id,
            "xiaomi_username": request.username,
            "server": request.server,
            "created_at": time.time()
        }
        
        # 需要验证码
        if result2.get("need_captcha"):
            return LoginStepResponse(
                session_id=session_id,
                status="need_captcha",
                message="需要输入验证码",
                data={
                    "captcha_url": f"/api/v1/xiaomi/captcha/{session_id}"
                }
            )
        
        # 需要双因素认证
        if result2.get("need_2fa"):
            verify_url = result2["verify_url"]
            # 自动触发验证码发送
            trigger_result = connector.trigger_2fa_send(verify_url)
            
            # 保存 verify_url 到 session
            SESSIONS[session_id]["verify_url"] = verify_url
            
            # 保存 identity_session 到 session（如果有的话）
            if hasattr(connector, '_identity_session') and connector._identity_session:
                SESSIONS[session_id]["identity_session"] = connector._identity_session
                logger.info(f"Saved identity_session to session")
            
            if trigger_result.get("success"):
                # 记录首次发送时间
                SESSIONS[session_id]["last_2fa_send_time"] = time.time()
                
                verify_method = trigger_result.get("verify_method", "手机或邮箱")
                manual = trigger_result.get("manual", False)
                
                return LoginStepResponse(
                    session_id=session_id,
                    status="need_2fa",
                    message=f"验证码已发送到您的{verify_method}，请查收" if not manual else "请手动发送验证码",
                    data={
                        "verify_method": verify_method,
                        "verify_url": verify_url  # 返回URL供前端使用
                    }
                )
            else:
                return LoginStepResponse(
                    session_id=session_id,
                    status="need_2fa",
                    message="需要双因素认证，请准备接收验证码",
                    data={
                        "verify_url": verify_url
                    }
                )
        
        # 登录成功
        if result2.get("success"):
            result3 = connector.login_step_3()
            if result3.get("success"):
                # 保存到数据库
                await save_xiaomi_credentials(
                    system_user_id=request.system_user_id,
                    xiaomi_username=request.username,
                    service_token=connector._serviceToken,
                    ssecurity=connector._ssecurity,
                    xiaomi_user_id=connector.userId,
                    server=request.server
                )
                
                # 清理会话
                SESSIONS.pop(session_id, None)
                
                return LoginStepResponse(
                    session_id=session_id,
                    status="success",
                    message="登录成功，小米账号已绑定！",
                    data={}
                )
        
        raise HTTPException(status_code=400, detail=result2.get("error", "登录失败"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"start_xiaomi_login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.get("/captcha/{session_id}")
async def get_captcha(session_id: str):
    """
    获取验证码图片
    """
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    connector = session["connector"]
    image_data = connector.get_captcha_image()
    
    if not image_data:
        raise HTTPException(status_code=404, detail="无法获取验证码图片")
    
    return Response(content=image_data, media_type="image/jpeg")


@router.post("/captcha/submit", response_model=LoginStepResponse)
async def submit_captcha(request: CaptchaSubmitRequest):
    """
    提交验证码
    """
    session = SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    connector = session["connector"]
    
    try:
        # 重新提交，带验证码
        result2 = connector.login_step_2(captcha_code=request.captcha_code)
        
        # 验证码错误，需要重新输入
        if result2.get("need_captcha"):
            return LoginStepResponse(
                session_id=request.session_id,
                status="need_captcha",
                message="验证码错误，请重新输入",
                data={
                    "captcha_url": f"/api/v1/xiaomi/captcha/{request.session_id}"
                }
            )
        
        # 需要双因素认证
        if result2.get("need_2fa"):
            verify_url = result2["verify_url"]
            # 自动触发验证码发送
            trigger_result = connector.trigger_2fa_send(verify_url)
            
            # 更新 session 中的 verify_url
            SESSIONS[request.session_id]["verify_url"] = verify_url
            
            if trigger_result.get("success"):
                # 记录首次发送时间
                SESSIONS[request.session_id]["last_2fa_send_time"] = time.time()
                
                verify_method = trigger_result.get("verify_method", "手机或邮箱")
                manual = trigger_result.get("manual", False)
                
                return LoginStepResponse(
                    session_id=request.session_id,
                    status="need_2fa",
                    message=f"验证码已发送到您的{verify_method}，请查收" if not manual else "请手动发送验证码",
                    data={
                        "verify_method": verify_method,
                        "verify_url": verify_url  # 返回URL供前端使用
                    }
                )
            else:
                return LoginStepResponse(
                    session_id=request.session_id,
                    status="need_2fa",
                    message="需要双因素认证，请准备接收验证码",
                    data={
                        "verify_url": verify_url
                    }
                )
        
        # 登录成功
        if result2.get("success"):
            result3 = connector.login_step_3()
            if result3.get("success"):
                # 保存到数据库
                await save_xiaomi_credentials(
                    username=session["username"],
                    service_token=connector._serviceToken,
                    ssecurity=connector._ssecurity,
                    user_id=connector.userId,
                    server=session["server"]
                )
                
                # 清理会话
                SESSIONS.pop(request.session_id, None)
                
                return LoginStepResponse(
                    session_id=request.session_id,
                    status="success",
                    message="登录成功，小米账号已绑定！",
                    data={}
                )
        
        raise HTTPException(status_code=400, detail=result2.get("error", "登录失败"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"submit_captcha error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.post("/2fa/refresh", response_model=LoginStepResponse)
async def refresh_2fa_session(request: dict):
    """
    刷新双因素认证会话（重新获取identity_session）
    """
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少会话ID")
    
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    connector = session["connector"]
    verify_url = session.get("verify_url")
    
    if not verify_url:
        raise HTTPException(status_code=400, detail="缺少验证URL")
    
    try:
        # 重新触发2FA流程以获取新的identity_session
        logger.info(f"Refreshing 2FA session for: {session_id}")
        trigger_result = connector.trigger_2fa_send(verify_url)
        
        # 更新保存的 identity_session
        if hasattr(connector, '_identity_session') and connector._identity_session:
            session["identity_session"] = connector._identity_session
            logger.info(f"Updated identity_session in session")
        
        if trigger_result.get("success"):
            # 重置倒计时
            session["last_2fa_send_time"] = time.time()
            
            verify_method = trigger_result.get("verify_method", "手机或邮箱")
            return LoginStepResponse(
                session_id=session_id,
                status="need_2fa",
                message=f"会话已刷新，验证码已发送到您的{verify_method}",
                data={
                    "verify_method": verify_method,
                    "verify_url": verify_url
                }
            )
        else:
            # 即使自动发送失败，也返回成功让用户手动操作
            return LoginStepResponse(
                session_id=session_id,
                status="need_2fa",
                message="会话已刷新，请手动发送验证码",
                data={
                    "verify_method": "手机或邮箱",
                    "verify_url": verify_url
                }
            )
    except Exception as e:
        logger.error(f"refresh_2fa_session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.post("/2fa/resend", response_model=LoginStepResponse)
async def resend_2fa_code(request: dict):
    """
    重新发送双因素认证验证码
    限制：每180秒只能发送一次
    """
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少会话ID")
    
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    # 检查发送间隔（180秒）
    last_send_time = session.get("last_2fa_send_time", 0)
    current_time = time.time()
    time_elapsed = current_time - last_send_time
    
    RESEND_INTERVAL = 180  # 180秒间隔
    
    if time_elapsed < RESEND_INTERVAL:
        wait_seconds = int(RESEND_INTERVAL - time_elapsed)
        raise HTTPException(
            status_code=429, 
            detail=f"发送过于频繁，请{wait_seconds}秒后再试"
        )
    
    connector = session["connector"]
    verify_url = session.get("verify_url")
    
    if not verify_url:
        raise HTTPException(status_code=400, detail="缺少验证URL")
    
    try:
        # 触发验证码发送
        trigger_result = connector.trigger_2fa_send(verify_url)
        
        if trigger_result.get("success"):
            # 更新最后发送时间
            session["last_2fa_send_time"] = current_time
            
            verify_method = trigger_result.get("verify_method", "手机或邮箱")
            return LoginStepResponse(
                session_id=session_id,
                status="need_2fa",
                message=f"验证码已重新发送到您的{verify_method}",
                data={
                    "verify_method": verify_method
                }
            )
        else:
            raise HTTPException(status_code=400, detail=trigger_result.get("error", "发送失败"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"resend_2fa_code error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.post("/2fa/verify", response_model=LoginStepResponse)
async def verify_2fa(request: TwoFactorAuthRequest):
    """
    验证双因素认证
    """
    session = SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    connector = session["connector"]
    
    try:
        # 从session中获取 verify_url 和 identity_session
        verify_url = session.get("verify_url")
        if not verify_url:
            raise HTTPException(status_code=400, detail="缺少验证URL")
        
        # 传入保存的 identity_session（如果有）
        saved_identity_session = session.get("identity_session")
        logger.info(f"Using saved identity_session: {saved_identity_session}")
        
        result = connector.verify_2fa(verify_url, request.ticket, saved_identity_session)
        
        if result.get("success"):
            # 验证成功后，需要执行步骤3获取 serviceToken
            result3 = connector.login_step_3()
            if result3.get("success"):
                # 保存到数据库
                await save_xiaomi_credentials(
                    system_user_id=session["system_user_id"],
                    xiaomi_username=session["xiaomi_username"],
                    service_token=connector._serviceToken,
                    ssecurity=connector._ssecurity,
                    xiaomi_user_id=connector.userId,
                    server=session["server"]
                )
                
                # 清理会话
                SESSIONS.pop(request.session_id, None)
                
                return LoginStepResponse(
                    session_id=request.session_id,
                    status="success",
                    message="登录成功，小米账号已绑定！",
                    data={}
                )
        
        raise HTTPException(status_code=400, detail=result.get("error", "验证失败"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"verify_2fa error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@router.get("/binding/status", response_model=BindingStatusResponse)
async def check_binding_status(system_user_id: int):
    """
    检查小米账号绑定状态
    需要传入 system_user_id 参数
    """
    try:
        logger.info(f"🔍 检查用户 {system_user_id} 的绑定状态")
        
        # 先查询该用户的所有绑定记录（调试用）
        debug_sql = """
            SELECT id, system_user_id, xiaomi_username, is_active, created_at, updated_at
            FROM xiaomi_account 
            WHERE system_user_id = %s
            ORDER BY updated_at DESC 
        """
        debug_result = query(debug_sql, (system_user_id,))
        logger.info(f"🔍 该用户所有绑定记录: {debug_result}")
        
        # 查询该用户最新的激活绑定记录
        sql = """
            SELECT xiaomi_username, created_at, is_active
            FROM xiaomi_account 
            WHERE system_user_id = %s AND is_active = 1
            ORDER BY updated_at DESC 
            LIMIT 1
        """
        result = query(sql, (system_user_id,))
        
        logger.info(f"📊 带 is_active=1 条件的查询结果: {result}")
        
        # 如果带 is_active 条件查不到，尝试不带条件
        if not result or len(result) == 0:
            logger.warning(f"⚠️ 带 is_active=1 条件查询失败，尝试不带条件查询")
            sql_no_active = """
                SELECT xiaomi_username, created_at, is_active
                FROM xiaomi_account 
                WHERE system_user_id = %s
                ORDER BY updated_at DESC 
                LIMIT 1
            """
            result = query(sql_no_active, (system_user_id,))
            logger.info(f"📊 不带 is_active 条件的查询结果: {result}")
        
        if result and len(result) > 0:
            logger.info(f"✅ 找到绑定账号: {result[0]['xiaomi_username']}, is_active={result[0].get('is_active')}")
            return BindingStatusResponse(
                is_bound=True,
                username=result[0]["xiaomi_username"],
                bound_at=str(result[0]["created_at"])
            )
        
        logger.error(f"❌ 完全未找到绑定账号，system_user_id={system_user_id}")
        return BindingStatusResponse(is_bound=False)
        
    except Exception as e:
        logger.error(f"❌ check_binding_status error: {e}", exc_info=True)
        return BindingStatusResponse(is_bound=False)


@router.get("/devices")
async def get_xiaomi_devices(system_user_id: int, server: str = "cn"):
    """
    获取用户的米家设备列表（通过 MCP 服务）
    需要传入 system_user_id 参数
    返回所有家庭的所有设备信息
    """
    try:
        # 导入 MCP 设备服务
        from services.mcp_device_service import get_mcp_device_service
        
        logger.info(f"📡 通过 MCP 服务获取用户 {system_user_id} 的设备列表")
        
        # 获取 MCP 服务实例
        mcp_service = get_mcp_device_service()
        
        # 调用 MCP 服务获取设备
        result = await mcp_service.get_user_devices(system_user_id, server)
        
        # 检查 MCP 服务是否可用
        if result is None:
            logger.error("❌ MCP 服务返回 None")
            raise HTTPException(
                status_code=503, 
                detail="❌ 设备查询MCP服务不可用"
            )
        
        # 检查是否成功
        if not result.get("success"):
            error_message = result.get("message", "获取设备失败")
            
            # 如果是MCP服务相关的错误，返回503状态码
            if "MCP" in error_message or "未部署" in error_message or "未安装" in error_message:
                raise HTTPException(status_code=503, detail=error_message)
            
            # 其他错误（如未绑定账号）返回400状态码
            raise HTTPException(status_code=400, detail=error_message)
        
        # 转换为旧格式以保持 API 兼容性
        return {
            "code": 0,
            "message": "success",
            "result": {
                "server": result.get("server", server),
                "total_homes": result.get("total_homes", 0),
                "total_devices": result.get("total_devices", 0),
                "homes": result.get("homes", []),
                "devices": result.get("devices", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_xiaomi_devices error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


async def get_xiaomi_devices_legacy(system_user_id: int, server: str = "cn"):
    """
    获取用户的米家设备列表（传统方式，作为备用）
    直接调用小米云 API
    """
    try:
        # 查询用户的激活凭证
        sql = """
            SELECT service_token, ssecurity, xiaomi_user_id, server
            FROM xiaomi_account 
            WHERE system_user_id = %s AND is_active = 1
            ORDER BY updated_at DESC 
            LIMIT 1
        """
        result = query(sql, (system_user_id,))
        
        if not result or len(result) == 0:
            raise HTTPException(status_code=404, detail="未找到小米账号绑定信息，请先绑定小米账号")
        
        credentials = result[0]
        
        # 创建临时connector
        connector = XiaomiCloudConnector("", "")
        connector._serviceToken = credentials["service_token"]
        connector._ssecurity = credentials["ssecurity"]
        connector.userId = credentials["xiaomi_user_id"]
        
        # 使用传入的server或数据库中的server
        current_server = server or credentials.get("server", "cn")
        
        # 获取所有家庭
        all_homes = []
        homes_result = connector.get_homes(current_server)
        
        if homes_result and homes_result.get("code") == 0:
            for h in homes_result['result']['homelist']:
                all_homes.append({
                    'home_id': h['id'],
                    'home_name': h.get('name', '未命名家庭'),
                    'home_owner': connector.userId
                })
        
        # 获取共享的家庭
        dev_cnt_result = connector.get_dev_cnt(current_server)
        if dev_cnt_result and dev_cnt_result.get("code") == 0:
            share_families = dev_cnt_result.get("result", {}).get("share", {}).get("share_family", [])
            for h in share_families:
                all_homes.append({
                    'home_id': h['home_id'],
                    'home_name': h.get('home_name', '共享家庭'),
                    'home_owner': h['home_owner']
                })
        
        # 获取每个家庭的设备
        all_devices = []
        for home in all_homes:
            devices_result = connector.get_devices(current_server, home['home_id'], home['home_owner'])
            
            if devices_result and devices_result.get("code") == 0:
                device_info = devices_result.get("result", {}).get("device_info", [])
                
                for device in device_info:
                    device_data = {
                        "home_id": home['home_id'],
                        "home_name": home['home_name'],
                        "name": device.get("name", "未命名设备"),
                        "did": device.get("did", ""),
                        "model": device.get("model", ""),
                        "token": device.get("token", ""),
                        "mac": device.get("mac", ""),
                        "localip": device.get("localip", ""),
                        "parent_id": device.get("parent_id", ""),
                        "parent_model": device.get("parent_model", ""),
                        "show_mode": device.get("show_mode", 0),
                        "isOnline": device.get("isOnline", False),
                    }
                    all_devices.append(device_data)
        
        return {
            "code": 0,
            "message": "success",
            "result": {
                "server": current_server,
                "total_homes": len(all_homes),
                "total_devices": len(all_devices),
                "homes": all_homes,
                "devices": all_devices
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_xiaomi_devices_legacy error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.post("/manual/bind", response_model=LoginStepResponse)
async def manual_bind_credentials(request: ManualCredentialsRequest):
    """
    手动输入小米凭证并绑定
    用户通过抓包获取 _ssecurity、userId、_cUserId、serviceToken 参数
    通过获取设备列表来验证凭证是否有效
    """
    try:
        # 创建临时的 connector 用于验证凭证
        # 使用虚拟的用户名和密码，因为我们直接使用提供的凭证
        connector = XiaomiCloudConnector("", "")
        
        # 设置手动提供的凭证
        connector._ssecurity = request.ssecurity
        connector.userId = request.userId
        connector._cUserId = request.cUserId
        connector._serviceToken = request.serviceToken
        
        # 尝试获取设备数量来验证凭证是否有效
        logger.info(f"验证用户 {request.system_user_id} 的小米凭证...")
        result = connector.get_dev_cnt(request.server)
        
        if result and result.get("code") == 0:
            # 凭证有效，保存到数据库
            logger.info(f"凭证验证成功: {result}")
            await save_xiaomi_credentials(
                system_user_id=request.system_user_id,
                xiaomi_username=request.xiaomi_username,
                service_token=request.serviceToken,
                ssecurity=request.ssecurity,
                xiaomi_user_id=request.userId,
                server=request.server
            )
            
            device_count = result.get("result", {})
            return LoginStepResponse(
                session_id="manual_bind",
                status="success",
                message=f"绑定成功！检测到 {device_count.get('own_cnt', 0)} 个设备",
                data={
                    "device_count": device_count
                }
            )
        else:
            # 凭证无效
            error_msg = "凭证验证失败"
            if result:
                error_msg = f"凭证验证失败: {result.get('message', '未知错误')}"
            logger.warning(f"凭证验证失败: {result}")
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"manual_bind_credentials error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


async def save_xiaomi_credentials(system_user_id: int, xiaomi_username: str, 
                                   service_token: str, ssecurity: str, 
                                   xiaomi_user_id: str, server: str):
    """
    保存小米账号凭证到 xiaomi_account 表
    一个系统用户只能绑定一个小米账号
    
    MySQL: 先禁用旧账号（is_active=0），再插入新账号（is_active=1）
    StarRocks: DUPLICATE KEY 表不支持 UPDATE，直接插入新记录，查询时取最新的激活记录
    """
    try:
        import time
        import random
        
        # 获取数据库类型
        db_type = get_db_type()
        
        if db_type == 'mysql':
            # MySQL: 先将该用户的所有旧账号设置为未激活
            update_sql = """
                UPDATE xiaomi_account 
                SET is_active = 0 
                WHERE system_user_id = %s
            """
            insert(update_sql, (system_user_id,))
            
            # 然后插入新的激活账号
            insert_sql = """
                INSERT INTO xiaomi_account 
                (system_user_id, xiaomi_username, service_token, ssecurity, xiaomi_user_id, server, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
            """
            insert(insert_sql, (system_user_id, xiaomi_username, service_token, ssecurity, xiaomi_user_id, server))
            logger.info(f"[MySQL] 用户 {system_user_id} 成功绑定小米账号: {xiaomi_username}")
            
        else:  # starrocks 或其他
            # StarRocks: DUPLICATE KEY 表不支持 UPDATE
            # 直接插入新记录（is_active=1），查询时取最新的激活记录
            credential_id = int(time.time() * 1000) + random.randint(1000, 9999)
            insert_sql = """
                INSERT INTO xiaomi_account 
                (id, system_user_id, xiaomi_username, service_token, ssecurity, xiaomi_user_id, server, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
            """
            insert(insert_sql, (credential_id, system_user_id, xiaomi_username, service_token, ssecurity, xiaomi_user_id, server))
            logger.info(f"[StarRocks] 用户 {system_user_id} 成功绑定小米账号: {xiaomi_username}")
        
    except Exception as e:
        logger.error(f"save_xiaomi_credentials error: {e}")
        raise


@router.delete("/unbind")
async def unbind_xiaomi_account(system_user_id: int):
    """
    解绑小米账号

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
                UPDATE xiaomi_account 
                SET is_active = 0 
                WHERE system_user_id = %s
            """
            update(update_sql, (system_user_id,))
        else:
            # StarRocks: 由于是DUPLICATE KEY表，不支持DELETE，插入一条标记删除的记录
            logger.warning("StarRocks不支持DELETE，请手动处理或在查询时过滤")

        logger.info(f"✅ 用户 {system_user_id} 已解绑小米账号")
        return {"status": "success", "message": "小米账号已解绑"}

    except Exception as e:
        logger.error(f"解绑小米账号失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解绑失败: {str(e)}")
