<div align="center">

**بازیابیِ اسلاید، وایت‌برد و ویدیوی همگام از هر ضبطِ ادوبی کانکت — از جمله «وادانا»ی دانشگاه آزاد.**

<br />

[![CI](https://img.shields.io/github/actions/workflow/status/phoseinq/vadana-extractor/ci.yml?label=CI&logo=github&logoColor=white)](https://github.com/phoseinq/vadana-extractor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/phoseinq/vadana-extractor?label=release&color=2CA5E0&logo=github&logoColor=white)](https://github.com/phoseinq/vadana-extractor/releases)
[![Python](https://img.shields.io/badge/Python-3.11–3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/iau_archive_Bot)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<br />

[English](README.md) · **فارسی**

[▶️ رباتِ زنده](https://t.me/iau_archive_Bot) · [گزارشِ باگ](https://github.com/phoseinq/vadana-extractor/issues) · [درخواستِ قابلیت](https://github.com/phoseinq/vadana-extractor/issues)

</div>

<br />

<div align="center">

<img src="assets/gui.png" alt="اپِ دسکتاپِ وادانا اکسترکتور" width="560">

<sub><b>اپِ دسکتاپ</b> — ضبط را تحلیل کن، خروجی را انتخاب کن، استخراج</sub>

<br />
<br />

<table>
<tr>
<td align="center"><img src="assets/bot.png" alt="ربات تلگرام" height="260"><br /><sub><b>رباتِ تلگرام</b></sub></td>
<td align="center"><img src="assets/cli.png" alt="خط‌فرمان" height="260"><br /><sub><b>خط‌فرمانِ تعاملی</b></sub></td>
</tr>
</table>

</div>

<br />

<div dir="rtl" align="right">

## ✨ چی می‌گیری

جزوه و محتوای درسی، مستقیم از پکیجِ آفلاینِ خودِ ضبط — بدونِ اسکرین‌رکورد، بدونِ آپلودِ دوباره. برای سرورهای **وادانا**ی دانشگاه آزاد ساخته شده (همهٔ شعبه‌ها — `vadavc30`، `vadana14`، `vadana36`، …)، ولی ساختارِ پکیج استانداردِ ادوبی کانکت است، پس روی **هر سروری** کار می‌کند: فقط لینکِ کاملِ ضبط را بفرست.

- 📄 **فایل‌های اشتراکی** — همان PDFِ اصلِ اسلاید از Share pod، حتی وقتی دکمهٔ دانلود بسته بوده.
- 📝 **وایت‌برد ← PDF** — هر صفحهٔ تخته به‌صورتِ PDFِ تمیز، با خط‌های صاف‌شده. اگر استاد روی یک PDFِ اشتراکی نوشته باشد، همان صفحه پشتِ نوشته‌ها می‌ماند.
- 🎬 **ویدیوی همگام** — وایت‌برد + اشتراکِ صفحه + صدا روی یک تایم‌لاین.
- 🎧 **فقط صدا** — کلاسِ بی‌تصویر به‌صورتِ `m4a` یا `mp3` برمی‌گردد.
- 🖼️ **پیش‌نمایش و جزئیات** — هر فایل با تامبنیل و یک کپشنِ کوتاه می‌رسد (شناسه، تاریخ، حجم، مدت).
- 🤖 **سه راهِ اجرا** — رباتِ تلگرام، خط‌فرمانِ تعاملی، و اپِ دسکتاپِ دارک.
- 🇮🇷 **همه‌جا کار می‌کند** — روی سیستمِ شخصی یا سرورِ ایران بدونِ پروکسی؛ پروکسیِ ریورس فقط روی سرورِ خارج.

**یک لینکِ ضبط، سه خروجیِ ممکن:**

| می‌فرستی | می‌گیری |
| :-- | :-- |
| لینک + 📄 **فایل‌ها** | همان PDFهای اصلِ اسلاید (`Chapter 1.pdf`، …) |
| لینک + 📝 **وایت‌برد** | یک PDF از تخته — نوشته‌های استاد روی اسلایدها |
| لینک + 🎬 **ویدیو** | یک MP4: وایت‌برد + اشتراکِ صفحه + صدا، هماهنگ با صفحه‌ها |

<br />

## ⚡ شروعِ سریع — خط‌فرمانِ تعاملی

**پیش‌نیازها:** پایتون **۳.۱۱ تا ۳.۱۳** (گزینهٔ *Add to PATH* را بزن) · برای ویدیو/صدا هم `ffmpeg` (`winget install ffmpeg`).

```bash
git clone https://github.com/phoseinq/vadana-extractor
cd vadana-extractor
pip install -r requirements.txt
python cli/vadana.py          # Windows: just double-click vadana.bat
```

کاملاً راهنمایی‌شده است: لینکِ ضبط را بزن، خودش می‌گوید ضبط چه دارد (وایت‌برد / اسلاید / صدا)، بعد از منو یکی را انتخاب کن — **اسلاید PDF**، **وایت‌برد PDF**، **ویدیوی همگام**، یا **فقط صدا (m4a یا mp3)**. حلقه می‌زند، پس بدونِ اجرای دوباره می‌توانی چند خروجی — یا چند ضبط — بگیری. همه‌چیز در `out/` ذخیره می‌شود.

> معمولاً همین لینکِ ساده کافی است. اگر ضبطی به ورود نیاز داشت، لینکِ کامل همراه با مقدارِ `session=` را کپی کن (زود منقضی می‌شود).

<details><summary><b>دستورهای تک‌مرحله‌ای را ترجیح می‌دهی؟</b></summary>

<br />

```bash
python cli/download_slides.py "https://<connect-host>/<id>/"   # shared files
python cli/make_video.py "<url>"                               # synced video (audio-only -> .m4a)
python cli/make_video.py "<url>" --pages-only                  # board pages as a PDF
```
</details>

<br />

## 🖥️ اپِ دسکتاپ (محیطِ گرافیکیِ دارک)

پنجره را به ترمینال ترجیح می‌دهی؟ در **ویندوز** فقط روی **`vadana-gui.bat`** دوبار کلیک کن (بارِ اول وابستگیِ گرافیکی را خودش نصب می‌کند و برنامه باز می‌شود)؛ روی هر سیستمی:

```bash
pip install -r requirements-gui.txt
python gui/vadana_gui.py
```

لینک را بزن (دکمهٔ **Paste** هم هست، پس با کیبوردِ فارسی هم کار می‌کند)، **Analyze** را بزن تا محتوای ضبط را نشان دهد. بعد یکی از **Slides PDF / Whiteboard PDF / Video / Audio** را انتخاب کن، **کیفیتِ** ویدیو (720p / 1080p / 1440p / 4K) و **فریم‌ریت**، یا **فرمتِ** صدا (m4a / mp3) را بچین و **Extract** بزن — با **تخمینِ حجمِ زنده** همین‌طور که تنظیم می‌کنی.

تمِ دارک با آیکونِ خطی، **بررسیِ پیش‌نیازها** با نصبِ یک‌کلیکیِ موارد گم‌شده (ffmpeg + پکیج‌ها)، دکمهٔ **لغو**، **تلاشِ مجدد** هنگام خطا، **باکسِ فایل‌های خروجی** (نام، حجم، مسیر و «نمایش در پوشه»)، پیشرفتِ زنده، لاگِ روی صفحه و فایل (`out/vadana.log`)، و پنجرهٔ **About**. همه‌چیز در `out/` ذخیره می‌شود.

<br />

## 🤖 راه‌اندازیِ ربات

یک دستور روی سرور. می‌پرسد با داکر یا مستقیم، همه‌چیز را نصب می‌کند (ffmpeg، وابستگی‌ها، سرویسِ systemd و دستورِ `vadana`) و بعد قدمِ بعدی را نشان می‌دهد.

```bash
curl -fsSL https://raw.githubusercontent.com/phoseinq/vadana-extractor/main/install.sh | bash
```

> **داکر** ایمیجِ منتشرشدهٔ `ghcr.io/phoseinq/vadana-extractor:latest` را اجرا می‌کند (CI روی هر ریلیز پوش می‌کند)، پس نصبِ داکری — و `docker compose pull` — بدونِ build است؛ `build:` هم به‌عنوانِ fallback می‌ماند.

بعد `bot/.env` را پر کن (با `vadana env`، یا برای داکر دستی ویرایشش کن) و راه بینداز:

| متغیر | توضیح |
| :-- | :-- |
| `BOT_TOKEN` | توکن از [@BotFather](https://t.me/BotFather) — **اجباری** |
| `IRAN_PROXY` | پروکسیِ HTTP/SOCKS5، فقط روی سرورِ خارج؛ وگرنه خالی |
| `ADMINS` | آی‌دیِ کاربرها (با کاما) که اجازهٔ ساختِ ویدیو دارند |
| `STORAGE_CHANNEL` | آی‌دیِ چنلِ خصوصی برای کشِ فایل‌ها (ربات باید ادمین باشد) |
| `ALLOW_VIDEO` | `1` = ساختِ ویدیو برای همه؛ `0` = فقط ادمین |
| `AUDIO_DENOISE` | نویزگیریِ صدای ویدیو — یک زنجیرهٔ فیلترِ ffmpeg دلخواه، یا خالی برای خاموش‌کردن (پیش‌فرض روشن) |

**دستورِ `vadana`:**

| دستور | کار |
| :-- | :-- |
| `vadana` | منوی تعاملی |
| `files` / `whiteboard` / `video` | دانلودِ همان خروجی |
| `status` / `logs` | وضعیتِ سرویس / لاگِ زنده |
| `start` / `stop` / `restart` | کنترلِ سرویس |
| `update` | git pull + نصبِ مجدد + ری‌استارت |
| `env` | ویرایشِ `.env` و ری‌استارت |
| `uninstall` | حذفِ سرویس |

<br />

## ⚙️ چطور کار می‌کند

هر ضبط یک ZIPِ آفلاین در `/<id>/output/<id>.zip` دارد. اسناد اشتراکی از `downloadUrl`های داخلِ `mainstream.xml` می‌آیند؛ وایت‌برد رویدادهای بُرداریِ زمان‌دار در `ftcontent*.xml` است که بازپخش می‌شود تا تخته دوباره کشیده شود؛ صدا و اشتراکِ صفحه با offsetهای `indexstream.xml` روی تایم‌لاین می‌نشینند و با FFmpeg ترکیب می‌شوند.

<details><summary><b>معماری (برای مشارکت‌کننده‌ها)</b></summary>

<br />

ربات یک event loopِ `aiogram` است. هر مرحلهٔ سنگین (دانلود، رِندرِ وایت‌برد، FFmpeg) در یک تردِ کارگر با `asyncio.to_thread` اجرا می‌شود تا حلقه هیچ‌وقت بلاک نشود و به بقیه پاسخ‌گو بماند.

**هر کاربر یک کار.** هر درخواست یک `asyncio.Task` در `ACTIVE_TASKS[uid]` می‌شود؛ فرستادنِ لینکِ دوم وسطِ کار رد می‌شود («صبر کن یا لغو بزن»). لغو یک `asyncio.Event` را ست می‌کند که کار مدام چکش می‌کند، پس تمیز متوقف می‌شود و اسلاتش آزاد می‌شود.

**دو سمافور کلِ سرور را محدود می‌کنند** (نه per-user):

- `SLIDES_SEM = Semaphore(MAX_CONCURRENT)` — پیش‌فرض **۳** — دانلودِ فایل / وایت‌برد.
- `VIDEO_SEM = Semaphore(MAX_VIDEO_CONCURRENT)` — پیش‌فرض **۱** — ساختِ ویدیو، که گران‌ترین است (رِندر + انکود).

**دو نفر هم‌زمان ویدیو می‌سازند:** اولی `async with VIDEO_SEM:` تنها اسلات را می‌گیرد و اجرا می‌شود. دومی `VIDEO_SEM.locked()` را می‌بیند، پیامِ وضعیتش «ویدیوی دیگری در حال ساخت است — بعدی نوبتِ توست» می‌شود و پشتِ سمافور `await` می‌کند. asyncio منتظرها را به ترتیبِ ورود بیدار می‌کند، پس مثلِ صفِ FIFO رفتار می‌کند — کسی حذف نمی‌شود، فقط نوبتش می‌رسد.

**محدودیت و ضدِ اسپم:** کول‌داونِ per-user (`USER_COOLDOWN`، ۱۵ ثانیه) و سهمیهٔ روزانهٔ ویدیو (`MAX_VIDEO_PER_DAY`، ۳ برای غیرِادمین). یک `ThrottleMiddleware` (حدودِ ۱۰ آپدیت در پنجرهٔ ۸ ثانیه‌ای) سیل را *قبل از* هر هندلر می‌اندازد؛ ادمین‌ها معاف‌اند.

**کش همهٔ این‌ها را دور می‌زند.** هر نتیجهٔ آماده یک بار در چنلِ ذخیره آپلود و `file_id`ِ تلگرامش در `store.json` ذخیره می‌شود؛ درخواستِ تکراری فوری از همان‌جا می‌رسد — نه سمافوری می‌گیرد نه به سرورِ منبع دست می‌زند.

کجا را ببینی: `bot/bot.py` (هندلرها، سمافورها، پولرِ پیشرفت)، `vadana/connect.py` (احراز + دانلودِ پکیج)، `vadana/whiteboard.py` + `vadana/video.py` (بازسازی)، `vadana/slides.py` (فایل‌های اشتراکی).

</details>

<br />

## 🛰️ نودهای کارگر (اختیاری)

وقتی تنها اسلاتِ ویدیوی مستر پر است، می‌تواند ساختِ سنگین را روی mTLS به یک **نودِ کارگرِ** دور بسپارد تا فایلِ کمتری در صف بماند. نود فقط CPU و ffmpeg است — پروکسیِ ایران و توکنِ تلگرام ندارد؛ مستر پکیجِ ضبط را همراهِ PDFهای اشتراکی در یک باندل می‌فرستد، نود رِندر می‌کند و MP4 را برمی‌گرداند. **پیش‌فرض خاموش — بدونِ نود، مستر دقیقاً مثلِ قبل خودش همه‌چیز را می‌سازد.**

```bash
vadana node add mynode        # issue a node cert + print one enrollment bundle
vadana node status            # which nodes are connected right now
```

APIِ نود **خودکار** روشن می‌شود وقتی حداقل یک نود ثبت شده باشد (و با حذفِ آخرین نود خاموش). دستی: `vadana node on|off|auto`. سمتِ نود ریپوی جداست: **[vadana-node](https://github.com/phoseinq/vadana-node)** (worker + Docker، چند-ورکر با `--workers`).

| متغیر | توضیح |
| :-- | :-- |
| `NODE_API_ENABLE` | override: `1`/`0` روشن/خاموشِ اجباری؛ خالی = auto (روشن وقتی ≥۱ نود) |
| `NODE_API_PORT` | پورتِ mTLS که نودها وصل می‌شوند (پیش‌فرض `8443`) |
| `HEARTBEAT_TTL` | ثانیه‌هایی که یک نود از آخرین ping «زنده» حساب می‌شود (پیش‌فرض ۳۰) |
| `CLAIM_TTL` | ثانیه تا وقتی کارِ تحویل‌نشده به حالتِ محلی برگردد (پیش‌فرض ۱۲۰۰) |

<br />

## 🔌 API (اختیاری)

```bash
pip install -r requirements-api.txt
uvicorn cli.api:app --host 0.0.0.0 --port 8000
```

`POST /extract` با `{"url": "...", "kind": "files"}` یک zip از فایل‌ها برمی‌گرداند (یا با `"kind": "whiteboard"` همان PDFِ تخته).

<br />

## 🧪 تست

```bash
pip install -r requirements-dev.txt
pytest
```

</div>

<br />

---

<div align="center">

⭐ **اگر وقتت را ذخیره کرد، یک ستاره به ریپو بده.**

<sub>MIT · ساختهٔ <a href="https://github.com/phoseinq">phoseinq</a> · <a href="https://pvboy.dev">pvboy.dev</a></sub>

</div>
