import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib import parse as url_parse

import requests.utils
from flask import (Flask, jsonify, make_response, redirect, render_template,
                   request)
from requests import Session
from requests.adapters import HTTPAdapter
from waitress import serve

from utils.config_vars import (BOT_USERNAME, CALLBACK_URL, bgm, config, redis,
                               sql)

# 异步线程池
executor = ThreadPoolExecutor()
lock = threading.RLock()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

# 错误访问
@app.route("/")
def index():
    return render_template("error.html")  # 发生错误


@app.route("/health")
def health():
    return "OK"  # 健康检查


@app.route("/web_index")
def web_index():
    try:
        state = request.args.get("state")
        if not state: return render_template("error.html")
        redis_data = redis.get("oauth:" + state)
        if not redis_data: return render_template("expired.html")
        params = json.loads(redis_data)
        check = sql.inquiry_user_data(params["tg_id"])
        if check: return render_template("verified.html")
        b64_captcha, cookie = bgm.web_authorization_captcha()
        cookie_dict: dict = requests.utils.dict_from_cookiejar(cookie)
        resp = make_response(render_template("webindex.html", b64_captcha=b64_captcha))
        resp.set_cookie("chii_sec_id", cookie_dict["chii_sec_id"])
        resp.set_cookie("chii_sid", cookie_dict["chii_sid"])
        return resp
    except Exception as e:
        logging.error(f"[E] web_index: {e}")
        return render_template("error.html")


@app.route("/web_login", methods=["POST"])
def web_login():
    try:
        cookie = request.headers.get("cookie")
        email, password = request.json.get("email"), request.json.get("password")
        captcha, state = request.json.get("captcha"), request.json.get("state")
        if not state or not cookie: return "缺少必要参数", 403
        redis_data = redis.get("oauth:" + state)
        if not redis_data: return "您的请求已过期，请重新私聊 Bot 并发送 /start", 403
        params = json.loads(redis_data)
        check = sql.inquiry_user_data(params["tg_id"])
        if check: return "你已验证成功，无需重复验证", 403
        back_check, back_data = bgm.web_authorization_login(cookie, email, password, captcha)
        if not back_check: return back_data, 400
        cookie_dict: dict = requests.utils.dict_from_cookiejar(back_data)
        cookie_str = cookie + "; " + "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
        code = bgm.web_authorization_oauth(cookie_str)
        if not code: return "Web 授权失败，请重试", 400
        back_oauth = bgm.oauth_authorization_code(code)
        sql.insert_user_data(params["tg_id"], back_oauth["user_id"], back_oauth["access_token"], back_oauth["refresh_token"], cookie_str)
        return jsonify({"BotUsername": config["BOT_USERNAME"], "Params": params["param"]}), 200
    except Exception as e:
        logging.error(f"[E] web_login: {e}")
        return "出错了，请重试", 403


@app.route("/oauth_index")
def oauth_index():
    try:
        state = request.args.get("state")
        if not state: return render_template("error.html")
        redis_data = redis.get("oauth:" + state)
        if not redis_data: return render_template("expired.html")
        params = json.loads(redis_data)
        check = sql.inquiry_user_data(params["tg_id"])
        if check: return render_template("verified.html")
        USER_AUTH_URL = "https://bgm.tv/oauth/authorize?" + url_parse.urlencode(
                {
                    "client_id": config["BGM"]["APP_ID"],
                    "response_type": "code",
                    "redirect_uri": CALLBACK_URL,
                    "state": state,
                }
            )
        return redirect(USER_AUTH_URL)
    except Exception as e:
        logging.error(f"[E] oauth_index: {e}")
        return render_template("error.html")


@app.route("/oauth_callback")
def oauth_callback():
    try:
        code, state = request.args.get("code"), request.args.get("state")
        if not code or not state: return render_template("error.html")
        redis_data = redis.get("oauth:" + state)
        if not redis_data: return render_template("expired.html")
        params = json.loads(redis_data)
        back_oauth = bgm.oauth_authorization_code(code)
        sql.insert_user_data(params["tg_id"], back_oauth["user_id"], back_oauth["access_token"], back_oauth["refresh_token"])
        redis.delete("oauth:" + state)
        return redirect(f"https://t.me/{config['BOT_USERNAME']}?start={params['param']}")
    except Exception as e:
        logging.error(f"[E] oauth_callback: {e}")
        return render_template("error.html")


