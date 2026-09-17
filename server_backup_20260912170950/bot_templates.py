"""bot_templates.py — قوالب بوتات GitHub الحقيقية لمنصة TikZoom.

كل قالب = مجلد داخل app/template_repos/<id>/ يحتوي:
  - .tpl_manifest.json  (بيانات القالب: الاسم، الفئة، متطلبات التشغيل، متغيرات البيئة…)
  - ملفات البوت الفعلية (مشروع متعدد الملفات كامل من GitHub)

المتغيرات الإلزامية لكل بوت عند الإنشاء: BOT_TOKEN + ADMIN_ID
والمتغيرات الاختيارية تُعرَّف في manifest.optional_env مع قيم افتراضية.

قواعد القوالب المعتمدة (يتحقق منها خط الأنابيب قبل الاعتماد):
  - `python entry.py` يجب أن يبدأ long-polling مباشرة
  - التوكن من os.environ BOT_TOKEN
  - معرّف الأدمن من os.environ ADMIN_ID
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

REPOS_DIR = Path(__file__).resolve().parent / "template_repos"

TEMPLATES: dict[str, dict] = {}


def _load_dir() -> None:
    TEMPLATES.clear()
    if not REPOS_DIR.is_dir():
        log.warning("template_repos dir missing: %s", REPOS_DIR)
        return
    for sub in sorted(REPOS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        mf = sub / ".tpl_manifest.json"
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("bad manifest %s: %s", mf, exc)
            continue
        tid = data.get("id") or sub.name
        entry = data.get("entry") or "bot.py"
        if not (sub / entry).is_file():
            # قالب بدون ملف الدخول يُتجاهل
            log.warning("template %s: entry missing: %s", tid, entry)
            continue
        TEMPLATES[tid] = {
            "id": tid,
            "name": data.get("name") or tid,
            "desc": data.get("desc") or "",
            "icon": data.get("icon") or "🤖",
            "category": data.get("category") or "أدوات",
            "entry": entry,
            "requirements": data.get("requirements") or [],
            "required_env": data.get("required_env") or [
                {"name": "BOT_TOKEN", "desc": "توكن البوت من @BotFather"},
                {"name": "ADMIN_ID", "desc": "معرّف الأدمن الرقمي"},
            ],
            "optional_env": data.get("optional_env") or [],
            "source": data.get("source") or "",
            "meta": data.get("meta") or {},
            "files_dir": str(sub),
            "code": None,  # توافق مع أي واجهة قديمة تتوقع حقل code
        }


_load_dir()


def reload_templates() -> int:
    """إعادة فحص مجلد القوالب (بعد نشر حزمة جديدة مثلاً)."""
    _load_dir()
    return len(TEMPLATES)


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)


def list_templates() -> list[tuple[str, dict]]:
    return sorted(
        TEMPLATES.items(),
        key=lambda kv: (kv[1].get("category", ""), kv[1].get("name", "")),
    )
