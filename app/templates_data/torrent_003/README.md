# Alist-Magnet-Bot-Render

一个通过 Telegram 控制 Alist 离线下载的磁力搜索与推送机器人。

本项目基于群友 Patty 的 Python 脚本，由群友 misaka 增强了垃圾清理功能，群友 0721 用 Go 语言重构并提供了适用于 Render 的镜像。

---

## 🚀 功能简介
- 支持 Telegram 控制磁力链接搜索与推送到 Alist 离线下载目录
- 可对接任意公开搜索 API（默认已配置）
- 支持垃圾文件清理指令（如 `/clean`）

---

## ☁️ Render 部署 ThunderXBot 教程

### 步骤 1：注册 / 登录 Render
- 打开 [https://render.com](https://render.com)
- 使用 GitHub 账号或邮箱注册 / 登录

---

### 步骤 2：创建 Web Service

1. 登录后点击 `New` → `Web Service`
2. 选择 `Existing Image`
3. 填写以下信息：

| 项目         | 内容 |
|--------------|------|
| **Docker Image** | `mikehand888/jav-telegram-bot:latest` |
| **Service Name** | 自定义，例如 `thunderxbot` |
| **Region**       | 建议选择靠近你用户的区域，如 `Singapore` |

---

### 步骤 3：配置环境变量

在 `Environment Variables` 一栏填入以下内容：
## 环境变量
  | 变量名       | 变量内容  |默认值|说明|
  | ------------ | ------   |-----|---|
  |TELEGRAM_TOKEN|你的机器人Token|
  |ALIST_BASE_URL|`https://你的Alist地址`||不带/结尾|
  |ALIST_TOKEN|你的AlistToken|
  |ALIST_OFFLINE_DIRS|/你的下载目录||可以多个下载目录，用英文逗号分开|
  |JAV_SEARCH_APIS|`https://api.wwlww.org/v1/avcode/`|
  |ALLOWED_USER_IDS|你的tg id||多个ID,用英文逗号分开|
  |CLEAN_INTERVAL_MINUTES|间隔多少分钟自动清理文件|60（分钟）|
  |SIZE_THRESHOLD|自动清理小于多少M的文件|150（MB）|
  |PREFERRED_KEYWORDS|-C,-C-,ch,字幕||关键词不区分大小写（如 -C 会匹配 -c 或 -C），如果不需要优先级关键词可留空。|
  |CUSTOM_CATEGORIES|分类1:关键词1,关键词2;分类2:关键词3,关键词4||自定义分类，番号匹配完毕之后匹配自定义分类，可留空。|
  |SYSTEM_FOLDERS|/system/folder1,/system/folder2||这些文件夹在清理过程中将被保护，不会被删除或修改|
  |CLEAN_BATCH_SIZE||500|
  |CLEAN_REQUEST_INTERVAL||0.2|
  |MAX_CONCURRENT_REQUESTS||20|
  |HTML_URL|内容为自定义静态网页的raw文件链接，不填静态网页为Hello world!|

✅ 填写完毕点击 `Deploy` 即可部署。

📌 **如果提示绑定信用卡：**
使用干净的美国家宽节点全局代理，我实测一次成功。

---

### 步骤 4：设置保活（可选）

Render 免费服务有休眠限制，可以通过第三方保活项目实现持续运行。

推荐项目：[Auto-keep-online by eooce](https://github.com/eooce/Auto-keep-online)

👉 部署后访问项目分配给你的域名，即可自动保持 Render 服务在线。

uptime,哪吒面板等工具增加监控任务也可以

---

## 🐳 Docker 通用部署方式

群友 john Nate 提供了适用于任意 Docker 平台的镜像：

https://hub.docker.com/r/hide3110/jav-telegram-bot

---

## 🧩 其他平台部署说明

如果你在 Render 上无法成功部署：

- 可以在 Releases 中下载适用于其他平台（如 Minecraft 容器、Python、java脚本环境）的版本  
- 每个版本的压缩包中都包含说明文件，按需配置即可使用

---

## 🙏 致谢

感谢以下群友对本项目的贡献与支持：

- [**群友Patty**](https://t.me/joinchat/GZxTslH80phQbAR0bglMMA)：提供原始 Python 脚本  
- **misaka**：增强 `/clean` 指令，实现垃圾文件清理功能  
- **0721**：用 Go 语言重写项目，并提供 Render 镜像与多平台 Docker 镜像支持
- [**月**](https://github.com/yyyr-otz)：重新编译支持java
- [**Lmentor**]：增加了初版脚本的很多功能。
- [**john Nate**](https://hub.docker.com/r/hide3110/jav-telegram-bot)：提供通用Docker部署镜像
- [**Mike HanD**](https://github.com/Kaiser-Ryo/jav-telegram-bot)：编译了render镜像
- [**eooce**](https://github.com/eooce)：提供 Auto-keep-online 项目，实现 Render 自动保活

> 📌 本教程由本人整理，经作者同意整合发布，内容仅供参考，如有问题自行解决，各种AI或者群里问。
