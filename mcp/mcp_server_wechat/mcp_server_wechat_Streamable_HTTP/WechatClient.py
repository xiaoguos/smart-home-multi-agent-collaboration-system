import json
import re
import os
import datetime
import logging
from typing import Optional, List, Union, Callable, Awaitable

import pyautogui
import time
from pywechat import Systemsettings, NotFolderError, Tools, NoChatHistoryError
from pywechat.WechatAuto import Messages

from pywinauto import mouse


class WeChatClient:
    """
    微信客户端（支持流式进度反馈）
    负责微信聊天记录获取和消息发送功能
    """

    def __init__(self, default_folder_path: Optional[str] = None):
        """
        初始化微信客户端

        参数:
        - default_folder_path: 默认保存聊天记录的文件夹路径
        """
        self.default_folder_path = default_folder_path
        self.logger = logging.getLogger(__name__)
        if self.default_folder_path:
            try:
                os.makedirs(self.default_folder_path, exist_ok=True)
            except Exception as e:
                self.logger.error(f"创建默认文件夹失败: {self.default_folder_path}, 错误: {e}")

    async def get_chat_history_by_date(
        self,
        friend: str,
        target_date: str,
        folder_path: str = None,
        search_pages: int = 5,
        wechat_path: str = None,
        is_maximize: bool = False,
        close_wechat: bool = True,
        scroll_delay: float = 0.01,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        获取特定日期的微信聊天记录（支持流式进度反馈）

        参数:
        - friend: 好友或群聊备注或昵称
        - target_date: 目标日期，格式为"YY/M/D"，如"25/3/22"
        - folder_path: 保存聊天记录的文件夹路径
        - search_pages: 搜索好友时翻页次数
        - wechat_path: 微信可执行文件路径
        - is_maximize: 是否最大化窗口
        - close_wechat: 完成后是否关闭微信
        - scroll_delay: 翻页延迟时间(秒)
        - progress_callback: 进度回调函数（用于流式推送）
        返回:
        - 聊天记录的JSON字符串
        """
        if folder_path is None:
            folder_path = self.default_folder_path

        if folder_path:
            folder_path = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', folder_path)
            if not Systemsettings.is_dirctory(folder_path):
                raise NotFolderError(r'给定路径不是文件夹!无法保存聊天记录,请重新选择文件夹！')

        # 解析日期
        try:
            match = re.match(r'(\d{2})/(\d{1,2})/(\d{1,2})', target_date)
            if match:
                year, month, day = map(int, match.groups())
                target_datetime = datetime.datetime(2000 + year, month, day)
            else:
                raise ValueError(f'日期格式不正确: {target_date}, 应为"YY/M/D"格式，如"25/3/22"')
        except Exception as e:
            raise ValueError(f'日期解析错误: {e}')

        def parse_date(date_str):
            """解析微信日期格式为datetime对象"""
            try:
                today = datetime.datetime.now().date()

                match = re.match(r'(\d{2})/(\d{1,2})/(\d{1,2})', date_str)
                if match:
                    year, month, day = map(int, match.groups())
                    return datetime.datetime(2000 + year, month, day)

                if "昨天" in date_str:
                    yesterday = today - datetime.timedelta(days=1)
                    return datetime.datetime.combine(yesterday, datetime.time())

                if "星期" in date_str:
                    weekday_map = {
                        "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3,
                        "星期五": 4, "星期六": 5, "星期日": 6, "星期天": 6
                    }

                    for weekday_str, weekday_num in weekday_map.items():
                        if weekday_str in date_str:
                            current_weekday = today.weekday()
                            days_diff = weekday_num - current_weekday

                            if days_diff > 0:
                                days_diff -= 7

                            target_date_calc = today + datetime.timedelta(days=days_diff)
                            return datetime.datetime.combine(target_date_calc, datetime.time())

                if re.match(r'^\d{1,2}:\d{2}$', date_str):
                    return datetime.datetime.combine(today, datetime.time())

                return None
            except Exception as e:
                self.logger.error(f"日期解析错误: {date_str}, {e}")
                return None

        def get_info(contentList):
            """获取当前页面的聊天信息"""
            content = []
            messages = contentList.children(title='', control_type='ListItem')
            who = [message.descendants(control_type='Text')[0].window_text() for message in messages]
            time_list = [message.descendants(control_type='Text')[1].window_text() for message in messages]
            for message in messages:
                if message.window_text() == '[图片]':
                    content.append('图片消息')
                elif '视频' in message.window_text():
                    content.append('视频消息')
                elif message.window_text() == '[动画表情]':
                    content.append('动画表情')
                elif message.window_text() == '[文件]':
                    filename = message.descendants(control_type='Text')[2].texts()[0]
                    content.append(f'文件:{filename}')
                elif '[语音]' in message.window_text():
                    content.append('语音消息')
                else:
                    texts = message.descendants(control_type='Text')
                    texts = [text.window_text() for text in texts]
                    if '微信转账' in texts:
                        index = texts.index('微信转账')
                        content.append(f'微信转账:{texts[index - 2]}:{texts[index - 1]}')
                    else:
                        content.append(texts[2])
            chat_history = list(zip(who, time_list, content))
            return chat_history

        # 流式反馈：开始打开聊天记录窗口
        if progress_callback:
            await progress_callback(f"正在打开与 {friend} 的聊天记录窗口...")

        chat_history_window = Tools.open_chat_history(
            friend=friend,
            wechat_path=wechat_path,
            is_maximize=is_maximize,
            close_wechat=close_wechat,
            search_pages=search_pages
        )[0]
        rec = chat_history_window.rectangle()
        mouse.click(coords=(rec.right - 10, rec.bottom - 10))
        pyautogui.press('End')

        contentList = chat_history_window.child_window(title='全部', control_type='List')
        if not contentList.exists():
            chat_history_window.close()
            raise NoChatHistoryError(f'你还未与{friend}聊天,无法获取聊天记录')

        found_target_date = False
        search_count = 0
        found_earlier_date = False

        self.logger.info(f"开始查找日期: {target_date}")
        if progress_callback:
            await progress_callback(f"开始查找 {target_date} 的聊天记录...")

        # 查找目标日期
        while not found_target_date:
            info = get_info(contentList)

            if not info:
                break

            for record in info:
                _, time_str, _ = record
                msg_date = parse_date(time_str)
                if msg_date:
                    msg_date_obj = msg_date.date() if hasattr(msg_date, 'date') else msg_date
                    target_date_obj = target_datetime.date() if hasattr(target_datetime, 'date') else target_datetime

                    if msg_date_obj == target_date_obj:
                        found_target_date = True
                        break
                    elif msg_date_obj < target_date_obj:
                        found_earlier_date = True
                        if not found_target_date:
                            break

            if found_target_date or (found_earlier_date and not found_target_date):
                break

            pyautogui.keyDown('pageup', _pause=False)
            if scroll_delay > 0:
                time.sleep(scroll_delay)

            search_count += 1
            if search_count % 10 == 0:
                msg = f"正在查找中，已翻页 {search_count} 次..."
                self.logger.warning(msg)
                if progress_callback:
                    await progress_callback(msg)

        if not found_target_date:
            chat_history_window.close()
            self.logger.warning(f"未找到{target_date}的聊天记录，共翻页{search_count}次")
            if progress_callback:
                await progress_callback(f"未找到 {target_date} 的聊天记录（共翻页 {search_count} 次）")
            return json.dumps([], ensure_ascii=False, indent=4)

        self.logger.info(f"开始收集{target_date}的聊天记录")
        if progress_callback:
            await progress_callback(f"找到目标日期！开始收集聊天记录...")

        pyautogui.press('End')

        collect_count = 0
        target_messages = []
        first_date_found = False
        date_completed = False

        # 收集聊天记录
        while not date_completed:
            info = get_info(contentList)

            if not info:
                break

            current_page_has_target = False
            page_has_earlier_date = False

            for record in info:
                _, time_str, _ = record
                msg_date = parse_date(time_str)

                if msg_date:
                    msg_date_obj = msg_date.date() if hasattr(msg_date, 'date') else msg_date
                    target_date_obj = target_datetime.date() if hasattr(target_datetime, 'date') else target_datetime

                    if msg_date_obj == target_date_obj:
                        first_date_found = True
                        current_page_has_target = True
                        target_messages.append(record)
                    elif msg_date_obj < target_date_obj and first_date_found:
                        page_has_earlier_date = True

            if not current_page_has_target and page_has_earlier_date and first_date_found:
                self.logger.info(f"已收集完{target_date}的所有聊天记录")
                if progress_callback:
                    await progress_callback(f"已收集完所有聊天记录，共 {len(target_messages)} 条")
                break

            # 继续向上翻页
            pyautogui.keyDown('pageup', _pause=False)
            if scroll_delay > 0:
                time.sleep(scroll_delay)

            collect_count += 1
            if collect_count % 10 == 0:
                msg = f"已收集 {len(target_messages)} 条消息，继续查找..."
                self.logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)

        pyautogui.press('End')

        target_messages.reverse()

        formatted_messages = []
        for index, record in enumerate(target_messages):
            sender, time_str, message = record
            formatted_messages.append({
                "index": index,
                "发送者": sender,
                "时间": time_str,
                "消息": message
            })

        chat_history_json = json.dumps(formatted_messages, ensure_ascii=False, indent=4)

        # 保存文件
        if folder_path:
            safe_date = target_date.replace('/', '-')
            json_path = os.path.abspath(os.path.join(folder_path, f'与{friend}的{safe_date}聊天记录.json'))
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(chat_history_json)
            self.logger.info(f"已保存JSON到: {json_path}")
            if progress_callback:
                await progress_callback(f"已保存到: {json_path}")

        chat_history_window.close()

        if not formatted_messages:
            self.logger.warning(f"未找到{target_date}的聊天记录")
        else:
            result_msg = f"成功获取 {len(formatted_messages)} 条聊天记录！"
            self.logger.info(result_msg)
            if progress_callback:
                await progress_callback(result_msg)

        return chat_history_json

    async def send_message_to_friend(
        self,
        friend: str,
        message: str,
        search_pages: int = 0,
        delay: float = 1.0,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        向单个好友发送单条消息

        参数:
        - friend: 好友或群聊备注或昵称
        - message: 要发送的消息
        - search_pages: 搜索好友时翻页次数
        - progress_callback: 进度回调函数

        返回:
        - 发送结果
        """
        try:
            if progress_callback:
                await progress_callback(f"正在向 {friend} 发送消息...")

            Messages.send_messages_to_friend(
                friend=friend,
                messages=[message],
                delay=delay,
                search_pages=search_pages
            )

            if progress_callback:
                await progress_callback(f"消息已成功发送给 {friend}")

            return {"status": "success", "message": f"消息已发送给 {friend}"}
        except Exception as e:
            error_msg = f"发送失败: {str(e)}"
            if progress_callback:
                await progress_callback(error_msg)
            return {"status": "error", "message": f"发送消息失败: {str(e)}"}

    async def send_messages_to_friend(
        self,
        friend: str,
        messages: List[str],
        search_pages: int = 0,
        delay: float = 1.0,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        向单个好友发送多条消息

        参数:
        - friend: 好友或群聊备注或昵称
        - messages: 要发送的消息列表
        - search_pages: 搜索好友时翻页次数
        - progress_callback: 进度回调函数

        返回:
        - 发送结果
        """
        try:
            if progress_callback:
                await progress_callback(f"正在向 {friend} 发送 {len(messages)} 条消息...")

            Messages.send_messages_to_friend(
                friend=friend,
                messages=messages,
                search_pages=search_pages,
                delay=delay
            )

            if progress_callback:
                await progress_callback(f"已成功向 {friend} 发送 {len(messages)} 条消息")

            return {"status": "success", "message": f"已向 {friend} 发送 {len(messages)} 条消息"}
        except Exception as e:
            error_msg = f"发送失败: {str(e)}"
            if progress_callback:
                await progress_callback(error_msg)
            return {"status": "error", "message": f"发送消息失败: {str(e)}"}

    async def send_message_to_friends(
        self,
        friends: List[str],
        message: Union[str, List[str]],
        delay: float = 1.0,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        向多个好友发送消息

        参数:
        - friends: 好友或群聊备注或昵称列表
        - message: 要发送的消息或针对每个好友的消息列表
        - progress_callback: 进度回调函数

        返回:
        - 发送结果
        """
        try:
            if progress_callback:
                await progress_callback(f"正在向 {len(friends)} 位好友发送消息...")

            Messages.send_message_to_friends(
                friends=friends,
                message=message,
                delay=delay
            )

            if progress_callback:
                await progress_callback(f"已成功向 {len(friends)} 位好友发送消息")

            return {"status": "success", "message": f"已向 {len(friends)} 位好友发送消息"}
        except Exception as e:
            error_msg = f"❌ 发送失败: {str(e)}"
            if progress_callback:
                await progress_callback(error_msg)
            return {"status": "error", "message": f"发送消息失败: {str(e)}"}