@app.route("/sub")
def sub():
    type = request.values.get("type")
    subject_id = request.values.get("subject_id")
    bgm_id = request.values.get("user_id")
    if not (type and subject_id and bgm_id):
        logging.error(f"[E] sub: 缺少参数 {type} {subject_id} {bgm_id}")
        resu = {"code": 400, "message": "参数不能为空！"}
        return jsonify(resu), 400
    if int(type) == 1:
        is_subscribed = sql.check_subscribe(subject_id, None, bgm_id)
        logging.info(f"[I] sub: 查询 用户 {bgm_id} {'已订阅' if is_subscribed else '未订阅'} {subject_id}")
        return {"status": 1 if is_subscribed else 0}, 200
    elif int(type) == 2:
        is_subscribed = sql.check_subscribe(subject_id, None, bgm_id)
        if is_subscribed:
            sql.delete_subscribe_data(subject_id, None, bgm_id)
            logging.info(f"[I] sub: 用户 {bgm_id} 取消订阅 {subject_id}")
            resu = {"code": 200, "message": "已取消订阅"}
            return jsonify(resu), 200
        else:
            logging.info(f"[E] sub: 用户 {bgm_id} 未订阅过 {subject_id}")
            resu = {"code": 401, "message": "该用户未订阅此条目"}
            return jsonify(resu), 401


@app.route("/push")
def push():
    from telebot import TeleBot
    from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
    logging.info(f"[I] push: 收到推送请求 {request.full_path}")
    video_id = request.values.get("vid")
    subject_id = request.values.get("subject_id")
    subject_name = request.values.get("title")
    volume = request.values.get("volume")
    if subject_id and video_id:
        subscribe_list = sql.inquiry_subscribe_data(subject_id)
        if subscribe_list:
            text = (
                f"*🌸 #{subject_name} [*[{volume}](https://cover.bangumi.online/episode/{video_id}.png)*] 更新咯～*\n\n"
                f"[>>🍿 前往观看](https://bangumi.online/watch/{video_id}?s=bgmbot)\n"
            )
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(text="取消订阅", callback_data=f"unaddsub|{subject_id}"),
                InlineKeyboardButton(text="查看详情", url=f"t.me/{BOT_USERNAME}?start={subject_id}")
            )
        else:
            logging.info(f"[I] push: {subject_id} 无订阅用户")
            resu = {"code": 200, "message": f"{subject_id} 无订阅用户"}
            return jsonify(resu), 200
        lock.acquire() # 线程加锁
        success_count = 0 # 成功计数器
        failed_count = 0 # 不成功计数器
        bot = TeleBot(config["BOT_TOKEN"], parse_mode="Markdown")
        for i, user in enumerate(subscribe_list):
            try:
                bot.send_message(chat_id=user, text=text, reply_markup=markup)
                success_count += 1
            except: failed_count += 1
            if (i + 1) % 30 == 0: time.sleep(1)
        logging.info(f"[I] push: 推送成功 {success_count} 条，失败 {failed_count} 条")
        resu = {"code": 200, "message": f"推送:成功 {success_count} 失败 {failed_count}"}
        lock.release() # 线程解锁
        return jsonify(resu), 200
    else:
        logging.error(f"[E] push: 缺少参数 {subject_id} {video_id}")
        resu = {"code": 400, "message": "参数不能为空！"}
        return jsonify(resu), 400


@app.before_request
def before():
    """中间件拦截器"""
    url = request.path  # 读取到当前接口的地址
    if url in ["/health", "/oauth_index", "/oauth_callback", "/web_index", "/web_login"]:
        pass
    elif re.findall(r"pma|db|mysql|phpMyAdmin|.env|php|admin|config|setup", url):
        logging.debug(f"[W] before: 拦截到非法请求 {request.remote_addr} -> {url}")
        fuck = {"code": 200, "message": "Fack you mather!"}
        return jsonify(fuck), 200
    elif request.headers.get("Content-Auth") != config["API_SERVER"]["AUTH_KEY"]:
        logging.debug(f"[W] before: 拦截访问 {request.remote_addr} -> {url}")
        resu = {"code": 403, "message": "你没有访问权限！"}
        return jsonify(resu), 200
    else:
        pass


def start_flask():
    serve(app, port=config["API_SERVER"]["POST"])


def start_api():
    executor.submit(start_flask)


def stop_api():
    executor.shutdown(wait=False)