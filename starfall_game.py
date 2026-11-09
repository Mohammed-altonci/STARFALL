# -*- coding: utf-8 -*-
"""
STARFALL - GALAXY ATTACK   (ستارفول: هجوم المجرة)
=================================================
لعبة فضائية بلغة بايثون + مكتبة pygame. كل شيء فيها مرسوم ومولّد بالكود:
لا صور ولا ملفات صوت خارجية.   التشغيل:  pip install pygame   ثم   python starfall.py

المزايا:
- 400 مرحلة طويلة (5 موجات + أعداء نخبة + كويكبات)، وكل 10 مراحل زعيم، و8 تصاميم زعماء بقدرات خاصة.
- 6 مركبات (منها مركبتان مميزتان) و10 أسلحة وطائرات مرافقة ومظاهر وألوان أثر المحرك.
- رسومات عام 2500: توهج Bloom وخطوط مسح وواجهة هولوغرامية وخلفية معركة بعيدة وصواعق أيونية.
- متجر من 7 صفحات و52 عنصراً: عملات عادية + كريستال نوفا (عملة مميزة تُشحن فقط).
- نظام مبيعات: حزم كريستال، حزمة مبتدئين، اشتراك VIP، تذكرة ستارفول (Battle Pass)، مكافأة يومية.
- حفظ تلقائي، لاعبان على نفس الجهاز، إعدادات الصوت والصعوبة وتغيير المفاتيح.

للنشر والربح: انظر PURCHASE_MODE و PLAY_BILLING_HOOK و PRODUCTS قرب بداية الملف،
وأداة المالك starfall_codegen.py (لا توزعها مع اللعبة) لتوليد أكواد الشحن.

التحكم (بعضها يمكن تغييره من الإعدادات):
  الحركة: الأسهم أو WASD     الدرع: Left Shift     السلاح الخاص: E     تبديل السلاح: Q
  القنبلة: X     المتجر: B     إيقاف مؤقت: P أو ESC     ملء الشاشة: F11
  لاعبان: اللاعب 1 = WASD ، اللاعب 2 = الأسهم + Right Shift + Right Ctrl
  الإطلاق تلقائي (يمكن إيقافه من الإعدادات، ثم المسافة / Enter)
  في المتجر: الأسهم للتنقل، Q و E أو TAB لتبديل الصفحة، Enter أو الأرقام 1-9 للشراء
"""
import pygame
import random
import math
import sys
import os
import json
import array
import hashlib
import hmac
import base64
import webbrowser
import time
import datetime
import importlib
from types import SimpleNamespace

# ================= التهيئة والإعدادات الأساسية =================
WIDTH, HEIGHT, FPS = 900, 700, 60
MAX_LEVEL = 400
BOSS_EVERY = 10
TAU = math.tau

# تهيئة pygame والصوت (قناة واحدة mono بتردد 22050 هرتز)
ANDROID = ("ANDROID_ARGUMENT" in os.environ or
           hasattr(sys, "getandroidapilevel") or
           sys.platform == "android")
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
SOUND_ENABLED = True
SR, CH = 22050, 1
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(22050, -16, 1, 512)
    _mi = pygame.mixer.get_init()
    SR, _fmt, CH = _mi
    if _fmt != -16:
        SOUND_ENABLED = False
    else:
        pygame.mixer.set_num_channels(32)
        pygame.mixer.set_reserved(2)
except pygame.error:
    SOUND_ENABLED = False

try:
    # على الهاتف نستخدم دقة الشاشة الحقيقية ثم نمدد اللوحة المنطقية
    # إلى كامل الشاشة، مع إبقاء الرسومات الأصلية على canvas بدقة 900x700.
    if ANDROID:
        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        window = pygame.display.set_mode((WIDTH, HEIGHT), getattr(pygame, "SCALED", 0))
except Exception:
    try:
        window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if ANDROID else 0)
    except Exception:
        window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("STARFALL - GALAXY ATTACK")
# canvas = لوحة الرسم الخلفية: نرسم عليها كل شيء ثم ننسخها للنافذة (هذا يسهّل اهتزاز الشاشة)
canvas = pygame.Surface((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# الخطوط المستخدمة في الواجهة (أول خط متوفر في جهازك)
_FN = "consolas,dejavusansmono,couriernew,monospace"
F_S = pygame.font.SysFont(_FN, 14, bold=True)
F_M = pygame.font.SysFont(_FN, 20, bold=True)
F_L = pygame.font.SysFont(_FN, 32, bold=True)
F_XL = pygame.font.SysFont(_FN, 52, bold=True)
F_T = pygame.font.SysFont(_FN, 74, bold=True)

# ================= الألوان =================
BLACK = (5, 7, 18)
WHITE = (240, 248, 255)
RED = (205, 35, 55)
RED_LIGHT = (255, 95, 115)
RED_DARK = (90, 15, 30)
BLUE = (30, 100, 210)
BLUE_LIGHT = (80, 210, 255)
BLUE_DARK = (10, 35, 95)
GOLD = (255, 185, 45)
GOLD_LIGHT = (255, 235, 150)
CYAN = (40, 225, 255)
ORANGE = (255, 110, 30)
PURPLE = (160, 70, 230)
PINK = (255, 60, 180)
GREEN = (80, 220, 110)
GRAY = (130, 138, 150)
GRAY_D = (70, 78, 92)
GRAY_L = (200, 208, 220)
NAVY = (14, 22, 52)
FIRE_COLS = [(255, 120, 30), (255, 190, 60), (255, 80, 40), (255, 230, 140)]

# ================= نظام الحفظ (يحفظ تقدمك تلقائياً) =================
try:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _BASE_DIR = os.getcwd()
if ANDROID:
    try:
        from android.storage import app_storage_path
        _BASE_DIR = app_storage_path()
    except Exception:
        pass
SAVE_FILE = os.path.join(_BASE_DIR, "starfall_save.json")
DEFAULT_BINDS = dict(shield=pygame.K_LSHIFT, special=pygame.K_e,
                     weapon=pygame.K_q, pause=pygame.K_p, bomb=pygame.K_x)

# يحصر القيمة بين حد أدنى وحد أعلى
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

# القيم الافتراضية للحفظ: التقدم، العملات، الترقيات، المركبات، الإعدادات
def default_save():
    return dict(high_score=0, score=0, level=1, coins=0,
                weapons=["laser"], equipped="laser", power=1,
                max_health=5, max_special=3, max_shield=100,
                sfx=7, music=4, difficulty=1, shake=True,
                autofire=True, two_players=False,
                ship="vanguard", ships=["vanguard"], speed_lv=0, regen_lv=0,
                coin_lv=0, luck_lv=0, firerate_lv=0, spower_lv=0,
                drones=0, revives=0, bombs=0,
                crystals=0, used_codes=[], aegis=0, coin2=False, drone2=False,
                skins=["classic"], skin="classic", trails=["cyan"], trail="cyan",
                bloom=True, scan=True,
                vip_until=0, daily_last=0, daily_day=0, pass_xp=0, pass_prem=False,
                pass_free=[], pass_paid=[], purchases=[],
                binds=dict(DEFAULT_BINDS))

# تحميل الحفظ من الملف مع التحقق من كل قيمة حتى لا يفسد الملف اللعبة
def load_save():
    base = default_save()
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in base:
                base[k] = v
        binds = dict(DEFAULT_BINDS)
        for k, v in dict(base["binds"]).items():
            if k in binds:
                binds[k] = int(v)
        base["binds"] = binds
        base["level"] = clamp(int(base["level"]), 1, MAX_LEVEL)
        base["power"] = clamp(int(base["power"]), 1, 30)
        base["max_health"] = clamp(int(base["max_health"]), 3, 10)
        base["max_special"] = clamp(int(base["max_special"]), 3, 9)
        base["max_shield"] = clamp(int(base["max_shield"]), 100, 300)
        base["difficulty"] = clamp(int(base["difficulty"]), 0, 2)
        base["sfx"] = clamp(int(base["sfx"]), 0, 10)
        base["music"] = clamp(int(base["music"]), 0, 10)
        for k, hi in (("speed_lv", 5), ("regen_lv", 5), ("coin_lv", 10), ("luck_lv", 10),
                      ("firerate_lv", 10), ("spower_lv", 10), ("drones", 3),
                      ("revives", 9), ("bombs", 9)):
            base[k] = clamp(int(base[k]), 0, hi)
        if "vanguard" not in base["ships"]:
            base["ships"].append("vanguard")
        if base["ship"] not in base["ships"]:
            base["ship"] = "vanguard"
        base["crystals"] = max(0, int(base["crystals"]))
        base["aegis"] = clamp(int(base["aegis"]), 0, 4)
        base["coin2"] = bool(base["coin2"])
        base["drone2"] = bool(base["drone2"])
        for key in ("vip_until", "daily_last", "daily_day", "pass_xp"):
            base[key] = max(0, int(base[key]))
        base["pass_prem"] = bool(base["pass_prem"])
        for key in ("pass_free", "pass_paid", "purchases"):
            if not isinstance(base[key], list):
                base[key] = []
        base["purchases"] = [str(c) for c in base["purchases"]][-2000:]
        for key in ("used_codes", "skins", "trails"):
            if not isinstance(base[key], list):
                base[key] = list(default_save()[key])
        base["used_codes"] = [str(c) for c in base["used_codes"]][-2000:]
        if "classic" not in base["skins"]:
            base["skins"].append("classic")
        if base["skin"] not in base["skins"]:
            base["skin"] = "classic"
        if "cyan" not in base["trails"]:
            base["trails"].append("cyan")
        if base["trail"] not in base["trails"]:
            base["trail"] = "cyan"
        if "laser" not in base["weapons"]:
            base["weapons"].append("laser")
        if base["equipped"] not in base["weapons"]:
            base["equipped"] = "laser"
    except Exception:
        return default_save()
    return base

# كتابة الحفظ بأمان (عبر ملف مؤقت ثم استبدال)
def write_save():
    try:
        tmp = SAVE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(save, f)
        os.replace(tmp, SAVE_FILE)
    except Exception:
        pass

save = load_save()

def vip_active():
    """هل اشتراك VIP فعّال الآن؟"""
    return time.time() < save["vip_until"]


def add_coins(n):
    """يضيف عملات للاعب مع مكافأة المتجر (كل مستوى = +10%) ويعيد العدد الفعلي."""
    n = int(round(n * (1 + 0.1 * save["coin_lv"]) * (2 if save["coin2"] else 1) * (1.5 if vip_active() else 1.0)))
    save["coins"] += n
    return n


# ================= نظام الشحن: العملة المميزة (كريستال نوفا) =================
# الكريستال لا يُكسب من اللعب، بل يُشحن بكود شحن. الكود يُولَّد بملف starfall_codegen.py (للمالك فقط)
# تنبيه أمني: بما أن اللعبة كود مفتوح فيمكن استخراج المفتاح السري. لحماية حقيقية للأرباح
# استعمل خادماً يتحقق من الأكواد، أو حوّل اللعبة إلى برنامج تنفيذي (PyInstaller/Nuitka).
RECHARGE_SECRET = b"CHANGE-THIS-SECRET-BEFORE-RELEASE"   # غيّره هنا وفي starfall_codegen.py بنفس القيمة
STORE_URL = "https://example.com/starfall-store"        # رابط متجرك الذي تبيع فيه الأكواد
RECHARGE_TIERS = [100, 300, 700, 1500, 4000, 10000]     # كمية الكريستال لكل فئة كود
RECHARGE_PRICES = ["$0.99", "$2.99", "$6.99", "$14.99", "$34.99", "$79.99"]  # للعرض فقط

# ---------- نظام المبيعات (للربح) ----------
# PURCHASE_MODE = "codes": الدفع خارج اللعبة (موقعك/itch.io/Steam) ثم يدخل اللاعب كوداً.
# PURCHASE_MODE = "play" : الدفع عبر Google Play Billing. ضع في PLAY_BILLING_HOOK دالة (sku, callback)
#   تبدأ عملية الشراء في Google Play وتستدعي callback(purchase_token) بعد نجاحها (يجب التحقق من الإيصال في خادمك).
# مهم: متجر Google Play يُلزم باستعمال Play Billing لبيع العناصر الرقمية داخل التطبيق.
PURCHASE_MODE = "codes"
PLAY_BILLING_HOOK = None
# فئات الأكواد بالترتيب (رقم الفئة داخل الكود = موضع المنتج هنا)
CODE_SKUS = ["crystals_100", "crystals_300", "crystals_700", "crystals_1500", "crystals_4000", "crystals_10000",
             "starter_pack", "vip_30d", "battle_pass", "mega_pack"]
# كتالوج المنتجات: المعرّف -> (الاسم, السعر للعرض, ما يُمنح). اجعل المعرّفات مطابقة لـ Play Console
PRODUCTS = {
    "crystals_100": ("100 Crystals", "$0.99", dict(crystals=100)),
    "crystals_300": ("300 Crystals", "$2.99", dict(crystals=300)),
    "crystals_700": ("700 Crystals", "$6.99", dict(crystals=700)),
    "crystals_1500": ("1500 Crystals", "$14.99", dict(crystals=1500)),
    "crystals_4000": ("4000 Crystals", "$34.99", dict(crystals=4000)),
    "crystals_10000": ("10000 Crystals", "$79.99", dict(crystals=10000)),
    "starter_pack": ("Starter Pack (once)", "$1.99", dict(crystals=500, coins=5000, revives=3, skins=["gold"], once=True)),
    "vip_30d": ("VIP 30 Days", "$4.99", dict(vip_days=30)),
    "battle_pass": ("Starfall Pass", "$4.99", dict(pass_premium=True)),
    "mega_pack": ("Mega Pack (once)", "$19.99", dict(crystals=3000, ships=["eclipse"], bombs=9, revives=9, once=True)),
}


def _b32(b):
    return base64.b32encode(b).decode().rstrip("=")


def make_code(tier, rid=None):
    """يصنع كود شحن: [الفئة 1 بايت + رقم عشوائي 5 بايت + توقيع HMAC 6 بايت]."""
    rid = rid if rid is not None else os.urandom(5)
    payload = bytes([tier]) + rid
    mac = hmac.new(RECHARGE_SECRET, payload, hashlib.sha256).digest()[:6]
    raw = _b32(payload + mac)
    return "SF-" + "-".join(raw[i:i + 5] for i in range(0, 20, 5))


def parse_code(code):
    """يتحقق من توقيع الكود ويعيد (الفئة, المعرّف) أو None إن كان مزيفاً."""
    s = code.upper().replace(" ", "")
    if s.startswith("SF-"):
        s = s[3:]
    s = s.replace("-", "")
    if len(s) != 20:
        return None
    try:
        raw = base64.b32decode(s + "====")
    except Exception:
        return None
    payload, mac = raw[:6], raw[6:]
    good = hmac.new(RECHARGE_SECRET, payload, hashlib.sha256).digest()[:6]
    if not hmac.compare_digest(mac, good) or payload[0] >= len(CODE_SKUS):
        return None
    return payload[0], payload[1:].hex()


def apply_grants(gr):
    """يطبّق مكافآت (عملات، كريستال، عناصر، VIP...) على الحفظ. يُستعمل للمنتجات والحزم والمكافآت."""
    save["coins"] += gr.get("coins", 0)
    save["crystals"] += gr.get("crystals", 0)
    save["revives"] = min(9, save["revives"] + gr.get("revives", 0))
    save["bombs"] = min(9, save["bombs"] + gr.get("bombs", 0))
    save["aegis"] = min(4, save["aegis"] + gr.get("aegis", 0))
    for key in ("ships", "weapons", "skins", "trails"):
        for item in gr.get(key, []):
            if item not in save[key]:
                save[key].append(item)
    if gr.get("coin2"):
        save["coin2"] = True
    if gr.get("drone2"):
        save["drone2"] = True
    if gr.get("vip_days"):
        base = max(time.time(), save["vip_until"])
        save["vip_until"] = int(base + gr["vip_days"] * 86400)
    if gr.get("pass_premium"):
        save["pass_prem"] = True


def grant_product(sku, token):
    """يمنح منتجاً اشتراه اللاعب (إيصال واحد لا يُعالج مرتين). يعيد رسالة."""
    if sku not in PRODUCTS:
        return "UNKNOWN PRODUCT"
    name, _, gr = PRODUCTS[sku]
    if token in save["purchases"]:
        return "ALREADY PROCESSED"
    if gr.get("once") and sku in save["purchases"]:
        return "ONE-TIME OFFER ALREADY USED"
    save["purchases"].append(token)
    if gr.get("once"):
        save["purchases"].append(sku)
    apply_grants(gr)
    write_save()
    return "%s ACTIVATED!" % name.upper()


def request_purchase(sku):
    """زر الشراء: عبر Google Play إن فُعّل، وإلا يطلب كود شحن."""
    if PURCHASE_MODE == "play" and PLAY_BILLING_HOOK:
        PLAY_BILLING_HOOK(sku, lambda token: grant_product(sku, token))
        return "OPENING GOOGLE PLAY..."
    return "BUY A CODE IN THE STORE (F1), THEN TYPE IT"


def redeem_code(code):
    """يستبدل كود شحن (مرة واحدة لكل كود). يعيد (نجاح, رسالة)."""
    r = parse_code(code)
    if r is None:
        return False, "INVALID CODE"
    tier, cid = r
    if cid in save["used_codes"]:
        return False, "CODE ALREADY USED"
    sku = CODE_SKUS[tier]
    name, _, gr = PRODUCTS[sku]
    if gr.get("once") and sku in save["purchases"]:
        return False, "ONE-TIME OFFER ALREADY USED"
    save["used_codes"].append(cid)
    return True, grant_product(sku, "code-" + cid)


def reward_text(gr):
    """وصف مختصر للمكافأة."""
    parts = []
    if gr.get("coins"):
        parts.append("%d COINS" % gr["coins"])
    if gr.get("crystals"):
        parts.append("%d CRYSTALS" % gr["crystals"])
    for k, lab in (("revives", "REVIVES"), ("bombs", "BOMBS"), ("aegis", "AEGIS")):
        if gr.get(k):
            parts.append("%d %s" % (gr[k], lab))
    for k, lab in (("ships", "SHIP"), ("weapons", "GUN"), ("skins", "PAINT"), ("trails", "TRAIL")):
        for it in gr.get(k, []):
            parts.append("%s %s" % (lab, it.upper()))
    if gr.get("vip_days"):
        parts.append("VIP %d DAYS" % gr["vip_days"])
    if gr.get("pass_premium"):
        parts.append("PREMIUM PASS")
    return " + ".join(parts) or "-"


# ---------- المكافأة اليومية (تزيد عودة اللاعبين) ----------
DAILY_REWARDS = [dict(coins=500), dict(coins=800), dict(coins=1200, bombs=1), dict(coins=1800),
                 dict(coins=2500, revives=1), dict(coins=3500), dict(coins=6000, crystals=15)]


def daily_state():
    """يعيد (يوم السلسلة الحالي, هل الجائزة متاحة اليوم)."""
    t = datetime.date.today().toordinal()
    last = save["daily_last"]
    if last == t:
        return save["daily_day"] % 7, False
    if last and t - last > 1:
        return 0, True
    return save["daily_day"] % 7, True


def claim_daily():
    day, ok = daily_state()
    if not ok:
        return "COME BACK TOMORROW"
    apply_grants(DAILY_REWARDS[day])
    extra = ""
    if vip_active():
        save["crystals"] += 25
        extra = " + 25 VIP CRYSTALS"
    save["daily_last"] = datetime.date.today().toordinal()
    save["daily_day"] = (day + 1) % 7
    write_save()
    return "CLAIMED: " + reward_text(DAILY_REWARDS[day]) + extra


# ---------- تذكرة ستارفول (Battle Pass): 30 مستوى، مسار مجاني ومسار مميز ----------
PASS_TIERS = 30
PASS_XP_PER_TIER = 100
_PASS_SPECIAL = {5: dict(bombs=5), 10: dict(skins=["aurora"]), 15: dict(revives=5),
                 20: dict(ships=["nova"]), 25: dict(aegis=1), 30: dict(ships=["eclipse"])}


def pass_reward(tier, premium):
    if not premium:
        return dict(coins=300 + 100 * tier)
    return _PASS_SPECIAL.get(tier, dict(crystals=15))


def pass_tier():
    return min(PASS_TIERS, save["pass_xp"] // PASS_XP_PER_TIER)


def add_pass_xp(n):
    save["pass_xp"] = min(PASS_TIERS * PASS_XP_PER_TIER, save["pass_xp"] + int(n))


def claim_pass():
    """يستلم كل مكافآت المستويات المفتوحة. يعيد عدد المكافآت."""
    got = 0
    for t in range(1, pass_tier() + 1):
        if t not in save["pass_free"]:
            apply_grants(pass_reward(t, False))
            save["pass_free"].append(t)
            got += 1
        if save["pass_prem"] and t not in save["pass_paid"]:
            apply_grants(pass_reward(t, True))
            save["pass_paid"].append(t)
            got += 1
    write_save()
    return got


# ================= دوال مساعدة =================

# دوال الألوان والأرقام: lerp = استيفاء بين رقمين، mix = مزج لونين، shade = تعتيم/تفتيح لون
def lerp(a, b, t):
    return a + (b - a) * t

def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))

def shade(c, f):
    return (clamp(int(c[0] * f), 0, 255), clamp(int(c[1] * f), 0, 255),
            clamp(int(c[2] * f), 0, 255))

# يرسم نصاً على اللوحة (مع ظل أسود للوضوح)
def text(s, font, col, x, y, center=False, right=False, shadow=True):
    img = font.render(s, True, col)
    if center:
        x -= img.get_width() // 2
        y -= img.get_height() // 2
    elif right:
        x -= img.get_width()
    if shadow:
        canvas.blit(font.render(s, True, (0, 0, 0)), (int(x) + 2, int(y) + 2))
    canvas.blit(img, (int(x), int(y)))

# شاشة تحميل بسيطة تظهر أثناء توليد الرسومات والأصوات
def show_loading(msg):
    canvas.fill((4, 5, 14))
    text(msg, F_M, GOLD_LIGHT, WIDTH // 2, HEIGHT // 2, center=True)
    window.blit(canvas, (0, 0))
    pygame.display.flip()
    pygame.event.pump()

# اسم المفتاح للعرض على الشاشة
def kname(code):
    try:
        return pygame.key.name(code).upper()
    except Exception:
        return "?"

# ---------- التوهج (إضاءة بوضع الإضافة) ----------
_glow_cache = {}

def _q(c):
    return ((c[0] >> 4) << 4, (c[1] >> 4) << 4, (c[2] >> 4) << 4)

# توهج دائري يُرسم مرة واحدة ويُخزَّن (cache) لأنه يُستعمل مئات المرات
def glow_sprite(radius, color):
    key = (radius, color)
    s = _glow_cache.get(key)
    if s is None:
        if len(_glow_cache) > 1500:
            _glow_cache.clear()
        s = pygame.Surface((radius * 2, radius * 2))
        s.fill((0, 0, 0))
        for i in range(radius, 0, -1):
            t = 1 - i / radius
            f = (t ** 2) * 0.95
            pygame.draw.circle(s, (int(color[0] * f), int(color[1] * f),
                                   int(color[2] * f)), (radius, radius), i)
        _glow_cache[key] = s
    return s

# يضيف التوهج بوضع الجمع (ADD) فيظهر كضوء حقيقي فوق الخلفية
def add_glow(surf, x, y, radius, color):
    radius = max(3, int(radius))
    g = glow_sprite(radius, _q(color))
    surf.blit(g, (int(x - radius), int(y - radius)),
              special_flags=pygame.BLEND_ADD)

# ---------- أداة رسم الصور بالكود ----------
# Pen = أداة رسم المركبات: ترسم مضلعات ودوائر بإحداثيات نسبية، mirror=True ترسم الجهة المقابلة تلقائياً
class Pen:
    def __init__(self, s, ox, oy, k):
        self.s, self.ox, self.oy, self.k = s, ox, oy, k

    def P(self, pts, m=1):
        return [(self.ox + x * m * self.k, self.oy + y * self.k) for x, y in pts]

    def _w(self, ew):
        return max(1, int(ew * self.k))

    def poly(self, pts, col, edge=None, ew=2, mirror=False):
        for m in ((1, -1) if mirror else (1,)):
            p = self.P(pts, m)
            pygame.draw.polygon(self.s, col, p)
            if edge:
                pygame.draw.polygon(self.s, edge, p, self._w(ew))

    def gpoly(self, pts, c1, c2, edge=None, ew=2, mirror=False):
        """polygon with layered highlight (modern shaded look)."""
        self.poly(pts, c2, edge, ew, mirror)
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        self.poly([(cx + (x - cx) * 0.68 - 1.5, cy + (y - cy) * 0.68 - 1.5) for x, y in pts], mix(c1, c2, 0.5), None, 2, mirror)
        self.poly([(cx + (x - cx) * 0.36 - 2, cy + (y - cy) * 0.36 - 2) for x, y in pts], c1, None, 2, mirror)

    def neon(self, a, b, col, w=1.5, mirror=False):
        self.line(a, b, shade(col, 0.35), w * 3, mirror)
        self.line(a, b, col, w * 1.6, mirror)
        self.line(a, b, mix(col, WHITE, 0.8), max(0.6, w * 0.6), mirror)

    def rect(self, x, y, w, h, col, edge=None, ew=2, mirror=False):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                  col, edge, ew, mirror)

    def ell(self, cx, cy, rx, ry, col, edge=None, ew=2, mirror=False):
        for m in ((1, -1) if mirror else (1,)):
            r = pygame.Rect(0, 0, max(2, int(rx * 2 * self.k)),
                            max(2, int(ry * 2 * self.k)))
            r.center = (int(self.ox + cx * m * self.k), int(self.oy + cy * self.k))
            pygame.draw.ellipse(self.s, col, r)
            if edge:
                pygame.draw.ellipse(self.s, edge, r, self._w(ew))

    def circ(self, cx, cy, r, col, edge=None, ew=2, mirror=False):
        for m in ((1, -1) if mirror else (1,)):
            c = (int(self.ox + cx * m * self.k), int(self.oy + cy * self.k))
            rr = max(1, int(r * self.k))
            pygame.draw.circle(self.s, col, c, rr)
            if edge:
                pygame.draw.circle(self.s, edge, c, rr, self._w(ew))

    def line(self, a, b, col, w=2, mirror=False):
        for m in ((1, -1) if mirror else (1,)):
            pa = (self.ox + a[0] * m * self.k, self.oy + a[1] * self.k)
            pb = (self.ox + b[0] * m * self.k, self.oy + b[1] * self.k)
            pygame.draw.line(self.s, col, pa, pb, self._w(w))

# يصنع صورة: يرسم بحجم مضاعف ثم يصغّرها ليحصل على حواف ناعمة
def make_sprite(w, h, fn, *args, scale=1.0):
    big = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
    fn(Pen(big, w, h, 2.0 * scale), *args)
    return pygame.transform.smoothscale(big, (w, h))

_flash_cache = {}

# نسخة بيضاء مضيئة من الصورة تظهر لحظة إصابة العدو
def flash_version(spr):
    f = _flash_cache.get(id(spr))
    if f is None:
        f = spr.copy()
        f.fill((110, 110, 110, 0), special_flags=pygame.BLEND_RGB_ADD)
        _flash_cache[id(spr)] = f
    return f

# يرسم لهب المحرك (3 طبقات + توهج) ويرتعش مع الزمن
def draw_flame(surf, x, y, w, length, color, anim, up=False):
    L = length * (0.8 + 0.2 * math.sin(anim * 0.55))
    d = -1 if up else 1
    pygame.draw.polygon(surf, color, [(x - w, y), (x + w, y), (x, y + L * d)])
    pygame.draw.polygon(surf, mix(color, WHITE, 0.5),
                        [(x - w * 0.55, y), (x + w * 0.55, y), (x, y + L * 0.7 * d)])
    pygame.draw.polygon(surf, WHITE,
                        [(x - w * 0.25, y), (x + w * 0.25, y), (x, y + L * 0.4 * d)])
    add_glow(surf, x, y + L * 0.3 * d, w * 3 + 4, color)

# ================= توليد الصوت بالكود (بدون ملفات) =================

# محرك توليد الصوت: ندخل دالة رياضية تعطي كل عينة صوتية، ثم نضيف صدى ونحوّلها لصوت pygame
def synth(duration, fn, vol=0.6, echo=None):
    if not SOUND_ENABLED:
        return None
    n = max(1, int(SR * duration))
    buf = [fn(i / SR, i / n) for i in range(n)]
    if echo:
        delay, gain, reps = echo
        d = int(SR * delay)
        dry = buf[:]
        buf += [0.0] * (d * reps)
        for k in range(1, reps + 1):
            g = gain ** k
            off = d * k
            for i in range(n):
                buf[i + off] += dry[i] * g
    data = array.array("h")
    for v in buf:
        iv = int(math.tanh(v) * vol * 32767)
        for _ in range(CH):
            data.append(iv)
    try:
        return pygame.mixer.Sound(buffer=data.tobytes())
    except Exception:
        return None

# غلاف الصوت: بداية سريعة ثم تلاشٍ تدريجي
def _env(p, a=0.02, pw=1.6):
    return min(1.0, p / a) * (1 - p) ** pw

def chirp(f0, f1, dur, vol, harm=0.4, noise=0.0, pw=1.6, a=0.03, trem=0, click=0.0, sq=0.0, echo=None, sub=0.0):
    """نغمة متغيرة التردد. click = نقرة بداية، sub = دوي منخفض يعطي قوة، echo = صدى."""
    def fn(t, p):
        ph = f0 * t + 0.5 * (f1 - f0) * t * p
        sn = math.sin(TAU * ph)
        v = sn + harm * math.sin(TAU * ph * 2.01)
        if sq:
            v += sq * (1.0 if sn > 0 else -1.0)
        if noise:
            v += noise * random.uniform(-1, 1)
        if click:
            v += click * random.uniform(-1, 1) * math.exp(-t * 350)
        if sub:
            v += 0.9 * math.sin(TAU * sub * t * (1 - 0.6 * p)) * math.exp(-t * 18)
        if trem:
            v *= 0.7 + 0.3 * math.sin(TAU * trem * t)
        return v * _env(p, a, pw)
    return synth(dur, fn, vol, echo)

# صوت انفجار حقيقي: فرقعة البداية + ضجيج منخفض + دوي عميق + قرقعة حطام + صدى
def blast(dur, vol, low=0.2, thump=70, pw=1.5, crackle=0.0, rumble=0.0, echo=None):
    st = [0.0, 0.0, 0.0]

    def fn(t, p):
        a = low * (1 - p) ** 1.3 + 0.015
        nz = random.uniform(-1, 1)
        st[0] += a * (nz - st[0])
        st[1] += a * (st[0] - st[1])
        crack = nz * math.exp(-t * 60) * 0.9
        sub = math.sin(TAU * thump * (1 - 0.55 * p) * t) * 0.9 * (1 - p) ** 0.8
        v = st[1] * 7.0 + sub + crack
        if rumble:
            st[2] += 0.01 * (nz - st[2])
            v += st[2] * rumble * 40 * min(1.0, p * 8) * (1 - p) ** 0.7
        if crackle and random.random() < crackle * (1 - p):
            v += random.uniform(-0.6, 0.6)
        return v * _env(p, 0.002, pw)
    return synth(dur, fn, vol, echo)

# نغمات متتابعة (تُستعمل لأصوات الجوائز والشراء والفوز)
def arp(notes, step, vol, harm=0.35, pw=1.2):
    def fn(t, p):
        i = min(len(notes) - 1, int(t / step))
        lt = (t - i * step) / step
        f = notes[i]
        return (math.sin(TAU * f * t) + harm * math.sin(TAU * f * 2 * t)) * \
            (1 - lt) ** pw * min(1.0, lt * 30)
    return synth(step * len(notes), fn, vol)

# صفارة إنذار تتأرجح (ظهور الزعيم)
def siren(dur, vol):
    def fn(t, p):
        ph = 520 * t - (160 / (TAU * 2.2)) * math.cos(TAU * 2.2 * t)
        return math.sin(TAU * ph) * 0.8 * min(1.0, t * 20) * min(1.0, (dur - t) * 10)
    return synth(dur, fn, vol)

# مولّد الموسيقى: وتر خلفي هادئ + خط باص + نغمات متسلسلة حسب سلسلة الأوتار prog
def music_track(prog, bpm, minor=True, pat=(0, 1, 2, 1)):
    beat = 60.0 / bpm
    bar = beat * 4
    total = bar * len(prog)
    chord = (1.0, 1.1892 if minor else 1.2599, 1.4983)

    def fn(t, p):
        b = int(t / bar) % len(prog)
        root = prog[b]
        tb = t - b * bar
        pad = 0.0
        slow = math.sin(TAU * 0.25 * t) * 0.6
        for m in chord:
            pad += math.sin(TAU * root * m * t + slow)
        pad *= 0.07
        bt = (tb % beat) / beat
        bass = math.sin(TAU * root * 0.5 * t) * (1 - bt) ** 1.4 * 0.4
        step = beat / 2
        si = int(t / step)
        lt = (t - si * step) / step
        f = root * 2 * chord[pat[si % len(pat)] % 3] * (2 if (si // len(pat)) % 2 else 1)
        a = (math.sin(TAU * f * t) + 0.3 * math.sin(TAU * f * 2 * t)) * \
            (1 - lt) ** 2 * min(1.0, lt * 40) * 0.16
        fade = min(1.0, t / 0.05, (total - t) / 0.05)
        return (pad + bass + a) * fade
    return synth(total, fn, 0.55)

def engine_hum():
    """حلقة هدير المحرك (ثانية واحدة بترددات صحيحة لتتكرر دون فرقعة)."""
    def fn(t, p):
        v = math.sin(TAU * 55 * t) * 0.6 + math.sin(TAU * 110 * t) * 0.35 + math.sin(TAU * 165 * t + 1.0) * 0.18
        v *= 0.75 + 0.25 * math.sin(TAU * 6 * t)
        return v * 0.5
    return synth(1.0, fn, 0.5)

def roar(dur, vol):
    """زئير الزعيم: نغمة منخفضة مع تعديل ترددي وضجيج."""
    def fn(t, p):
        f = 90 - 40 * p
        mod = math.sin(TAU * 17 * t) * 3.0
        v = math.sin(TAU * f * t + mod) + 0.5 * math.sin(TAU * f * 2.01 * t + mod * 1.3)
        v += 0.35 * random.uniform(-1, 1) * (1 - p)
        return v * _env(p, 0.05, 0.9)
    return synth(dur, fn, vol, (0.12, 0.4, 3))

def zap():
    """صوت برق كهربائي (سلاح تسلا)."""
    def fn(t, p):
        f = 3200 - 2400 * p
        v = math.sin(TAU * f * t) * (1 if random.random() < 0.7 else -1) + random.uniform(-1, 1) * 0.6
        return v * _env(p, 0.01, 1.2)
    return synth(0.22, fn, 0.38, (0.04, 0.35, 2))

def whoosh(dur, vol, up=True):
    """صفير هواء/صاروخ: ضجيج مفلتر يتصاعد أو يتناقص."""
    st = [0.0]

    def fn(t, p):
        nz = random.uniform(-1, 1)
        a = 0.05 + 0.4 * (p if up else 1 - p)
        st[0] += a * (nz - st[0])
        return st[0] * 5.0 * math.sin(math.pi * p) ** 1.5
    return synth(dur, fn, vol, (0.06, 0.3, 2))

def alarm_beep():
    """إنذار انخفاض الصحة."""
    def fn(t, p):
        f = 880 if (t * 6) % 1 < 0.5 else 660
        return math.sin(TAU * f * t) * 0.8 * min(1.0, t * 40) * min(1.0, (0.5 - t) * 40)
    return synth(0.5, fn, 0.4)

# قواميس الأصوات والموسيقى وقنوات التشغيل
S = {}
MUSIC = {}
_last_play = {}
_cur_music = [None]
MUSIC_CH = None
ENGINE_CH = None
_engine_on = [False]

def build_sounds():
    """يبني كل الأصوات بالكود. كل سلاح له صوت مميز (نغمة + نقرة + دوي + صدى)."""
    # ---- أسلحة اللاعب ----
    S["laser"] = chirp(1800, 260, 0.18, 0.42, 0.7, click=0.6, sq=0.35, echo=(0.05, 0.35, 2), sub=140)
    S["spread"] = chirp(1000, 180, 0.22, 0.42, 0.9, 0.1, click=0.7, echo=(0.05, 0.35, 2), sub=110)
    S["rapid"] = chirp(2400, 650, 0.07, 0.3, 0.3, click=1.0, sub=200)
    S["plasma"] = chirp(240, 50, 0.45, 0.55, 1.0, 0.1, pw=1.0, trem=22, echo=(0.08, 0.4, 3), sub=70)
    S["missile"] = whoosh(0.55, 0.5, True)
    S["flak"] = blast(0.35, 0.55, 0.5, 120, 1.8, 0.05, 0.3, echo=(0.05, 0.3, 2))
    S["tesla"] = zap()
    S["special"] = chirp(120, 900, 0.5, 0.5, 0.8, 0.15, 1.2, trem=18, echo=(0.08, 0.35, 2), sub=60)
    # ---- العدو والزعيم ----
    S["enemy_fire"] = chirp(560, 160, 0.15, 0.28, 0.5, 0.3, click=0.5, sub=90)
    S["mine"] = chirp(300, 120, 0.2, 0.35, 0.5, click=0.4)
    S["roar"] = roar(1.6, 0.8)
    S["teleport"] = whoosh(0.5, 0.45, False)
    S["beam"] = chirp(120, 130, 0.9, 0.5, 1.2, 0.2, pw=0.3, a=0.1, trem=40, echo=(0.1, 0.3, 2))
    # ---- انفجارات (نسختان لكل حجم لتنويع الصوت) ----
    S["boom_s"] = [blast(0.5, 0.6, 0.35, 85, 1.5, 0.04, 0.5, echo=(0.07, 0.3, 2)) for _ in range(2)]
    S["boom_m"] = [blast(0.9, 0.7, 0.2, 60, 1.4, 0.06, 0.8, echo=(0.1, 0.35, 3)) for _ in range(2)]
    S["boom_l"] = [blast(1.4, 0.8, 0.12, 45, 1.2, 0.08, 1.0, echo=(0.13, 0.4, 3)) for _ in range(2)]
    S["boom_boss"] = blast(3.0, 0.95, 0.07, 32, 1.0, 0.1, 1.2, echo=(0.18, 0.45, 4))
    S["bomb"] = blast(1.6, 0.95, 0.15, 38, 1.1, 0.08, 1.2, echo=(0.15, 0.4, 3))
    S["die"] = blast(2.0, 0.95, 0.09, 45, 1.1, 0.1, 1.2, echo=(0.15, 0.4, 3))
    S["hit"] = chirp(1800, 600, 0.05, 0.25, 0.6, click=0.8)
    S["hurt"] = blast(0.5, 0.75, 0.5, 100, 1.3, 0.05, 0.5, echo=(0.06, 0.3, 2))
    S["shield"] = chirp(900, 1500, 0.2, 0.3, 0.2, trem=30)
    S["alarm"] = alarm_beep()
    # ---- جوائز وواجهة ----
    S["coin"] = arp([1318, 1760], 0.06, 0.35)
    S["gem"] = arp([1046, 1318, 1568, 2093], 0.06, 0.35)
    S["powerup"] = arp([523, 659, 784, 1046, 1318], 0.055, 0.4)
    S["buy"] = arp([880, 1320, 1760], 0.07, 0.4)
    S["deny"] = chirp(200, 140, 0.18, 0.4, 0.6, pw=0.8)
    S["click"] = chirp(900, 700, 0.04, 0.25)
    S["warn"] = siren(1.8, 0.5)
    S["clear"] = arp([523, 659, 784, 1046, 784, 1046, 1318], 0.11, 0.45)
    S["win"] = arp([523, 659, 784, 1046, 1318, 1568, 2093, 1568, 2093], 0.14, 0.5)
    S["lance"] = chirp(3200, 300, 0.32, 0.5, 0.5, click=0.8, sq=0.2, echo=(0.06, 0.4, 3), sub=90)
    S["photon"] = chirp(1500, 700, 0.14, 0.4, 0.6, click=0.5, echo=(0.04, 0.3, 2), sub=120)
    S["singularity"] = chirp(90, 35, 0.7, 0.6, 1.0, 0.1, pw=0.8, trem=9, echo=(0.12, 0.45, 3), sub=50)
    S["crystal"] = arp([1318, 1760, 2093, 2637, 3136], 0.07, 0.45)
    S["engine"] = engine_hum()
    # ---- موسيقى ----
    MUSIC["menu"] = music_track([98.0, 82.41, 110.0, 87.31], 84, True, (0, 1, 2, 1))
    MUSIC["calm"] = music_track([110.0, 87.31, 130.81, 98.0], 110)
    MUSIC["boss"] = music_track([82.41, 87.31, 82.41, 73.42], 150, True, (0, 2, 1, 2))
    MUSIC["boss2"] = music_track([92.5, 98.0, 82.41, 87.31], 160, True, (0, 2, 1, 0))
    apply_volumes()

# تطبيق مستوى الصوت المختار في الإعدادات على كل الأصوات
def apply_volumes():
    if not SOUND_ENABLED:
        return
    for v in S.values():
        for s in (v if isinstance(v, list) else [v]):
            if s:
                s.set_volume(save["sfx"] / 10.0)
    if MUSIC_CH is not None:
        MUSIC_CH.set_volume(save["music"] / 10.0 * 0.45)

# تشغيل مؤثر صوتي (gap = أقل فاصل بين تكرارين لمنع تراكم الأصوات)
def sfx(name, gap=30, vol=1.0):
    s = S.get(name)
    if isinstance(s, list):
        s = random.choice(s)
    if not s:
        return
    now = pygame.time.get_ticks()
    if now - _last_play.get(name, -999) < gap:
        return
    _last_play[name] = now
    ch = s.play()
    if ch is not None and vol < 1.0:
        ch.set_volume(vol)

def set_engine(flag):
    """تشغيل/إيقاف هدير المحرك أثناء اللعب فقط."""
    if not SOUND_ENABLED or ENGINE_CH is None or not S.get("engine"):
        return
    if flag and not _engine_on[0]:
        ENGINE_CH.play(S["engine"], loops=-1)
        ENGINE_CH.set_volume(0.22)
    elif not flag and _engine_on[0]:
        ENGINE_CH.stop()
    _engine_on[0] = flag

# تبديل الموسيقى الخلفية (قائمة / مرحلة / زعيم)
def set_music(name):
    if not SOUND_ENABLED or MUSIC_CH is None:
        return
    if _cur_music[0] == name:
        return
    _cur_music[0] = name
    MUSIC_CH.stop()
    if name and MUSIC.get(name):
        MUSIC_CH.play(MUSIC[name], loops=-1)
        MUSIC_CH.set_volume(save["music"] / 10.0 * 0.45)

# ================= تصاميم المركبات والأعداء =================
# ألوان المركبة الأساسية: الأول للاعب 1 (أحمر) والثاني للاعب 2 (أزرق)
SHIP_PALS = [
    dict(hull=(176, 40, 46), light=(232, 92, 80), dark=(88, 18, 28),
         wing=(132, 30, 40), trim=(70, 235, 220), flame=(60, 220, 255)),
    dict(hull=(40, 92, 196), light=(110, 175, 255), dark=(14, 36, 96),
         wing=(30, 66, 150), trim=(255, 205, 80), flame=(255, 190, 70)),
]

# المركبة الأساسية (فانجارد). tier = مستوى التطور حسب قوة السلاح: 0 أساسي، 1 أجنحة ومدافع، 2 شفرات طاقة
def draw_player_ship(p, pal, tier=0):
    """Modern red battlecruiser-fighter. tier 0/1/2 (weapon power) adds wings and cannons."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:
        p.gpoly([(-46, 0), (-92, 40), (-88, 74), (-60, 60), (-44, 30)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-52, 14), (-84, 60), T, 1.6, mirror=True)
        p.circ(-88, 70, 4, T, WHITE, 1, mirror=True)
    if tier >= 1:
        p.gpoly([(-40, -6), (-70, 28), (-72, 62), (-48, 52), (-36, 24)], L, W, BLACK, 2.5, mirror=True)
        p.rect(-54, -12, 5, 34, GRAY_D, BLACK, 1.5, mirror=True)
        p.rect(-53, -17, 3, 6, T, BLACK, 1, mirror=True)
        p.neon((-44, 10), (-64, 54), T, 1.4, mirror=True)
    p.gpoly([(-12, -14), (-48, 18), (-56, 56), (-34, 50), (-12, 38)], L, W, BLACK, 2.5, mirror=True)
    p.poly([(-14, -4), (-40, 20), (-46, 44), (-14, 30)], D, None, 2, mirror=True)
    for yy in (22, 32, 42):
        p.line((-46, yy + 2), (-18, yy - 8), shade(W, 0.6), 1.5, mirror=True)
    p.neon((-16, -4), (-52, 52), T, 1.6, mirror=True)
    p.poly([(-12, 30), (-26, 60), (-14, 62)], D, BLACK, 1.5, mirror=True)
    hull = [(0, -78), (-6, -58), (-11, -34), (-15, -4), (-17, 26), (-13, 52), (-7, 60),
            (7, 60), (13, 52), (17, 26), (15, -4), (11, -34), (6, -58)]
    p.gpoly(hull, L, H, BLACK, 2.5)
    p.line((0, -72), (0, 54), D, 2)
    p.poly([(-10, -26), (10, -26), (13, -4), (-13, -4)], D, BLACK, 1)
    p.neon((-9, 0), (-11, 44), T, 1.2, mirror=True)
    p.poly([(-5, -58), (5, -58), (3, -48), (-3, -48)], D, None, 2)
    # فتحات تهوية ومآخذ هواء جانبية ومسامير
    for yy in (-20, -12):
        p.line((-12, yy), (-7, yy + 3), D, 1.5, mirror=True)
    p.poly([(-17, 10), (-24, 22), (-17, 30)], D, BLACK, 1, mirror=True)
    p.circ(-13, -30, 1.2, WHITE, None, 1, mirror=True)
    p.circ(-15, 4, 1.2, WHITE, None, 1, mirror=True)
    p.ell(0, -38, 6.5, 16, (14, 36, 70), BLACK, 1.5)
    p.ell(0, -40, 4.5, 12, (70, 190, 255))
    p.ell(-1.5, -46, 1.6, 5, WHITE)
    p.circ(0, 26, 9, (14, 20, 40), BLACK, 2)
    p.circ(0, 26, 6, T)
    p.circ(0, 26, 3, WHITE)
    p.poly([(0, -78), (-3, -66), (3, -66)], T, BLACK, 1)
    p.rect(-14, 58, 8, 7, GRAY_D, BLACK, 1.5)
    p.rect(6, 58, 8, 7, GRAY_D, BLACK, 1.5)
    if tier >= 2:
        p.poly([(0, -92), (-4, -76), (4, -76)], pal["light"], BLACK, 1.5)
        p.poly([(-3, 8), (0, 2), (3, 8)], T, BLACK, 1)

def draw_ship_falcon(p, pal, tier=0):
    """الصقر: مركبة رشيقة بأجنحة مائلة للأمام (سريعة وضعيفة الدرع)."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:  # شفرات أمامية كبيرة
        p.gpoly([(-30, -26), (-88, -4), (-82, 28), (-34, 10)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-40, -14), (-80, 10), T, 1.5, mirror=True)
        p.circ(-84, 24, 3.5, T, WHITE, 1, mirror=True)
    if tier >= 1:  # مدافع جانبية
        p.rect(-48, -6, 5, 42, GRAY_D, BLACK, 1.5, mirror=True)
        p.rect(-47, -12, 3, 7, T, BLACK, 1, mirror=True)
    p.gpoly([(-8, 6), (-54, -12), (-62, 30), (-36, 60), (-10, 46)], L, W, BLACK, 2.5, mirror=True)
    p.poly([(-12, 12), (-48, 0), (-54, 28), (-12, 38)], D, None, 2, mirror=True)
    p.neon((-12, 10), (-54, -8), T, 1.5, mirror=True)
    p.poly([(-10, 40), (-24, 68), (-12, 66)], D, BLACK, 1.5, mirror=True)
    hull = [(0, -86), (-5, -62), (-9, -30), (-12, 10), (-13, 40), (-9, 62), (0, 68),
            (9, 62), (13, 40), (12, 10), (9, -30), (5, -62)]
    p.gpoly(hull, L, H, BLACK, 2.5)
    p.line((0, -82), (0, 62), D, 2)
    p.neon((-6, -20), (-8, 42), T, 1.2, mirror=True)
    p.ell(0, -44, 5.5, 17, (14, 36, 70), BLACK, 1.5)
    p.ell(0, -46, 3.8, 13, (110, 215, 255))
    p.ell(-1.2, -54, 1.4, 5, WHITE)
    p.circ(0, 30, 7, (14, 20, 40), BLACK, 2)
    p.circ(0, 30, 4.5, T)
    p.circ(0, 30, 2, WHITE)
    p.rect(-9, 64, 6, 6, GRAY_D, BLACK, 1)
    p.rect(3, 64, 6, 6, GRAY_D, BLACK, 1)

def draw_ship_titan(p, pal, tier=0):
    """العملاق: مركبة ثقيلة عريضة بدروع ومدافع كبيرة (بطيئة وقوية)."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:  # أكتاف درعية إضافية
        p.gpoly([(-60, -6), (-98, 20), (-94, 68), (-62, 60)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-70, 8), (-90, 60), T, 1.6, mirror=True)
    if tier >= 1:  # مدافع ثقيلة
        p.rect(-80, -22, 8, 50, GRAY_D, BLACK, 1.5, mirror=True)
        p.rect(-79, -28, 6, 7, T, BLACK, 1, mirror=True)
    p.gpoly([(-14, -26), (-62, -8), (-72, 44), (-54, 66), (-14, 50)], L, W, BLACK, 3, mirror=True)
    p.poly([(-18, -14), (-54, 0), (-62, 40), (-18, 38)], D, None, 2, mirror=True)
    p.rect(-66, -26, 9, 44, GRAY_D, BLACK, 1.5, mirror=True)
    p.rect(-65, -31, 7, 7, T, BLACK, 1, mirror=True)
    p.neon((-20, 0), (-58, 56), T, 1.6, mirror=True)
    hull = [(0, -64), (-14, -50), (-22, -22), (-25, 20), (-23, 52), (-12, 66),
            (12, 66), (23, 52), (25, 20), (22, -22), (14, -50)]
    p.gpoly(hull, L, H, BLACK, 3)
    for x in (-16, -8, 8, 16):
        p.line((x, -30), (x * 1.1, 56), D, 1.5)
    p.poly([(-20, -8), (20, -8), (23, 6), (-23, 6)], D, BLACK, 1.5)
    p.ell(0, -34, 9, 15, (14, 36, 70), BLACK, 1.5)
    p.ell(0, -36, 6.5, 11, (90, 200, 255))
    p.ell(-2, -41, 2, 4.5, WHITE)
    p.circ(0, 22, 13, (14, 20, 40), BLACK, 2.5)
    p.circ(0, 22, 9, T)
    p.circ(0, 22, 4, WHITE)
    for x in (-18, -5, 8):
        p.rect(x, 66, 10, 8, GRAY_D, BLACK, 1.5)

def draw_ship_phantom(p, pal, tier=0):
    """الشبح: جناح طائر خفي بحواف نيون (ضرر عالٍ ودرع ضعيف)."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:  # أشواك وأجنحة سفلية
        p.gpoly([(-44, 22), (-90, 62), (-62, 66), (-40, 48)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-48, 30), (-84, 62), T, 1.6, mirror=True)
        p.circ(-88, 62, 3.5, T, WHITE, 1, mirror=True)
    if tier >= 1:
        p.gpoly([(-30, 8), (-72, 42), (-56, 50), (-28, 34)], L, W, BLACK, 2.5, mirror=True)
        p.rect(-60, 16, 4, 26, GRAY_D, BLACK, 1.2, mirror=True)
    p.gpoly([(-6, -32), (-62, 30), (-72, 62), (-36, 54), (-12, 38)], L, W, BLACK, 2.5, mirror=True)
    p.poly([(-10, -20), (-50, 28), (-54, 48), (-14, 34)], D, None, 2, mirror=True)
    p.neon((-8, -28), (-68, 58), T, 1.8, mirror=True)
    hull = [(0, -82), (-8, -52), (-14, -12), (-16, 30), (-10, 58), (0, 66),
            (10, 58), (16, 30), (14, -12), (8, -52)]
    p.gpoly(hull, L, H, BLACK, 2.5)
    p.line((0, -78), (0, 60), BLACK, 2.5)
    p.poly([(0, -54), (-5, -32), (0, -22), (5, -32)], (70, 200, 255), BLACK, 1.2)
    p.poly([(-1.5, -46), (0, -40), (1.5, -46)], WHITE)
    p.neon((-9, -4), (-11, 44), T, 1.2, mirror=True)
    p.circ(0, 28, 8, (14, 14, 28), BLACK, 2)
    p.circ(0, 28, 5, T)
    p.circ(0, 28, 2, WHITE)
    p.rect(-9, 62, 5, 6, GRAY_D, BLACK, 1)
    p.rect(4, 62, 5, 6, GRAY_D, BLACK, 1)

def draw_ship_nova(p, pal, tier=0):
    """نوفا (مميزة بالكريستال): جناحان هلاليان وبلورة طاقة في القلب."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:
        p.gpoly([(-40, -30), (-96, -6), (-90, 40), (-44, 16)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-48, -20), (-88, 20), T, 1.8, mirror=True)
        p.circ(-92, 30, 4, T, WHITE, 1, mirror=True)
    if tier >= 1:
        p.rect(-50, -14, 5, 40, GRAY_D, BLACK, 1.5, mirror=True)
        p.circ(-47, -18, 3, T, WHITE, 1, mirror=True)
    p.gpoly([(-8, -4), (-44, -34), (-64, -2), (-58, 40), (-34, 62), (-12, 44)], L, W, BLACK, 2.5, mirror=True)
    p.poly([(-12, 2), (-42, -22), (-54, 4), (-50, 34), (-14, 36)], D, None, 2, mirror=True)
    p.neon((-10, -2), (-58, 36), T, 1.6, mirror=True)
    hull = [(0, -90), (-7, -62), (-12, -30), (-14, 8), (-12, 42), (-6, 64),
            (6, 64), (12, 42), (14, 8), (12, -30), (7, -62)]
    p.gpoly(hull, L, H, BLACK, 2.5)
    p.line((0, -84), (0, 60), D, 2)
    p.poly([(0, -4), (-9, 14), (0, 34), (9, 14)], (20, 26, 60), BLACK, 1.5)
    p.poly([(0, 0), (-6, 14), (0, 28), (6, 14)], T)
    p.poly([(0, 2), (-2.5, 14), (0, 22)], WHITE)
    p.ell(0, -50, 5, 15, (14, 36, 70), BLACK, 1.5)
    p.ell(0, -52, 3.5, 11, (120, 225, 255))
    p.ell(-1, -58, 1.3, 4, WHITE)
    p.neon((-9, -20), (-10, 40), T, 1.2, mirror=True)
    p.rect(-9, 64, 6, 6, GRAY_D, BLACK, 1)
    p.rect(3, 64, 6, 6, GRAY_D, BLACK, 1)


def draw_ship_eclipse(p, pal, tier=0):
    """إكليبس (مميزة بالكريستال): مركبة سوداء بحواف ذهبية وهالة كسوف."""
    H, L, D, W, T = pal["hull"], pal["light"], pal["dark"], pal["wing"], pal["trim"]
    if tier >= 2:
        p.gpoly([(-50, 10), (-100, 46), (-92, 76), (-58, 60)], L, W, BLACK, 2.5, mirror=True)
        p.neon((-56, 20), (-94, 68), T, 1.8, mirror=True)
        p.circ(-96, 70, 4, T, WHITE, 1, mirror=True)
    if tier >= 1:
        p.gpoly([(-34, 4), (-76, 34), (-70, 60), (-40, 48)], L, W, BLACK, 2.5, mirror=True)
        p.rect(-58, -8, 5, 36, GRAY_D, BLACK, 1.5, mirror=True)
    p.gpoly([(-10, -20), (-56, -4), (-74, 34), (-60, 70), (-24, 52), (-12, 36)], L, W, BLACK, 2.5, mirror=True)
    p.poly([(-14, -8), (-50, 6), (-62, 34), (-18, 34)], D, None, 2, mirror=True)
    p.neon((-12, -16), (-70, 36), T, 1.8, mirror=True)
    p.neon((-26, 50), (-58, 66), T, 1.2, mirror=True)
    hull = [(0, -84), (-10, -56), (-16, -20), (-18, 24), (-12, 56), (-6, 66),
            (6, 66), (12, 56), (18, 24), (16, -20), (10, -56)]
    p.gpoly(hull, L, H, BLACK, 2.5)
    p.line((0, -80), (0, 60), BLACK, 2.5)
    p.circ(0, 12, 14, T)
    p.circ(3, 10, 12, (6, 6, 12))
    p.neon((-12, -10), (-13, 40), T, 1.2, mirror=True)
    p.poly([(0, -58), (-5, -34), (0, -26), (5, -34)], (255, 190, 80), BLACK, 1.2)
    p.poly([(-1.5, -50), (0, -44), (1.5, -50)], WHITE)
    p.rect(-10, 66, 6, 6, GRAY_D, BLACK, 1)
    p.rect(4, 66, 6, 6, GRAY_D, BLACK, 1)
    if tier >= 2:
        p.poly([(0, -98), (-4, -82), (4, -82)], T, BLACK, 1.5)


def draw_drone(p):
    """طائرة مرافقة صغيرة تطلق النار تلقائياً."""
    p.poly([(-4, -6), (-18, 6), (-14, 10), (-4, 4)], GRAY, BLACK, 1.5, mirror=True)
    p.circ(0, 0, 8, GRAY_D, BLACK, 2)
    p.circ(0, 0, 5, CYAN_G)
    p.circ(-1.5, -1.5, 1.6, WHITE)
    p.rect(-2, 6, 4, 5, GRAY, BLACK, 1)

CYAN_G = (90, 210, 255)

# ألوان نيون تُستعمل في تفاصيل الأعداء
NEON_R = (255, 70, 90)
NEON_O = (255, 150, 40)
NEON_M = (255, 80, 225)
NEON_C = (60, 225, 255)
NEON_Y = (255, 220, 70)

# مظاهر المركبة (skins): اللون الأساسي ولون الزخرفة. "classic" = ألوان المركبة الأصلية
SKIN_COL = dict(ice=((110, 190, 255), (255, 255, 255)), crimson=((220, 50, 70), (255, 200, 90)),
                stealth=((64, 68, 92), (255, 70, 70)), gold=((245, 190, 60), (255, 255, 200)),
                aurora=((80, 230, 170), (200, 120, 255)), void=((120, 60, 200), (60, 255, 230)))
TRAIL_COL = dict(pink=(255, 80, 200), rainbow=None)  # rainbow = يتغير لونه مع الزمن


def skin_pal(pal, skin):
    """يعيد ألوان مركبة بعد تطبيق المظهر."""
    if skin == "classic" or skin not in SKIN_COL:
        return pal
    main, trim = SKIN_COL[skin]
    return dict(hull=shade(main, 0.85), light=shade(main, 1.3), dark=shade(main, 0.4),
                wing=shade(main, 0.65), trim=trim, flame=pal["flame"])


def trail_color(pal, anim):
    """لون لهب المحرك حسب الأثر المختار."""
    t = save["trail"]
    if t == "rainbow":
        a = anim * 0.05
        return (int(150 + 105 * math.sin(a)), int(150 + 105 * math.sin(a + 2.09)), int(150 + 105 * math.sin(a + 4.19)))
    if t in TRAIL_COL and TRAIL_COL[t]:
        return TRAIL_COL[t]
    return pal["flame"]


# ----- تصاميم الأعداء الستة (كل واحد يُرسم بالكود، ورأسه للأعلى ثم يُقلب للأسفل) -----
def draw_scout(p):
    p.gpoly([(-8, -6), (-38, 14), (-36, 30), (-12, 26)], (100, 110, 145), (34, 38, 62), BLACK, 2, mirror=True)
    p.neon((-12, 12), (-34, 24), NEON_R, 1.3, mirror=True)
    p.gpoly([(0, -36), (-8, -12), (-10, 18), (-5, 32), (0, 28), (5, 32), (10, 18), (8, -12)],
            (120, 130, 165), (40, 44, 70), BLACK, 2.5)
    p.poly([(-4, 20), (4, 20), (0, 30)], NEON_R, BLACK, 1)
    p.ell(0, -10, 3.5, 9, (255, 80, 100), BLACK, 1)
    p.ell(-1, -13, 1.4, 4, WHITE)
    p.neon((0, -28), (0, -18), NEON_R, 1.2)
    p.circ(-30, 24, 2.5, NEON_R, BLACK, 1, mirror=True)

def draw_fighter(p):
    p.gpoly([(-8, -18), (-46, 6), (-50, 34), (-14, 28)], (110, 118, 150), (36, 40, 64), BLACK, 2.5, mirror=True)
    p.poly([(-30, 10), (-48, 32), (-36, 30)], (24, 26, 40), BLACK, 1, mirror=True)
    p.neon((-12, 4), (-44, 26), NEON_O, 1.4, mirror=True)
    p.rect(-47, 4, 4, 24, GRAY_D, BLACK, 1, mirror=True)
    p.circ(-45, 30, 2.5, NEON_O, BLACK, 1, mirror=True)
    p.gpoly([(0, -42), (-8, -24), (-12, 8), (-7, 36), (0, 40), (7, 36), (12, 8), (8, -24)],
            (130, 140, 175), (42, 46, 74), BLACK, 3)
    p.poly([(-5, -4), (5, -4), (7, 22), (0, 30), (-7, 22)], (28, 30, 48), BLACK, 1)
    p.neon((0, -34), (0, -6), NEON_O, 1.3)
    p.ell(0, -14, 4.5, 10, (255, 170, 60), BLACK, 1.5)
    p.ell(-1.2, -17, 1.6, 4.5, WHITE)
    p.circ(0, 18, 4, NEON_O, BLACK, 1)
    p.rect(-6, 36, 12, 6, GRAY_D, BLACK, 1)

def draw_bee(p):
    for m in (1, -1):
        w = [(m * 8, -4), (m * 36, -22), (m * 42, -10), (m * 32, 2), (m * 10, 6)]
        pygame.draw.polygon(p.s, (240, 244, 250), p.P([(abs(x) * (1 if m == 1 else -1), y) for x, y in w]))
        pygame.draw.polygon(p.s, (120, 130, 150), p.P([(abs(x) * (1 if m == 1 else -1), y) for x, y in w]), p._w(1.5))
    p.ell(0, 4, 14, 24, (236, 150, 30), BLACK, 2.5)
    for yy in (-2, 8, 18):
        p.line((-12, yy), (12, yy), (110, 40, 20), 3)
    p.ell(0, -22, 11, 9, (210, 70, 40), BLACK, 2)
    p.circ(-5, -23, 3.5, (255, 240, 120), BLACK, 1, mirror=True)
    p.circ(0, 12, 6, (255, 220, 90), (110, 40, 20), 1.5)
    for sx in (-1, 1):
        p.line((sx * 12, 6), (sx * 24, 22), (110, 60, 30), 2)
        p.line((sx * 11, -2), (sx * 24, 8), (110, 60, 30), 2)

def draw_clawer(p):
    p.gpoly([(-30, -34), (-14, -34), (-14, 6), (14, 6), (14, -34), (30, -34), (30, 22), (18, 36), (-18, 36), (-30, 22)],
            (150, 80, 140), (52, 28, 62), BLACK, 3)
    p.rect(-30, -40, 16, 12, GRAY_L, BLACK, 2)
    p.rect(14, -40, 16, 12, GRAY_L, BLACK, 2)
    p.neon((-22, -28), (-22, 24), NEON_M, 1.4, mirror=True)
    p.circ(-22, -34, 3, NEON_M, WHITE, 1, mirror=True)
    p.gpoly([(-11, -26), (11, -26), (13, 10), (0, 22), (-13, 10)], (70, 74, 106), (24, 26, 44), BLACK, 2)
    p.ell(0, -8, 6, 12, (255, 90, 230), BLACK, 1.5)
    p.ell(-1.5, -12, 2, 5, WHITE)
    p.rect(-14, 36, 8, 6, GRAY_D, BLACK, 1)
    p.rect(6, 36, 8, 6, GRAY_D, BLACK, 1)

def draw_shielder(p):
    p.gpoly([(-30, -2), (-48, -10), (-44, 28), (-30, 22)], (120, 160, 200), (34, 50, 80), BLACK, 2.5, mirror=True)
    p.gpoly([(0, -44), (-30, -4), (-40, 24), (-16, 42), (16, 42), (40, 24), (30, -4)],
            (130, 160, 200), (36, 48, 80), BLACK, 3.5)
    p.poly([(0, -34), (-22, -2), (-30, 20), (-12, 32), (12, 32), (30, 20), (22, -2)], (24, 32, 58), BLACK, 1.5)
    for yy in (-18, -6, 8, 20):
        p.neon((-24 + abs(yy) * 0.2, yy), (-8, yy + 2), NEON_C, 1.1, mirror=True)
    p.neon((0, -40), (0, -24), NEON_C, 1.3)
    p.ell(0, -2, 11, 17, (10, 20, 50), BLACK, 2)
    p.ell(0, -2, 8, 13, (80, 230, 255))
    p.ell(-2, -8, 2.6, 5, WHITE)
    p.circ(0, 26, 4, NEON_C, BLACK, 1)
    p.rect(-14, 40, 8, 8, GRAY_D, BLACK, 1)
    p.rect(6, 40, 8, 8, GRAY_D, BLACK, 1)

def draw_heavy(p):
    p.gpoly([(-8, -24), (-50, -48), (-62, 16), (-40, 44), (-8, 32)], (210, 150, 80), (84, 52, 44), BLACK, 3.5, mirror=True)
    for i in range(4):
        p.neon((-14 - i * 9, -18 + i * 6), (-12 - i * 10, 28 - i * 2), NEON_Y, 1, mirror=True)
    p.circ(-44, -12, 5, (120, 230, 255), BLACK, 1.5, mirror=True)
    p.rect(-58, 6, 5, 24, GRAY_L, BLACK, 1, mirror=True)
    p.gpoly([(0, -44), (-13, -22), (-15, 18), (-9, 48), (9, 48), (15, 18), (13, -22)], (140, 110, 180), (42, 30, 72), BLACK, 3)
    p.ell(0, -8, 7, 20, (24, 24, 60), BLACK, 2)
    p.ell(0, -8, 5, 16, (100, 220, 255))
    p.ell(-1.5, -14, 1.8, 6, WHITE)
    p.poly([(-8, 22), (8, 22), (6, 42), (-6, 42)], (170, 70, 230), BLACK, 1.5)
    p.rect(-10, 48, 8, 8, GRAY_D, BLACK, 1)
    p.rect(2, 48, 8, 8, GRAY_D, BLACK, 1)

# سجل المركبات: دالة رسم كل مركبة، ثم مواصفاتها (سرعة، صحة، درع، ضرر، تبريد، سعر، ألوان اللاعبين)
SHIP_DRAW = dict(vanguard=draw_player_ship, falcon=draw_ship_falcon,
                 titan=draw_ship_titan, phantom=draw_ship_phantom,
                 nova=draw_ship_nova, eclipse=draw_ship_eclipse)
# كل مركبة: السرعة، تعديل الصحة، تعديل الدرع، مضاعف الضرر، مضاعف زمن التبريد، وألوان اللاعب 1 و 2
SHIP_DEFS = dict(
    vanguard=dict(name="VANGUARD", desc="Balanced battlecruiser", price=0, speed=6.0, hp=0, shield=0, dmg=1.0, cool=1.0,
                  pals=SHIP_PALS),
    falcon=dict(name="FALCON", desc="Fast and agile, light armor", price=500, speed=7.6, hp=-1, shield=0, dmg=1.0, cool=0.85,
                pals=[dict(hull=(225, 230, 240), light=(255, 255, 255), dark=(90, 100, 120), wing=(60, 150, 210),
                           trim=(255, 170, 60), flame=(255, 170, 60)),
                      dict(hull=(60, 200, 140), light=(150, 255, 200), dark=(20, 80, 60), wing=(30, 130, 100),
                           trim=(255, 255, 120), flame=(255, 255, 120))]),
    titan=dict(name="TITAN", desc="Heavy armor, slow, big shield", price=900, speed=4.8, hp=2, shield=60, dmg=1.15, cool=1.05,
               pals=[dict(hull=(200, 120, 40), light=(255, 190, 90), dark=(100, 56, 20), wing=(150, 86, 30),
                          trim=(255, 240, 120), flame=(255, 200, 80)),
                     dict(hull=(110, 60, 170), light=(190, 140, 255), dark=(50, 24, 90), wing=(80, 40, 130),
                          trim=(120, 255, 255), flame=(120, 230, 255))]),
    phantom=dict(name="PHANTOM", desc="Stealth glass cannon, +35% damage", price=1400, speed=6.6, hp=-1, shield=0, dmg=1.35, cool=0.9,
                 pals=[dict(hull=(50, 50, 70), light=(110, 110, 150), dark=(20, 20, 32), wing=(36, 36, 56),
                            trim=(190, 90, 255), flame=(190, 110, 255)),
                       dict(hull=(40, 70, 70), light=(90, 160, 160), dark=(14, 34, 34), wing=(24, 52, 52),
                            trim=(90, 255, 170), flame=(110, 255, 190))]),
    # ---- مركبات مميزة تُشترى بالكريستال فقط ----
    nova=dict(name="NOVA PRIME", desc="Premium: fast, shielded, +25% dmg", price=900, speed=7.0, hp=0, shield=40, dmg=1.25, cool=0.85,
              pals=[dict(hull=(230, 240, 255), light=(255, 255, 255), dark=(70, 90, 130), wing=(90, 150, 230),
                         trim=(90, 255, 255), flame=(90, 255, 255)),
                    dict(hull=(255, 235, 240), light=(255, 255, 255), dark=(130, 70, 100), wing=(230, 110, 180),
                         trim=(255, 120, 200), flame=(255, 120, 200))]),
    eclipse=dict(name="ECLIPSE", desc="Premium: elite armor, +50% dmg", price=1800, speed=6.8, hp=1, shield=80, dmg=1.5, cool=0.8,
                 pals=[dict(hull=(28, 28, 40), light=(90, 90, 120), dark=(10, 10, 18), wing=(60, 48, 24),
                            trim=(255, 200, 70), flame=(255, 190, 60)),
                       dict(hull=(30, 20, 40), light=(100, 70, 130), dark=(10, 6, 20), wing=(50, 30, 70),
                            trim=(200, 120, 255), flame=(200, 120, 255))]),
)

# مواصفات الأعداء: الحياة hp، السرعة، نصف القطر r، النقاط، هل يثبت في مكانه hold، سعة الحركة، زمن الإطلاق fire
ENEMY_DEFS = dict(
    scout=dict(hp=1.0, speed=3.3, r=22, score=10, size=(76, 76), hold=False, amp=40, freq=0.045, fire=None, fn=draw_scout),
    fighter=dict(hp=2.0, speed=2.7, r=28, score=15, size=(96, 92), hold=False, amp=70, freq=0.03, fire=(70, 150), fn=draw_fighter),
    bee=dict(hp=2.5, speed=2.4, r=26, score=20, size=(84, 84), hold=False, amp=110, freq=0.05, fire=(80, 160), fn=draw_bee),
    clawer=dict(hp=5.0, speed=1.6, r=32, score=35, size=(88, 92), hold=True, fire=(70, 130), fn=draw_clawer),
    shield=dict(hp=9.0, speed=1.3, r=38, score=55, size=(104, 104), hold=True, fire=(80, 140), fn=draw_shielder),
    heavy=dict(hp=16.0, speed=1.0, r=46, score=90, size=(136, 112), hold=True, fire=(70, 120), fn=draw_heavy),
)

# ---------------- الزعماء ----------------
# ألوان الزعماء (10 ألوان تتبدل بين الزعماء)
BOSS_PALS = [
    dict(wing=(205, 210, 222), cannon=(214, 86, 40), ring=(235, 175, 40), eye=(255, 50, 60), body=(50, 60, 125)),
    dict(wing=(200, 225, 205), cannon=(60, 160, 90), ring=(210, 230, 90), eye=(255, 240, 60), body=(30, 90, 70)),
    dict(wing=(200, 230, 255), cannon=(70, 140, 230), ring=(120, 230, 255), eye=(255, 80, 200), body=(30, 50, 120)),
    dict(wing=(225, 200, 250), cannon=(150, 70, 210), ring=(255, 120, 220), eye=(255, 230, 70), body=(60, 30, 110)),
    dict(wing=(250, 225, 190), cannon=(200, 60, 40), ring=(255, 210, 90), eye=(90, 255, 230), body=(110, 40, 40)),
    dict(wing=(190, 240, 235), cannon=(40, 170, 160), ring=(255, 255, 140), eye=(255, 70, 70), body=(20, 80, 100)),
    dict(wing=(235, 235, 245), cannon=(120, 120, 140), ring=(255, 90, 90), eye=(90, 230, 255), body=(40, 40, 60)),
    dict(wing=(255, 210, 220), cannon=(225, 70, 130), ring=(190, 120, 255), eye=(255, 240, 120), body=(100, 30, 80)),
    dict(wing=(220, 245, 190), cannon=(130, 190, 40), ring=(255, 170, 50), eye=(255, 60, 90), body=(50, 90, 30)),
    dict(wing=(255, 235, 170), cannon=(230, 160, 40), ring=(255, 110, 70), eye=(100, 160, 255), body=(100, 70, 20)),
]
BOSS_ADJ = ["IRON", "VOID", "NOVA", "CRIMSON", "TITAN", "PHANTOM", "OMEGA", "SOLAR", "FROST", "TOXIC"]
BOSS_NOUN = ["WARDEN", "DEVOURER", "SENTINEL", "OVERLORD"]

# ----- تصاميم الزعماء الثمانية: الجمجمة، الدماغ، الملكة، الحصن، الشبح، التوأم، الكسّار، عين الفراغ -----
def draw_boss_skull(p, pal, tier):
    wing, cannon, ring, eye = pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    blade = [(-34, -24), (-118, -118), (-148, -92), (-150, -30), (-128, 34), (-72, 62), (-40, 40)]
    p.poly(blade, wing, BLACK, 4, mirror=True)
    p.poly([(-44, -22), (-112, -104), (-136, -84), (-138, -34), (-60, 6)], shade(wing, 0.82), None, mirror=True)
    p.line((-100, -100), (-62, 26), shade(wing, 0.6), 3, mirror=True)
    p.circ(-124, -82, 5, GRAY_D, BLACK, 1.5, mirror=True)
    p.poly([(-50, 30), (-125, 45), (-152, 82), (-70, 70)], shade(wing, 0.75), BLACK, 3, mirror=True)
    p.poly([(-135, -18), (-72, -34), (-52, 34), (-128, 52)], cannon, BLACK, 4, mirror=True)
    p.poly([(-128, -8), (-82, -22), (-70, 22), (-120, 36)], shade(cannon, 1.2), None, mirror=True)
    for i in range(3):
        p.line((-122 + i * 12, -4 + i * 3), (-112 + i * 12, 28 + i * 3), shade(cannon, 0.6), 2, mirror=True)
    p.ell(-92, 44, 32, 14, (50, 30, 20), BLACK, 3, mirror=True)
    p.ell(-92, 43, 25, 10, (255, 200, 50), None, mirror=True)
    p.rect(-40, -86, 14, 28, GRAY, BLACK, 2, mirror=True)
    p.rect(-38, -90, 10, 6, GRAY_L, BLACK, 1, mirror=True)
    p.circ(0, 0, 72, (34, 26, 40), BLACK, 5)
    p.circ(0, 0, 65, ring, BLACK, 3)
    p.circ(0, 0, 52, (60, 26, 36), BLACK, 3)
    p.ell(-60, 0, 9, 26, shade(ring, 0.8), BLACK, 2, mirror=True)
    p.ell(0, 2, 32, 38, (150, 158, 170), BLACK, 2.5)
    p.ell(-13, -4, 10, 8, (40, 10, 16), BLACK, 1.5, mirror=True)
    p.ell(-13, -4, 6, 5, eye, None, mirror=True)
    p.poly([(0, 6), (-4, 17), (4, 17)], (50, 55, 70))
    for x in (-12, -6, 0, 6, 12):
        p.line((x, 24), (x, 34), (60, 66, 82), 2)
    p.line((-14, 24), (14, 24), (60, 66, 82), 2)
    p.poly([(-30, 52), (-54, 80), (-44, 100), (-22, 66)], GRAY_L, BLACK, 3, mirror=True)
    p.poly([(-30, -76), (30, -76), (22, -58), (-22, -58)], ring, BLACK, 3)
    p.circ(0, -67, 6, (90, 220, 255), BLACK, 1.5)
    p.poly([(-26, 70), (26, 70), (18, 88), (-18, 88)], ring, BLACK, 3)
    p.circ(0, 79, 6, (90, 220, 255), BLACK, 1.5)
    if tier >= 1:
        p.poly([(-22, -78), (-12, -112), (-2, -78)], eye, BLACK, 3, mirror=True)
        p.poly([(-6, -78), (0, -120), (6, -78)], eye, BLACK, 3)

def draw_boss_brain(p, pal, tier):
    body, cannon, ring, eye = pal["body"], pal["cannon"], pal["ring"], pal["eye"]
    p.poly([(-70, 40), (-96, 104), (-70, 120), (-44, 72)], shade(body, 0.7), BLACK, 3, mirror=True)
    p.poly([(-100, 8), (-166, -6), (-160, 72), (-110, 80), (-78, 44)], body, BLACK, 4, mirror=True)
    p.poly([(-150, 4), (-162, -2), (-158, 62), (-146, 58)], (200, 50, 60), BLACK, 2, mirror=True)
    p.circ(-114, -50, 44, cannon, BLACK, 4, mirror=True)
    p.ell(-114, -50, 30, 41, shade(cannon, 1.15), None, mirror=True)
    for dx in (-14, 0, 14):
        p.line((-114 + dx, -88), (-114 + dx * 0.5, -12), shade(cannon, 0.65), 2, mirror=True)
    p.circ(-122, -84, 13, (214, 40, 150), BLACK, 3, mirror=True)
    p.circ(-122, -84, 6, (40, 10, 40), None, mirror=True)
    p.poly([(-92, -60), (-70, -112), (70, -112), (92, -60), (70, -72), (-70, -72)], body, BLACK, 5)
    p.ell(0, -100, 32, 18, cannon, BLACK, 3)
    p.poly([(-16, -106), (-8, -106), (-12, -96)], (30, 10, 10))
    p.poly([(8, -106), (16, -106), (12, -96)], (30, 10, 10))
    p.poly([(-12, -94), (12, -94), (6, -88), (0, -92), (-6, -88)], (30, 10, 10))
    p.ell(0, -6, 88, 94, body, BLACK, 5)
    p.ell(0, -4, 72, 80, ring, BLACK, 3)
    p.ell(0, -4, 62, 70, mix(ring, WHITE, 0.45))
    p.ell(0, -8, 46, 38, (210, 150, 170), (120, 60, 80), 2.5)
    for (a, b, c, d) in ((-30, -20, -10, -30), (-20, -4, 4, -14), (0, -26, 24, -22),
                         (6, -6, 32, -10), (-34, -2, -14, 8), (12, 6, 30, 12), (-4, -36, -2, -14)):
        p.line((a, b), (c, d), (150, 80, 100), 2)
    p.ell(-12, -18, 10, 7, (240, 190, 205))
    p.ell(0, 60, 31, 19, (90, 20, 20), BLACK, 3)
    p.ell(0, 60, 25, 14, eye)
    p.ell(0, 60, 5, 12, (40, 5, 5))
    p.poly([(-30, 40), (30, 40), (18, 50), (-18, 50)], GRAY_L, BLACK, 2)
    p.poly([(0, 42), (-6, 48), (6, 48)], (60, 70, 110))
    if tier >= 1:
        p.poly([(-70, -74), (-56, -112), (-44, -78)], eye, BLACK, 3, mirror=True)

def draw_boss_hive(p, pal, tier):
    """ملكة الخلية: جسم حشرة بأجنحة شفافة وعيون مركّبة."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    wc = mix(wing, WHITE, 0.25)
    p.poly([(-30, -28), (-140, -112), (-166, -50), (-120, 8), (-40, 0)], wc, BLACK, 3, mirror=True)
    p.poly([(-34, 10), (-132, 28), (-158, 84), (-84, 74), (-36, 38)], shade(wing, 0.85), BLACK, 3, mirror=True)
    for (a, b) in (((-40, -20), (-140, -92)), ((-40, -10), (-150, -50)), ((-44, 20), (-140, 70))):
        p.line(a, b, shade(wing, 0.55), 2, mirror=True)
    for i, (yy, rx, ry) in enumerate(((60, 34, 26), (88, 28, 22), (112, 20, 18))):
        p.ell(0, yy, rx, ry, shade(body, 0.85 - 0.1 * i), BLACK, 3)
        p.ell(0, yy - 6, rx * 0.8, 4, ring, None)
    for dy in (-6, 14, 34):
        p.line((-40, dy), (-86, dy + 34), shade(body, 0.7), 5, mirror=True)
    p.circ(-62, 52, 17, cannon, BLACK, 3, mirror=True)
    p.circ(-62, 52, 8, ring, None, 1, mirror=True)
    p.ell(0, 10, 50, 56, body, BLACK, 4)
    p.ell(0, 6, 38, 44, mix(body, ring, 0.3))
    p.ell(0, -54, 34, 28, shade(body, 1.1), BLACK, 4)
    p.ell(-18, -58, 13, 16, eye, BLACK, 2, mirror=True)
    p.circ(-21, -63, 4, WHITE, None, 1, mirror=True)
    p.poly([(-10, -34), (-32, -16), (-24, -10), (-4, -26)], GRAY_L, BLACK, 2, mirror=True)
    p.line((-12, -78), (-42, -114), ring, 3, mirror=True)
    p.circ(-42, -114, 6, cannon, BLACK, 1.5, mirror=True)
    if tier >= 1:
        p.poly([(-16, -80), (-8, -108), (0, -82)], eye, BLACK, 2, mirror=True)

def draw_boss_fortress(p, pal, tier):
    """الحصن: محطة قتالية مدرعة بعدسة ليزر قاتلة."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    p.gpoly([(-60, -62), (-150, -42), (-164, 42), (-134, 78), (-60, 62)], shade(wing, 0.95), shade(body, 0.9), BLACK, 4, mirror=True)
    p.circ(-118, 0, 24, GRAY_D, BLACK, 3, mirror=True)
    p.circ(-118, 0, 14, cannon, BLACK, 2, mirror=True)
    p.rect(-124, 10, 12, 34, GRAY, BLACK, 2, mirror=True)
    p.gpoly([(-72, -92), (72, -92), (88, -42), (88, 60), (52, 106), (-52, 106), (-88, 60), (-88, -42)], wing, body, BLACK, 5)
    for i in range(7):
        p.poly([(-72 + i * 22, -90), (-58 + i * 22, -90), (-46 + i * 22, -72), (-60 + i * 22, -72)], GOLD, BLACK, 1)
    p.line((-86, 0), (86, 0), shade(body, 0.7), 3)
    p.ell(0, -34, 36, 26, (14, 20, 40), BLACK, 3)
    p.ell(0, -34, 28, 18, eye)
    p.ell(-9, -40, 9, 5, WHITE)
    p.circ(0, 58, 36, (20, 24, 40), BLACK, 4)
    p.circ(0, 58, 28, ring, BLACK, 2)
    p.circ(0, 58, 18, eye, None, 1)
    p.circ(0, 58, 8, WHITE)
    p.rect(-4, -124, 8, 34, GRAY, BLACK, 2)
    p.circ(0, -126, 6, eye, BLACK, 1.5)
    if tier >= 1:
        p.rect(-34, -112, 10, 22, GRAY, BLACK, 2, mirror=True)

def draw_boss_specter(p, pal, tier):
    """الشبح: كائن رداء متوهج بمخالب طاقة وعيون شبحية."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    for x in (-66, -40, -14, 14, 40, 66):
        p.line((x, 36), (x * 1.25, 116), shade(wing, 0.8), 9)
        p.circ(x * 1.25, 118, 6, ring, BLACK, 1.5)
    p.poly([(0, -112), (-72, -72), (-100, 0), (-84, 62), (-44, 50), (0, 72), (44, 50), (84, 62), (100, 0), (72, -72)], body, BLACK, 5)
    p.poly([(0, -96), (-58, -62), (-82, 0), (-68, 48), (-36, 40), (0, 58), (36, 40), (68, 48), (82, 0), (58, -62)], shade(body, 1.25))
    p.ell(0, -22, 56, 64, shade(body, 0.55), BLACK, 3)
    p.ell(-24, -34, 15, 11, (10, 10, 24), None, 1, mirror=True)
    p.ell(-24, -34, 10, 7, eye, None, 1, mirror=True)
    p.ell(-26, -36, 3, 2, WHITE, None, 1, mirror=True)
    for i in range(6):
        x0 = -30 + i * 12
        p.line((x0, 8), (x0 + 6, 18), ring, 3)
        p.line((x0 + 6, 18), (x0 + 12, 8), ring, 3)
    p.circ(-122, 8, 24, cannon, BLACK, 3, mirror=True)
    p.circ(-122, 8, 14, ring, BLACK, 2, mirror=True)
    p.circ(-122, 8, 6, eye, None, 1, mirror=True)
    p.poly([(-30, -104), (-20, -134), (-8, -108)], ring, BLACK, 2, mirror=True)
    p.poly([(-8, -108), (0, -146), (8, -108)], ring, BLACK, 2)
    if tier >= 1:
        p.circ(0, -66, 7, eye, BLACK, 2)

def draw_boss_gemini(p, pal, tier):
    """التوأم: قرنان قتاليان متصلان بجسر طاقة يطلقان نيراناً متقاطعة."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    p.rect(-112, -16, 224, 32, shade(body, 0.8), BLACK, 4)
    p.neon((-100, 0), (100, 0), eye, 2)
    p.gpoly([(-58, -96), (-134, -86), (-156, -22), (-146, 54), (-104, 104), (-60, 74), (-48, 0)], wing, body, BLACK, 5, mirror=True)
    p.circ(-100, 4, 36, GRAY_D, BLACK, 3, mirror=True)
    p.circ(-100, 4, 28, cannon, BLACK, 2, mirror=True)
    p.circ(-100, 4, 14, eye, None, 1, mirror=True)
    p.circ(-104, 0, 4, WHITE, None, 1, mirror=True)
    p.rect(-108, 44, 16, 52, GRAY, BLACK, 2, mirror=True)
    p.ell(-100, 98, 12, 6, (255, 190, 60), BLACK, 1.5, mirror=True)
    p.circ(0, 0, 34, ring, BLACK, 4)
    p.circ(0, 0, 24, (20, 20, 40), BLACK, 2)
    p.circ(0, 0, 14, eye, None, 1)
    p.circ(-5, -5, 5, WHITE)
    p.poly([(-20, -34), (0, -66), (20, -34)], shade(wing, 0.9), BLACK, 3)
    if tier >= 1:
        p.poly([(-130, -92), (-120, -124), (-108, -92)], eye, BLACK, 2, mirror=True)

def draw_boss_crusher(p, pal, tier):
    """الكسّار: دبابة فضائية ثقيلة تزرع الألغام."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    p.rect(-152, -62, 54, 152, GRAY_D, BLACK, 4, mirror=True)
    for i in range(8):
        p.line((-152, -52 + i * 18), (-98, -52 + i * 18), BLACK, 3, mirror=True)
    p.gpoly([(-112, -84), (112, -84), (136, -22), (124, 72), (72, 112), (-72, 112), (-124, 72), (-136, -22)], wing, body, BLACK, 5)
    for i in range(6):
        p.rect(-90 + i * 30, -80, 14, 10, GOLD, BLACK, 1)
    for x in range(-70, 80, 35):
        p.circ(x, 86, 12, cannon, BLACK, 2)
        p.line((x - 15, 86), (x + 15, 86), GRAY_L, 2)
        p.line((x, 71), (x, 101), GRAY_L, 2)
    p.circ(0, -20, 48, GRAY_D, BLACK, 4)
    p.circ(0, -20, 36, shade(body, 1.1), BLACK, 2)
    p.rect(-9, -20, 18, 84, GRAY, BLACK, 2)
    p.circ(0, -20, 15, eye, None, 1)
    p.circ(-4, -24, 4, WHITE)
    p.circ(-100, -50, 8, ring, BLACK, 1.5, mirror=True)
    if tier >= 1:
        p.rect(-54, -108, 12, 26, GRAY, BLACK, 2, mirror=True)

def draw_boss_void(p, pal, tier):
    """عين الفراغ: عين عملاقة تحيط بها حلقات وتجذب كل شيء نحوها."""
    body, wing, cannon, ring, eye = pal["body"], pal["wing"], pal["cannon"], pal["ring"], pal["eye"]
    for (r, c, e) in ((112, (18, 12, 36), ring), (94, (28, 16, 54), cannon), (76, (10, 6, 22), wing)):
        p.circ(0, 0, r, c, e, 3)
    for i in range(10):
        a = i * TAU / 10
        p.poly([(math.cos(a - 0.12) * 112, math.sin(a - 0.12) * 112), (math.cos(a) * 134, math.sin(a) * 134),
                (math.cos(a + 0.12) * 112, math.sin(a + 0.12) * 112)], ring, BLACK, 2)
    p.ell(0, 0, 60, 36, (240, 240, 250), BLACK, 3)
    p.circ(0, 0, 27, eye, BLACK, 2)
    p.ell(0, 0, 8, 24, (5, 5, 14))
    p.circ(-10, -10, 6, WHITE)
    for i in range(6):
        a = i * TAU / 6 + 0.5
        p.circ(math.cos(a) * 94, math.sin(a) * 94, 6, ring, BLACK, 1.5)
    if tier >= 1:
        p.poly([(-14, -112), (0, -148), (14, -112)], eye, BLACK, 2)

# قائمة دوال رسم الزعماء (الرقم = تصميم الزعيم)
BOSS_DRAW = [draw_boss_skull, draw_boss_brain, draw_boss_hive, draw_boss_fortress,
             draw_boss_specter, draw_boss_gemini, draw_boss_crusher, draw_boss_void]

_boss_cache = {}

def get_boss_sprite(design, pal_idx, tier):
    key = (design, pal_idx, tier)
    if key not in _boss_cache:
        fn = BOSS_DRAW[design]
        _boss_cache[key] = make_sprite(300, 250, fn, BOSS_PALS[pal_idx], tier, scale=0.82)
    return _boss_cache[key]

# ---------------- أيقونات الجوائز والمتجر ----------------
# ألوان أيقونات الجوائز وعناصر المتجر
ICON_COL = dict(
    health=(255, 80, 100), shield=(70, 170, 255), special=(70, 230, 255),
    coin=(255, 200, 60), gem=(255, 90, 220), power=(255, 120, 40),
    rapid=(255, 235, 80), triple=(120, 255, 140), bomb=(255, 90, 60),
    magnet=(255, 70, 70), upgrade=(110, 255, 130), hull=(190, 200, 220),
    repair=(90, 255, 150), w_laser=(60, 220, 255), w_spread=(255, 200, 60),
    w_rapid=(255, 70, 170), w_plasma=(190, 110, 255), w_missile=(255, 140, 60),
)

ICON_COL.update(dict(
    crystal=(190, 120, 255), w_lance=(90, 190, 255), w_photon=(190, 110, 255), w_singularity=(150, 90, 230),
    ship_nova=(120, 240, 255), ship_eclipse=(255, 200, 70),
    skin_classic=(180, 190, 210), skin_ice=(110, 190, 255), skin_crimson=(220, 50, 70), skin_stealth=(110, 116, 150),
    skin_gold=(245, 190, 60), skin_aurora=(80, 230, 170), skin_void=(150, 90, 230),
    bundle=(255, 200, 90),
    trail_pink=(255, 80, 200), trail_rainbow=(255, 220, 120),
    w_flak=(255, 150, 60), w_tesla=(120, 200, 255), firerate=(255, 240, 100), spower=(255, 180, 60),
    speed=(110, 230, 255), regen=(90, 200, 255), coinup=(255, 215, 70), luck=(100, 240, 130),
    drone=(120, 220, 255), revive=(255, 100, 130), ship_vanguard=(230, 90, 80),
    ship_falcon=(120, 200, 255), ship_titan=(240, 170, 70), ship_phantom=(190, 120, 255)))

ICON_COL["pass"] = (255, 220, 120)

# يرسم أيقونة (جائزة أو عنصر متجر) داخل دائرة متوهجة، لكل نوع رسم خاص
def draw_icon(p, kind):
    col = ICON_COL[kind]
    p.circ(0, 0, 19, (8, 12, 30), col, 2.5)
    p.circ(0, 0, 15, shade(col, 0.2))
    if kind == "health":
        p.circ(-5.5, -3, 6.5, col, BLACK, 1)
        p.circ(5.5, -3, 6.5, col, BLACK, 1)
        p.poly([(-11.5, 0), (11.5, 0), (0, 13)], col, BLACK, 1)
        p.circ(-6, -5, 2, WHITE)
    elif kind == "shield":
        p.poly([(0, -13), (11, -9), (10, 5), (0, 14), (-10, 5), (-11, -9)], col, WHITE, 1.5)
        p.poly([(0, -9), (7, -6), (6, 3), (0, 9), (-6, 3), (-7, -6)], shade(col, 0.55))
    elif kind in ("special", "w_missile"):
        c = col if kind == "special" else (230, 230, 240)
        p.ell(0, 0, 4.5, 11, c, BLACK, 1)
        p.poly([(0, -15), (-4.5, -6), (4.5, -6)], (255, 90, 70), BLACK, 1)
        p.poly([(-4, 4), (-9, 12), (-4, 10)], col, BLACK, 1)
        p.poly([(4, 4), (9, 12), (4, 10)], col, BLACK, 1)
        p.poly([(-2.5, 11), (2.5, 11), (0, 17)], (255, 190, 60))
    elif kind == "coin":
        p.circ(0, 0, 12, col, (160, 100, 10), 2)
        p.circ(0, 0, 8, shade(col, 0.82), (255, 235, 150), 1)
        p.rect(-1.5, -6, 3, 12, (255, 240, 170))
    elif kind == "gem":
        p.poly([(0, -13), (11, -3), (0, 13), (-11, -3)], col, WHITE, 1.2)
        p.poly([(0, -13), (4, -3), (0, 13), (-4, -3)], mix(col, WHITE, 0.45))
        p.line((-11, -3), (11, -3), WHITE, 1)
    elif kind == "power":
        p.poly([(0, -14), (8, -2), (6, 10), (0, 14), (-6, 10), (-8, -2)], col, (120, 40, 10), 1.2)
        p.poly([(0, -4), (4, 3), (3, 10), (0, 12), (-3, 10), (-4, 3)], (255, 230, 100))
    elif kind in ("rapid",):
        p.poly([(3, -14), (-8, 2), (-1, 2), (-4, 14), (9, -3), (1, -3)], col, (150, 100, 10), 1.2)
    elif kind == "triple":
        for x in (-8, 0, 8):
            p.rect(x - 2, -6, 4, 14, col, BLACK, 1)
            p.poly([(x - 2, -6), (x + 2, -6), (x, -12)], WHITE, BLACK, 1)
    elif kind == "bomb":
        p.circ(0, 3, 9, (30, 30, 40), WHITE, 1.5)
        p.circ(-3, 0, 2.5, (140, 140, 160))
        p.line((4, -4), (8, -10), (200, 170, 100), 2)
        p.circ(8, -11, 3, (255, 200, 60))
    elif kind == "magnet":
        p.poly([(-10, -12), (-4, -12), (-4, 2), (4, 2), (4, -12), (10, -12), (10, 4),
                (5, 12), (-5, 12), (-10, 4)], col, BLACK, 1.2)
        p.rect(-10, -12, 6, 5, WHITE)
        p.rect(4, -12, 6, 5, WHITE)
    elif kind == "upgrade":
        p.poly([(0, -13), (11, 0), (4, 0), (4, 12), (-4, 12), (-4, 0), (-11, 0)], col, BLACK, 1.2)
    elif kind == "hull":
        p.poly([(0, -13), (12, -5), (12, 6), (0, 14), (-12, 6), (-12, -5)], (160, 170, 190), BLACK, 1.5)
        p.poly([(0, -9), (8, -3), (8, 4), (0, 10), (-8, 4), (-8, -3)], (90, 100, 125))
        p.circ(-8, -4, 1.5, WHITE)
        p.circ(8, -4, 1.5, WHITE)
        p.circ(0, 10, 1.5, WHITE)
    elif kind == "repair":
        p.poly([(-4, -12), (4, -12), (4, -4), (12, -4), (12, 4), (4, 4), (4, 12), (-4, 12),
                (-4, 4), (-12, 4), (-12, -4), (-4, -4)], col, WHITE, 1.2)
    elif kind == "w_laser":
        p.ell(0, 0, 4, 12, col, WHITE, 1.2)
        p.ell(0, 0, 1.5, 9, WHITE)
    elif kind == "w_spread":
        for a in (-0.5, 0, 0.5):
            p.line((0, 10), (math.sin(a) * 15, 10 - math.cos(a) * 22), col, 3)
            p.circ(math.sin(a) * 15, 10 - math.cos(a) * 22, 2.5, WHITE)
    elif kind == "w_rapid":
        for x in (-7, 0, 7):
            p.line((x, -10), (x, -2), col, 3)
            p.line((x, 2), (x, 10), col, 3)
    elif kind == "w_plasma":
        p.circ(0, 0, 9, col, WHITE, 1.5)
        p.circ(0, 0, 4, (245, 220, 255))
        p.circ(-11, 0, 2, WHITE)
        p.circ(11, 0, 2, WHITE)
    else:
        draw_icon_extra(p, kind, col)

SHIP_ICON_PTS = dict(
    vanguard=[(0, -13), (3, -4), (10, 6), (12, 12), (4, 8), (0, 13), (-4, 8), (-12, 12), (-10, 6), (-3, -4)],
    falcon=[(0, -14), (3, -4), (13, -8), (8, 8), (3, 13), (0, 10), (-3, 13), (-8, 8), (-13, -8), (-3, -4)],
    titan=[(0, -12), (7, -8), (12, -2), (13, 10), (6, 13), (-6, 13), (-13, 10), (-12, -2), (-7, -8)],
    phantom=[(0, -14), (4, -6), (13, 12), (5, 8), (0, 13), (-5, 8), (-13, 12), (-4, -6)])
SHIP_ICON_PTS.update(
    nova=[(0, -14), (3, -6), (13, -8), (10, 6), (4, 12), (0, 8), (-4, 12), (-10, 6), (-13, -8), (-3, -6)],
    eclipse=[(0, -14), (5, -6), (13, 6), (12, 13), (4, 8), (0, 12), (-4, 8), (-12, 13), (-13, 6), (-5, -6)])

def draw_icon_extra(p, kind, col):
    """أيقونات الأسلحة والترقيات والمركبات والمظاهر الجديدة."""
    if kind == "bundle":
        p.rect(-11, -4, 22, 15, (150, 90, 40), WHITE, 1.2)
        p.rect(-11, -10, 22, 7, (200, 130, 60), WHITE, 1.2)
        p.rect(-2, -10, 4, 21, col)
        p.circ(0, -4, 2.5, WHITE)
        return
    if kind == "pass":
        p.rect(-13, -9, 26, 18, col, WHITE, 1.2)
        pts = [(math.cos(i * TAU / 10 - math.pi / 2) * (6 if i % 2 == 0 else 2.6),
                math.sin(i * TAU / 10 - math.pi / 2) * (6 if i % 2 == 0 else 2.6)) for i in range(10)]
        p.poly(pts, (120, 60, 160), WHITE, 1)
        return
    if kind == "crystal":
        p.poly([(0, -14), (9, -5), (6, 12), (-6, 12), (-9, -5)], col, WHITE, 1.2)
        p.poly([(0, -14), (3, -5), (0, 12), (-3, -5)], mix(col, WHITE, 0.5))
        p.line((-9, -5), (9, -5), WHITE, 1)
        return
    if kind == "w_lance":
        p.poly([(0, -14), (3, 6), (0, 12), (-3, 6)], col, WHITE, 1)
        p.line((0, -10), (0, 14), WHITE, 1.5)
        return
    if kind == "w_photon":
        for dx in (-7, 0, 7):
            p.circ(dx, -2 + abs(dx) * 0.4, 4.5, col, WHITE, 1)
        return
    if kind == "w_singularity":
        p.circ(0, 0, 9, (6, 2, 14), col, 2.5)
        for a in (0.3, 2.4, 4.5):
            p.line((math.cos(a) * 9, math.sin(a) * 9), (math.cos(a + 0.9) * 14, math.sin(a + 0.9) * 14), col, 2)
        return
    if kind.startswith("skin_"):
        p.poly(SHIP_ICON_PTS["vanguard"], col, WHITE, 1.2)
        p.circ(0, 2, 2.5, WHITE)
        return
    if kind.startswith("trail_"):
        for i in range(4):
            p.line((-10 + i * 3, 12 - i * 2), (4 + i * 3, -10 - i * 2), mix(col, BLACK, 0.2 * i), 3 - i * 0.5)
        p.circ(10, -12, 3.5, WHITE, col, 1)
        return
    if kind == "w_flak":
        p.circ(0, 0, 6, col, WHITE, 1.5)
        for i in range(8):
            a = i * TAU / 8
            p.line((math.cos(a) * 8, math.sin(a) * 8), (math.cos(a) * 13, math.sin(a) * 13), col, 2)
    elif kind == "w_tesla":
        for a, b in (((0, -13), (-5, -4)), ((-5, -4), (4, -2)), ((4, -2), (-3, 8)), ((-3, 8), (1, 13))):
            p.neon(a, b, col, 1.6)
    elif kind == "firerate":
        for dy in (-6, 2, 10):
            p.poly([(0, dy - 6), (9, dy + 2), (0, dy - 1), (-9, dy + 2)], col, BLACK, 1)
    elif kind == "spower":
        pts = [(math.cos(i * TAU / 16 - math.pi / 2) * (13 if i % 2 == 0 else 6),
                math.sin(i * TAU / 16 - math.pi / 2) * (13 if i % 2 == 0 else 6)) for i in range(16)]
        p.poly(pts, col, WHITE, 1.2)
    elif kind == "speed":
        p.poly([(0, -13), (9, -1), (3, -1), (3, 8), (-3, 8), (-3, -1), (-9, -1)], col, BLACK, 1.2)
        p.line((-8, 10), (-8, 15), col, 2)
        p.line((8, 10), (8, 15), col, 2)
    elif kind == "regen":
        p.poly([(0, -13), (11, -9), (10, 5), (0, 14), (-10, 5), (-11, -9)], col, WHITE, 1.5)
        p.rect(-2, -7, 4, 13, WHITE)
        p.rect(-6, -2, 12, 4, WHITE)
    elif kind == "coinup":
        p.circ(-2, 2, 10, (255, 200, 60), (160, 100, 10), 2)
        p.circ(-2, 2, 6, (230, 170, 40))
        p.poly([(8, -12), (13, -5), (10, -5), (10, 0), (6, 0), (6, -5), (3, -5)], GREEN, BLACK, 1)
    elif kind == "luck":
        for (x, y) in ((-5, -5), (5, -5), (-5, 5), (5, 5)):
            p.circ(x, y, 5.5, col, BLACK, 1)
        p.line((0, 4), (4, 14), (40, 140, 60), 2.5)
    elif kind == "drone":
        p.poly([(-8, -3), (-16, 3), (-8, 3)], GRAY, BLACK, 1, mirror=True)
        p.circ(0, 0, 9, GRAY_D, WHITE, 1.2)
        p.circ(0, 0, 5, col)
        p.circ(-1.5, -1.5, 1.8, WHITE)
    elif kind == "revive":
        p.circ(-4, -2, 5, col, BLACK, 1)
        p.circ(4, -2, 5, col, BLACK, 1)
        p.poly([(-9, 1), (9, 1), (0, 11)], col, BLACK, 1)
        p.poly([(-9, -4), (-17, -9), (-14, 0), (-9, 0)], WHITE, GRAY, 1, mirror=True)
    elif kind.startswith("ship_"):
        p.poly(SHIP_ICON_PTS[kind[5:]], col, WHITE, 1.2)
        p.circ(0, 2, 2.5, WHITE)

_icon_cache = {}

# يجلب الأيقونة من الذاكرة المؤقتة (يرسمها مرة واحدة فقط)
def get_icon(kind, size):
    key = (kind, size)
    if key not in _icon_cache:
        _icon_cache[key] = make_sprite(size, size, draw_icon, kind, scale=size / 48.0)
    return _icon_cache[key]

def draw_heart_small(p, col):
    p.circ(-5, -3, 6, col, BLACK, 1)
    p.circ(5, -3, 6, col, BLACK, 1)
    p.poly([(-10.5, 0), (10.5, 0), (0, 11)], col, BLACK, 1)

def draw_missile_sprite(p):
    p.ell(0, 0, 3.5, 11, (210, 214, 224), BLACK, 1)
    p.poly([(0, -15), (-3.5, -7), (3.5, -7)], (255, 90, 70), BLACK, 1)
    p.poly([(-3, 4), (-8, 12), (-3, 10)], (255, 150, 60), BLACK, 1)
    p.poly([(3, 4), (8, 12), (3, 10)], (255, 150, 60), BLACK, 1)

# ================= الخلفية الكونية =================
# ثيمات الخلفية الكونية: كل 10 مراحل ثيم جديد (ألوان سديم وكواكب)
THEMES = [
    dict(name="ORION VEIL", c1=(150, 50, 200), c2=(40, 110, 230), planet=((200, 120, 70), (120, 60, 40)), planet2=((120, 160, 220), (50, 70, 130))),
    dict(name="EMERALD DRIFT", c1=(30, 190, 120), c2=(30, 110, 200), planet=((90, 170, 110), (30, 90, 70)), planet2=((220, 200, 120), (130, 100, 60))),
    dict(name="CRIMSON RIFT", c1=(220, 60, 50), c2=(240, 150, 40), planet=((200, 90, 60), (90, 30, 30)), planet2=((200, 170, 140), (110, 80, 70))),
    dict(name="AZURE DEEP", c1=(40, 130, 255), c2=(60, 220, 240), planet=((90, 150, 230), (30, 60, 130)), planet2=((240, 200, 150), (150, 100, 70))),
    dict(name="ROSE NEBULA", c1=(240, 70, 170), c2=(130, 60, 220), planet=((230, 150, 190), (110, 50, 110)), planet2=((160, 200, 230), (70, 100, 150))),
    dict(name="GOLDEN HALO", c1=(250, 190, 60), c2=(240, 100, 40), planet=((240, 200, 120), (150, 100, 50)), planet2=((130, 190, 220), (60, 100, 140))),
    dict(name="FROST VOID", c1=(130, 210, 255), c2=(120, 140, 255), planet=((200, 230, 250), (100, 140, 190)), planet2=((230, 150, 110), (140, 70, 50))),
    dict(name="TOXIC MIST", c1=(150, 230, 50), c2=(40, 170, 130), planet=((170, 210, 90), (60, 100, 50)), planet2=((200, 130, 220), (100, 60, 130))),
]

# عينة ضجيج سلسة (value noise) بتكرار دوري حتى لا يظهر خط فاصل أثناء التمرير
def _smp(g, cx, cy, u, v):
    x0 = int(u)
    y0 = int(v)
    fx = u - x0
    fy = v - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    x1 = (x0 + 1) % cx
    y1 = (y0 + 1) % cy
    x0 %= cx
    y0 %= cy
    a = g[y0][x0]
    b = g[y0][x1]
    c = g[y1][x0]
    d = g[y1][x1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy

# يولّد السديم الملون بضجيج متعدد الطبقات بدقة منخفضة ثم يكبّره بنعومة
def make_nebula(theme, seed):
    rng = random.Random(seed)
    NW, NH = 100, 78
    octs = [(3, 3), (6, 6), (12, 12), (24, 24)]
    g1 = [[[rng.random() for _ in range(cx)] for _ in range(cy)] for cx, cy in octs]
    g2 = [[[rng.random() for _ in range(cx)] for _ in range(cy)] for cx, cy in octs[:3]]
    g3 = [[rng.random() for _ in range(4)] for _ in range(4)]
    surf = pygame.Surface((NW, NH))
    c1, c2 = theme["c1"], theme["c2"]
    for y in range(NH):
        v = y / NH
        for x in range(NW):
            u = x / NW
            n = 0.0
            tot = 0.0
            amp = 0.55
            for g, (cx, cy) in zip(g1, octs):
                n += amp * _smp(g, cx, cy, u * cx, v * cy)
                tot += amp
                amp *= 0.5
            n /= tot
            m = 0.0
            tot = 0.0
            amp = 0.55
            for g, (cx, cy) in zip(g2, octs[:3]):
                m += amp * _smp(g, cx, cy, (u + 0.37) * cx, (v + 0.21) * cy)
                tot += amp
                amp *= 0.5
            m /= tot
            dust = _smp(g3, 4, 4, u * 4, v * 4)
            f1 = max(0.0, (n - 0.42) / 0.58) ** 1.5
            f2 = max(0.0, (m - 0.45) / 0.55) ** 1.4
            k = 1.0 - 0.45 * max(0.0, dust - 0.5) * 2
            core = f1 ** 3 * 0.35
            r = (4 + (c1[0] * f1 * 0.85 + c2[0] * f2 * 0.6 + 255 * core) * k)
            gg = (5 + (c1[1] * f1 * 0.85 + c2[1] * f2 * 0.6 + 255 * core) * k)
            b = (12 + (c1[2] * f1 * 0.85 + c2[2] * f2 * 0.6 + 255 * core) * k)
            surf.set_at((x, y), (min(255, int(r)), min(255, int(gg)), min(255, int(b))))
    return pygame.transform.smoothscale(surf, (WIDTH, HEIGHT))

# يرسم كوكباً بإضاءة واقعية (إضاءة لامبرت + هالة جوية + حلقات اختيارية)
def make_planet(r, c1, c2, seed, ring=False, bands=True):
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    pad = int(r * 0.85) if ring else 4
    size = 2 * r + 2 * pad
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    def draw_rings():
        for rr, col, w in ((1.45, (215, 195, 165, 150), 5), (1.65, (170, 150, 125, 120), 9),
                           (1.85, (200, 180, 150, 90), 4)):
            rect = pygame.Rect(0, 0, int(rr * r * 2), int(rr * r * 0.7))
            rect.center = (cx, cy)
            pygame.draw.ellipse(s, col, rect, w)

    if ring:
        draw_rings()
    lx, ly, lz = -0.55, -0.5, 0.65
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            d2 = x * x + y * y
            if d2 > r * r:
                continue
            nx = x / r
            ny = y / r
            nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
            diff = max(0.0, nx * lx + ny * ly + nz * lz)
            if bands:
                tex = 0.5 + 0.5 * math.sin(ny * 9 + 1.6 * math.sin(nx * 3 + ph[0]) + 0.8 * math.sin(ny * 17 + nx * 5 + ph[1]))
            else:
                tex = 0.5 + 0.5 * math.sin(nx * 11 + ph[0]) * math.sin(ny * 9 + ph[1]) * math.sin(nx * ny * 20 + ph[2])
            base = mix(c1, c2, tex)
            light = 0.06 + 0.94 * diff ** 0.9
            rim = (1 - nz) ** 3 * (0.3 + diff) * 0.6
            col = [min(255, int(base[i] * light + (140 + c1[i] * 0.4) * rim * 0.5)) for i in range(3)]
            edge = r - math.sqrt(d2)
            a = 255 if edge > 1 else int(255 * max(0.0, edge))
            s.set_at((cx + x, cy + y), (col[0], col[1], col[2], a))
    if ring:
        s.set_clip(pygame.Rect(0, cy, size, size - cy))
        draw_rings()
        s.set_clip(None)
    return s

# تعتيم خفيف على الأطراف لعمق سينمائي
def make_vignette():
    sm = pygame.Surface((32, 24), pygame.SRCALPHA)
    for y in range(24):
        for x in range(32):
            dx = (x - 15.5) / 16
            dy = (y - 11.5) / 12
            d = math.hypot(dx, dy)
            sm.set_at((x, y), (0, 0, 8, clamp(int((d - 0.6) * 200), 0, 170)))
    return pygame.transform.smoothscale(sm, (WIDTH, HEIGHT))

def draw_far_ship(p, col, kind, seed):
    """سفينة حربية بعيدة (ظل مظلم بأضواء صغيرة) لخلفية المعركة."""
    rng = random.Random(seed)
    hi = shade(col, 1.8)
    if kind == 0:  # مدمرة
        p.gpoly([(0, -60), (-14, -30), (-18, 30), (-10, 58), (10, 58), (18, 30), (14, -30)], hi, col, BLACK, 2)
        p.rect(-28, -8, 9, 36, shade(col, 0.7), BLACK, 1, mirror=True)
    elif kind == 1:  # حاملة طائرات
        p.gpoly([(-40, -40), (40, -40), (52, 0), (40, 50), (-40, 50), (-52, 0)], hi, col, BLACK, 2)
        for x in (-30, -10, 10, 30):
            p.rect(x - 4, -52, 8, 14, shade(col, 0.7), BLACK, 1)
    else:  # طرّاد
        p.gpoly([(0, -70), (-30, 10), (-36, 50), (-10, 36), (0, 56), (10, 36), (36, 50), (30, 10)], hi, col, BLACK, 2)
    for _ in range(14):
        p.circ(rng.uniform(-12, 12), rng.uniform(-30, 40), 0.9, (255, 220, 140))
    p.circ(-8, 56, 2.4, (120, 200, 255))
    p.circ(8, 56, 2.4, (120, 200, 255))


class WarLayer:
    """معركة بعيدة في الخلفية: سفن حربية ضخمة وأشعة ليزر وانفجارات صامتة (أجواء عام 2500)."""
    def __init__(self):
        self.ships = [self._new(True) for _ in range(6)]
        self.lasers = []
        self.booms = []

    def _new(self, init=False):
        kind = random.randint(0, 2)
        col = random.choice(((52, 60, 92), (84, 48, 60), (44, 80, 80), (70, 60, 100)))
        spr = make_sprite(160, 180, draw_far_ship, col, kind, random.random(), scale=random.uniform(0.7, 1.0))
        y = random.uniform(-100, HEIGHT) if init else random.uniform(-260, -140)
        return [spr, random.uniform(40, WIDTH - 40), y, random.uniform(0.12, 0.32)]

    def update(self, boost):
        for sh in self.ships:
            sh[2] += sh[3] * boost
        for i, sh in enumerate(self.ships):
            if sh[2] > HEIGHT + 200:
                self.ships[i] = self._new()
        if random.random() < 0.06 and len(self.lasers) < 8:
            a, b = random.sample(self.ships, 2)
            col = random.choice(((255, 90, 90), (90, 200, 255), (255, 200, 90)))
            self.lasers.append([a[1], a[2], b[1] + random.uniform(-30, 30), b[2] + random.uniform(-40, 40), 10, col])
        for lz in self.lasers:
            lz[4] -= 1
        for lz in self.lasers[:]:
            if lz[4] <= 0:
                self.booms.append([lz[2], lz[3], 14, lz[5]])
                self.lasers.remove(lz)
        for bm in self.booms:
            bm[2] -= 1
        self.booms = [bm for bm in self.booms if bm[2] > 0]

    def draw(self, surf):
        for spr, x, y, _ in self.ships:
            surf.blit(spr, (int(x - 80), int(y - 90)))
        for x1, y1, x2, y2, life, col in self.lasers:
            f = life / 10.0
            pygame.draw.line(surf, shade(col, 0.5 * f + 0.2), (x1, y1), (x2, y2), 3)
            pygame.draw.line(surf, shade(col, f), (x1, y1), (x2, y2), 1)
        for x, y, life, col in self.booms:
            add_glow(surf, x, y, 6 + (14 - life) * 2, shade(col, life / 14.0))


# الخلفية الكونية: سديم، نجوم متلألئة بثلاث طبقات (بعيدة/متوسطة/قريبة)، كواكب، مذنبات
class Space:
    def __init__(self):
        self.stars = []
        for n, spd, sz in ((90, 0.35, 1), (60, 0.9, 1), (26, 1.7, 2)):
            for _ in range(n):
                self.stars.append([random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
                                   spd * random.uniform(0.8, 1.2), sz, random.uniform(0, 6.28),
                                   random.choice(((255, 255, 255), (190, 215, 255), (255, 235, 200), (200, 255, 255)))])
        self.theme = -1
        self.neb = None
        self.planets = []
        self.psprites = []
        self.pi = 0
        self.scroll = 0.0
        self.comets = []
        self.vig = make_vignette()
        self.t = 0
        self.war = WarLayer()
        self.boost = 1.0
        self.bolt = None

    def set_theme(self, idx):
        idx %= len(THEMES)
        if idx == self.theme:
            return
        show_loading("ENTERING SECTOR: " + THEMES[idx]["name"])
        th = THEMES[idx]
        self.theme = idx
        self.neb = make_nebula(th, idx * 131 + 7)
        self.psprites = [
            make_planet(96, th["planet"][0], th["planet"][1], idx + 1, False),
            make_planet(38, (175, 165, 155), (90, 80, 80), idx + 9, False, False),
            make_planet(56, th["planet2"][0], th["planet2"][1], idx + 5, True),
        ]
        self.planets = []
        self.pi = 0
        for y in (random.randint(120, 400), random.randint(-500, -200)):
            self.planets.append(self._new_planet(y))

    def _new_planet(self, y):
        spr = self.psprites[self.pi % len(self.psprites)]
        self.pi += 1
        spd = clamp(0.55 - spr.get_width() * 0.0016, 0.2, 0.5)
        return [spr, random.randint(100, WIDTH - 100), y, spd]

    def update(self, boost=1.0):
        self.t += 1
        self.boost = boost
        self.war.update(boost)
        if self.bolt:  # صاعقة أيونية عابرة
            self.bolt[1] -= 1
            if self.bolt[1] <= 0:
                self.bolt = None
        elif random.random() < 0.002:
            x = random.uniform(100, WIDTH - 100)
            pts = [(x, 0)]
            y = 0
            end = random.uniform(250, 550)
            while y < end:
                y += random.uniform(30, 60)
                x += random.uniform(-40, 40)
                pts.append((x, y))
            self.bolt = [pts, 9]
        self.scroll += 0.35 * boost
        for s in self.stars:
            s[1] += s[2] * boost
            if s[1] > HEIGHT:
                s[1] = -2
                s[0] = random.uniform(0, WIDTH)
        for pl in self.planets:
            pl[2] += pl[3] * boost
        for i, pl in enumerate(self.planets):
            if pl[2] - pl[0].get_height() // 2 > HEIGHT:
                self.planets[i] = self._new_planet(-pl[0].get_height() - random.randint(100, 500))
        if random.random() < 0.0025 and len(self.comets) < 2:
            self.comets.append([random.uniform(100, WIDTH), -20, random.uniform(-3, 3), random.uniform(8, 12)])
        for c in self.comets[:]:
            c[0] += c[2]
            c[1] += c[3]
            if c[1] > HEIGHT + 100:
                self.comets.remove(c)

    def draw(self, surf):
        if self.neb is None:
            surf.fill((4, 5, 12))
        else:
            y = int(self.scroll) % HEIGHT
            surf.blit(self.neb, (0, y - HEIGHT))
            surf.blit(self.neb, (0, y))
        tt = self.t * 0.05
        for sx, sy, spd, sz, ph, col in self.stars:
            v = 0.65 + 0.35 * math.sin(tt * (1 + spd) + ph)
            c = (int(col[0] * v), int(col[1] * v), int(col[2] * v))
            if self.boost > 1.8:  # سرعة الانتقال (warp): النجوم تتحول لخطوط
                pygame.draw.line(surf, c, (sx, sy), (sx, sy - spd * self.boost * 7), sz)
                continue
            if sz == 1:
                surf.set_at((int(sx), int(sy)), c)
            else:
                pygame.draw.rect(surf, c, (int(sx), int(sy), 2, 2))
                if v > 0.9:
                    pygame.draw.line(surf, shade(c, 0.5), (sx - 4, sy + 1), (sx + 5, sy + 1))
                    pygame.draw.line(surf, shade(c, 0.5), (sx + 1, sy - 4), (sx + 1, sy + 5))
        for spr, px, py, _ in self.planets:
            surf.blit(spr, (int(px - spr.get_width() / 2), int(py - spr.get_height() / 2)))
        self.war.draw(surf)
        for cx, cy, vx, vy in self.comets:
            for i in range(10):
                f = 1 - i / 10
                add_glow(surf, cx - vx * i * 2.4, cy - vy * i * 2.4, int(3 + 5 * f), (int(150 * f), int(190 * f), int(255 * f)))
        if self.bolt:
            pts, life = self.bolt
            if life > 6:
                surf.fill((16, 22, 40), special_flags=pygame.BLEND_RGB_ADD)
            for i in range(len(pts) - 1):
                pygame.draw.line(surf, (110, 150, 255), pts[i], pts[i + 1], 5)
                pygame.draw.line(surf, (230, 240, 255), pts[i], pts[i + 1], 2)
            add_glow(surf, pts[0][0], pts[0][1], 60, (80, 100, 220))
        surf.blit(self.vig, (0, 0))

space = None

# ================= الجسيمات والنصوص الطافية =================
particles = []
texts = []
_smoke_cache = {}

# جسيم: أساس الانفجارات (نار، شرر، دخان، حطام، موجة صدمة، وميض)
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "kind", "size", "col", "drag", "grow")

    def __init__(self, x, y, vx, vy, life, kind, size, col, drag=0.95, grow=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.kind, self.size, self.col, self.drag, self.grow = kind, size, col, drag, grow

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.drag
        self.vy *= self.drag
        self.size += self.grow
        self.life -= 1

    def draw(self, s):
        f = self.life / self.max
        k = self.kind
        x, y = int(self.x), int(self.y)
        if k == "fire":
            add_glow(s, x, y, max(3, int(self.size * (0.45 + 0.55 * f))), mix((70, 10, 0), self.col, f))
        elif k == "spark":
            pygame.draw.line(s, mix((120, 40, 10), self.col, f), (x, y),
                             (int(self.x - self.vx * 1.8), int(self.y - self.vy * 1.8)), 2)
        elif k == "flash":
            add_glow(s, x, y, int(self.size), shade(self.col, f))
        elif k == "ring":
            r = int(self.size * (1 - f) + 4)
            pygame.draw.circle(s, shade(self.col, f), (x, y), r, max(1, int(4 * f)))
        elif k == "smoke":
            r = max(4, int(self.size) // 4 * 4)
            spr = _smoke_cache.get(r)
            if spr is None:
                spr = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(spr, (66, 62, 74, 255), (r, r), r)
                _smoke_cache[r] = spr
            spr.set_alpha(int(100 * f))
            s.blit(spr, (x - r, y - r))
        elif k == "debris":
            pygame.draw.rect(s, shade(self.col, 0.4 + 0.6 * f), (x, y, int(self.size), int(self.size)))

# انفجار واقعي: وميض + موجة صدمة + نار + شرر + دخان + حطام
def explode(x, y, size=1.0, col=None):
    if len(particles) > 700:
        size = min(size, 0.6)
    particles.append(Particle(x, y, 0, 0, 8, "flash", int(46 * size) + 8, (255, 230, 180)))
    particles.append(Particle(x, y, 0, 0, int(22 + 10 * size), "ring", int(55 * size) + 10, (255, 170, 80)))
    for _ in range(int(8 + 12 * size)):
        a = random.uniform(0, TAU)
        sp = random.uniform(0.4, 4.5) * (0.6 + size * 0.5)
        particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(18, 38),
                                  "fire", int(random.randint(10, 18) * (0.6 + size * 0.5)),
                                  random.choice(FIRE_COLS), 0.93))
    for _ in range(int(6 + 8 * size)):
        a = random.uniform(0, TAU)
        sp = random.uniform(3, 10)
        particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(14, 30),
                                  "spark", 2, (255, 225, 130), 0.93))
    if size >= 1.0:
        for _ in range(int(3 + 3 * size)):
            a = random.uniform(0, TAU)
            sp = random.uniform(0.3, 2)
            particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(40, 70),
                                      "smoke", 12, GRAY, 0.96, 0.35))
    for _ in range(int(2 + 3 * size)):  # جمرات طويلة العمر
        a = random.uniform(0, TAU)
        sp = random.uniform(0.5, 3)
        particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp - 0.6, random.randint(45, 85),
                                  "fire", 4, (255, 170, 70), 0.97))
    if size >= 1.6:
        particles.append(Particle(x, y, 0, 0, 40, "ring", int(110 * size), (255, 220, 160)))
    dc = col or (150, 150, 165)
    for _ in range(int(3 + 4 * size)):
        a = random.uniform(0, TAU)
        sp = random.uniform(1, 5)
        particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(25, 50),
                                  "debris", random.randint(2, 5), dc, 0.96))

def spark(x, y, col, n=5):
    for _ in range(n):
        a = random.uniform(0, TAU)
        sp = random.uniform(1.5, 5)
        particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(8, 16),
                                  "spark", 2, col, 0.9))

# ================= الرصاص =================
MISSILE_SPR = None

# يرسم رصاصة على شكل كبسولة مضيئة
def capsule(s, x, y, ux, uy, half, w, col, core):
    a = (x - ux * half, y - uy * half)
    b = (x + ux * half, y + uy * half)
    pygame.draw.line(s, col, a, b, w)
    pygame.draw.circle(s, col, (int(a[0]), int(a[1])), w // 2)
    pygame.draw.circle(s, col, (int(b[0]), int(b[1])), w // 2)
    pygame.draw.line(s, core, a, b, max(1, w // 3))

# الرصاصة (للاعب أو للعدو): الحركة، التوجيه، الانفجار عند انتهاء العمر، والرسم حسب النوع
class Bullet:
    """رصاصة (للاعب أو للعدو). kind يحدد الشكل. seek = تلاحق اللاعب، life = عمرها بالإطارات."""
    def __init__(self, x, y, vx, vy, dmg, kind, friendly, r=5, pierce=0, homing=False, col=None, seek=False, life=None):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.kind, self.friendly, self.r = dmg, kind, friendly, r
        self.pierce, self.homing = pierce, homing
        self.seek, self.life = seek, life
        self.col = col or (255, 70, 100)
        self.hit = set()
        self.age = 0
        self.dead = False

    def update(self, g):
        self.age += 1
        # انتهاء العمر: الألغام والقذائف المتشظية تنفجر
        if self.life is not None and self.age >= self.life:
            self.dead = True
            if self.kind == "mine":
                g.mine_burst(self)
            elif self.kind == "flak":
                g.flak_burst(self)
            elif self.kind == "hole":
                g.hole_burst(self)
            return
        # رصاص العدو الملاحق: يدور ببطء نحو أقرب لاعب
        if self.seek:
            des = g.aim(self.x, self.y)
            cur = math.atan2(self.vy, self.vx)
            diff = (des - cur + math.pi) % TAU - math.pi
            cur += clamp(diff, -0.035, 0.035)
            sp = math.hypot(self.vx, self.vy)
            self.vx = math.cos(cur) * sp
            self.vy = math.sin(cur) * sp
        # صواريخ اللاعب الموجهة نحو أقرب هدف
        if self.homing:
            tgt = g.nearest_target(self.x, self.y)
            if tgt is not None:
                des = math.atan2(tgt.y - self.y, tgt.x - self.x)
                cur = math.atan2(self.vy, self.vx)
                diff = (des - cur + math.pi) % TAU - math.pi
                cur += clamp(diff, -0.09, 0.09)
                sp = min(math.hypot(self.vx, self.vy) + 0.2, 13.0)
                self.vx = math.cos(cur) * sp
                self.vy = math.sin(cur) * sp
            if self.age % 2 == 0:
                particles.append(Particle(self.x - self.vx, self.y - self.vy, random.uniform(-0.3, 0.3),
                                          random.uniform(-0.3, 0.3), 14, "fire", 7, (255, 150, 60), 0.9))
        self.x += self.vx
        self.y += self.vy

    def onscreen(self):
        return -90 < self.x < WIDTH + 90 and -130 < self.y < HEIGHT + 90

    def draw(self, s):
        k = self.kind
        x, y = self.x, self.y
        sp = math.hypot(self.vx, self.vy) or 1.0
        ux, uy = self.vx / sp, self.vy / sp
        if k == "laser":
            add_glow(s, x, y, 18, (0, 130, 190))
            add_glow(s, x - ux * 14, y - uy * 14, 12, (0, 80, 130))
            capsule(s, x, y, ux, uy, 12, 7, (40, 170, 240), WHITE)
        elif k == "spread":
            add_glow(s, x, y, 15, (190, 130, 20))
            pygame.draw.line(s, (255, 150, 30), (x, y), (x - ux * 14, y - uy * 14), 3)
            pygame.draw.circle(s, (255, 205, 80), (int(x), int(y)), 5)
            pygame.draw.circle(s, WHITE, (int(x), int(y)), 2)
        elif k == "rapid":
            add_glow(s, x, y, 11, (170, 30, 110))
            capsule(s, x, y, ux, uy, 7, 5, (255, 70, 170), WHITE)
        elif k == "plasma":
            pul = 1 + 0.12 * math.sin(self.age * 0.5)
            add_glow(s, x, y, int(34 * pul), (110, 40, 190))
            pygame.draw.circle(s, (170, 90, 240), (int(x), int(y)), int(11 * pul))
            pygame.draw.circle(s, (235, 205, 255), (int(x), int(y)), 6)
            for i in range(3):
                a = self.age * 0.3 + i * 2.09
                pygame.draw.circle(s, WHITE, (int(x + math.cos(a) * 15), int(y + math.sin(a) * 15)), 2)
        elif k == "missile":
            add_glow(s, x - ux * 8, y - uy * 8, 14, (200, 100, 30))
            ang = math.degrees(math.atan2(-ux, -uy))
            img = pygame.transform.rotate(MISSILE_SPR, ang)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        elif k == "flak":
            add_glow(s, x, y, 18, (200, 90, 20))
            pygame.draw.circle(s, (255, 150, 60), (int(x), int(y)), 7)
            pygame.draw.circle(s, (90, 40, 10), (int(x), int(y)), 7, 2)
            pygame.draw.circle(s, WHITE, (int(x), int(y)), 3)
        elif k == "lance":
            add_glow(s, x, y, 26, (60, 170, 255))
            pygame.draw.line(s, (60, 170, 255), (x - ux * 40, y - uy * 40), (x + ux * 14, y + uy * 14), 6)
            pygame.draw.line(s, WHITE, (x - ux * 40, y - uy * 40), (x + ux * 14, y + uy * 14), 2)
        elif k == "photon":
            add_glow(s, x, y, 18, (150, 60, 230))
            add_glow(s, x - ux * 10, y - uy * 10, 12, (90, 40, 160))
            pygame.draw.circle(s, (210, 150, 255), (int(x), int(y)), 6)
            pygame.draw.circle(s, WHITE, (int(x), int(y)), 3)
        elif k == "hole":
            pul = 1 + 0.1 * math.sin(self.age * 0.4)
            add_glow(s, x, y, int(70 * pul), (80, 30, 150))
            pygame.draw.circle(s, (5, 2, 14), (int(x), int(y)), int(15 * pul))
            rect = pygame.Rect(int(x) - 24, int(y) - 24, 48, 48)
            for i in range(4):
                a = self.age * 0.25 + i * 1.57
                pygame.draw.arc(s, (190, 120, 255), rect, a, a + 1.0, 3)
        elif k == "special":
            add_glow(s, x, y, 22, (0, 140, 190))
            pygame.draw.line(s, (60, 190, 240), (x, y), (x - ux * 20, y - uy * 20), 5)
            pygame.draw.circle(s, (80, 220, 255), (int(x), int(y)), 7)
            pygame.draw.circle(s, WHITE, (int(x), int(y)), 3)
        elif k == "orb":
            add_glow(s, x, y, 16, shade(self.col, 0.7))
            pygame.draw.circle(s, shade(self.col, 0.75), (int(x), int(y)), 7)
            pygame.draw.circle(s, self.col, (int(x), int(y)), 7, 2)
            pygame.draw.circle(s, mix(self.col, WHITE, 0.8), (int(x), int(y)), 3)
        elif k == "bolt":
            add_glow(s, x, y, 20, shade(self.col, 0.7))
            capsule(s, x, y, ux, uy, 11, 8, self.col, mix(self.col, WHITE, 0.85))
        elif k == "needle":
            add_glow(s, x, y, 12, shade(self.col, 0.6))
            capsule(s, x, y, ux, uy, 15, 4, self.col, WHITE)
        elif k == "mine":
            pul = 0.6 + 0.4 * math.sin(self.age * 0.3)
            add_glow(s, x, y, int(24 * (0.8 + 0.4 * pul)), shade(self.col, 0.8))
            for i in range(8):
                a = i * TAU / 8 + self.age * 0.05
                pygame.draw.line(s, (170, 170, 185), (x, y), (x + math.cos(a) * 14, y + math.sin(a) * 14), 3)
            pygame.draw.circle(s, (50, 52, 66), (int(x), int(y)), 9)
            pygame.draw.circle(s, mix(self.col, WHITE, 0.4 * pul), (int(x), int(y)), 4)

# ================= الجوائز =================
# احتمالات سقوط الجوائز (الرقم الأكبر = أكثر شيوعاً)
PICK_WEIGHTS = [("coin", 34), ("health", 10), ("shield", 8), ("special", 10), ("gem", 6),
                ("power", 8), ("rapid", 8), ("triple", 7), ("bomb", 4), ("magnet", 5)]

# جائزة تسقط من العدو، لكل نوع شكل خاص، والمغناطيس يجذبها نحوك
class Pickup:
    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.t = random.randint(0, 100)
        self.dead = False
        self.vx = random.uniform(-0.8, 0.8)

    def update(self, g):
        self.t += 1
        self.x += self.vx
        self.vx *= 0.97
        self.y += 1.6
        for p in g.players:
            if p.alive and p.buffs["magnet"] > 0:
                dx, dy = p.x - self.x, p.y - self.y
                d = math.hypot(dx, dy)
                if d < 380 and d > 1:
                    self.x += dx / d * 5.5
                    self.y += dy / d * 5.5
        if g.clear_timer > 0:
            for p in g.players:
                if p.alive:
                    dx, dy = p.x - self.x, p.y - self.y
                    d = math.hypot(dx, dy) or 1
                    self.x += dx / d * 9
                    self.y += dy / d * 9
        if self.y > HEIGHT + 40:
            self.dead = True

    def draw(self, s):
        col = ICON_COL[self.kind]
        pul = 1 + 0.12 * math.sin(self.t * 0.12)
        add_glow(s, self.x, self.y, int(30 * pul), shade(col, 0.55))
        spr = get_icon(self.kind, 48)
        s.blit(spr, spr.get_rect(center=(int(self.x), int(self.y + math.sin(self.t * 0.1) * 2))))

# ================= اللاعب =================
PLAYER_SPR = {}
DRONE_SPR = None
# لون وميض فوهة كل سلاح
WEAPON_COL = dict(laser=(60, 200, 255), spread=(255, 190, 60), rapid=(255, 70, 170), plasma=(190, 110, 255),
                  missile=(255, 150, 60), flak=(255, 150, 60), tesla=(120, 200, 255), lance=(90, 190, 255),
                  photon=(190, 110, 255), singularity=(150, 90, 230))


def get_player_sprite(pid, ship, tier, skin):
    """صورة المركبة: تُرسم عند أول طلب ثم تُخزَّن (المفتاح يشمل المظهر)."""
    key = (pid, ship, tier, skin)
    if key not in PLAYER_SPR:
        pal = skin_pal(SHIP_DEFS[ship]["pals"][pid], skin)
        PLAYER_SPR[key] = make_sprite(190, 170, SHIP_DRAW[ship], pal, tier)
    return PLAYER_SPR[key]

# أنواع التعزيزات المؤقتة التي تظهر في الواجهة
BUFF_KINDS = ("power", "rapid", "triple", "magnet", "shield")

# اللاعب: الحركة والإطلاق والدرع والطائرات المرافقة والإحياء
class Player:
    """مركبة اللاعب: حركة، إطلاق نار، درع، طائرات مرافقة، إحياء."""
    def __init__(self, pid):
        self.pid = pid
        self.reset_full(WIDTH // 2)

    def stats(self):
        """يحسب قدرات المركبة من المركبة المختارة وترقيات المتجر."""
        sd = SHIP_DEFS[save["ship"]]
        self.speed = sd["speed"] + 0.5 * save["speed_lv"]
        self.max_health = max(2, save["max_health"] + sd["hp"])
        self.shield_max = save["max_shield"] + sd["shield"] + 50 * save["aegis"]
        self.max_special = save["max_special"]

    def dmg_base(self):
        """الضرر الأساسي = قوة السلاح × مضاعف المركبة."""
        return (1 + 0.5 * (save["power"] - 1)) * SHIP_DEFS[save["ship"]]["dmg"]

    def drone_pos(self, i):
        """مكان الطائرة المرافقة رقم i حول المركبة."""
        ox = (-62, 62, 0)[i]
        oy = (22, 22, -92)[i]
        return self.x + ox, self.y + oy + math.sin((self.drone_t + i * 20) * 0.08) * 5

    def reset_full(self, x):
        self.x, self.y = x, HEIGHT - 110
        self.stats()
        self.health = self.max_health
        self.shield = self.shield_max
        self.shield_on = False
        self.specials = self.max_special
        self.cool = 0
        self.invuln = 90
        self.alive = True
        self.buffs = {k: 0 for k in BUFF_KINDS}
        self.hr = 15
        self.drone_t = 0

    def next_level(self, x):
        self.x, self.y = x, HEIGHT - 110
        self.stats()
        if not self.alive:
            self.alive = True
            self.health = max(1, (self.max_health + 1) // 2)
        else:
            self.health = min(self.max_health, self.health + 1)
        self.shield = min(self.shield_max, max(self.shield, self.shield_max * 0.5))
        self.specials = self.max_special
        self.invuln = 120
        self.shield_on = False
        self.cool = 0

    def keys(self, two):
        if self.pid == 0:
            if two:
                return dict(l=(pygame.K_a,), r=(pygame.K_d,), u=(pygame.K_w,), d=(pygame.K_s,), fire=pygame.K_SPACE)
            return dict(l=(pygame.K_a, pygame.K_LEFT), r=(pygame.K_d, pygame.K_RIGHT),
                        u=(pygame.K_w, pygame.K_UP), d=(pygame.K_s, pygame.K_DOWN), fire=pygame.K_SPACE)
        return dict(l=(pygame.K_LEFT,), r=(pygame.K_RIGHT,), u=(pygame.K_UP,), d=(pygame.K_DOWN,), fire=pygame.K_RETURN)

    def update(self, g):
        if not self.alive:
            return
        ks = pygame.key.get_pressed()
        kk = self.keys(len(g.players) > 1)
        dx = dy = 0
        if any(ks[k] for k in kk["l"]):
            dx -= 1
        if any(ks[k] for k in kk["r"]):
            dx += 1
        if any(ks[k] for k in kk["u"]):
            dy -= 1
        if any(ks[k] for k in kk["d"]):
            dy += 1
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = clamp(self.x + dx * self.speed, 50, WIDTH - 50)
        self.y = clamp(self.y + dy * self.speed, 140, HEIGHT - 60)
        if self.cool > 0:
            self.cool -= 1
        if self.invuln > 0:
            self.invuln -= 1
        for k in BUFF_KINDS:
            if self.buffs[k] > 0:
                self.buffs[k] -= 1
        # الدرع: يستهلك طاقة وهو مفعّل ويتجدد وهو مغلق (التجدد يتحسن من المتجر)
        if self.shield_on:
            self.shield -= 0.35
            if self.shield <= 0:
                self.shield = 0
                self.shield_on = False
        else:
            self.shield = min(self.shield_max, self.shield + 0.1 + 0.05 * save["regen_lv"])
        # الطائرات المرافقة تطلق رصاصاً صغيراً تلقائياً
        self.drone_t += 1
        for i in range(save["drones"]):
            if (self.drone_t + i * 9) % 28 == 0:
                px, py = self.drone_pos(i)
                g.pb.append(Bullet(px, py - 14, 0, -13, 0.45 * self.dmg_base() * (2 if save["drone2"] else 1), "rapid", True, 4))
        if save["autofire"] or ks[kk["fire"]]:
            self.shoot(g)

    def shoot(self, g):
        if self.cool > 0:
            return
        w = save["equipped"]
        pw = save["power"]
        dmg = self.dmg_base()
        if self.buffs["power"] > 0:
            dmg *= 2
        x, y = self.x, self.y - 60
        P = g.pb
        cool = 12
        if w == "laser":
            n = 1 + min(4, (pw - 1) // 5)
            for i in range(n):
                P.append(Bullet(x + (i - (n - 1) / 2) * 15, y, 0, -13, dmg, "laser", True, 5))
            cool = 12
        elif w == "spread":
            n = 3 + 2 * min(3, (pw - 1) // 7)
            arc = 0.45 + 0.07 * n
            for i in range(n):
                a = -math.pi / 2 + (i - (n - 1) / 2) * arc / (n - 1)
                P.append(Bullet(x, y + 10, math.cos(a) * 10.5, math.sin(a) * 10.5, dmg * 0.75, "spread", True, 5))
            cool = 17
        elif w == "rapid":
            n = 1 + (pw >= 10) + (pw >= 20)
            for i in range(n):
                P.append(Bullet(x + (i - (n - 1) / 2) * 16, y, 0, -15, dmg * 0.5, "rapid", True, 4))
            cool = max(4, 7 - pw // 10)
        elif w == "plasma":
            P.append(Bullet(x, y - 5, 0, -8, dmg * 3.2, "plasma", True, 11, pierce=4))
            cool = 30
        elif w == "missile":
            n = 2 + 2 * (pw >= 12)
            for i in range(n):
                off = (i - (n - 1) / 2)
                P.append(Bullet(x + off * 12, y + 15, off * 1.6, -7, dmg * 2.2, "missile", True, 7, homing=True))
            cool = 26
        elif w == "flak":
            # قذيفة تنفجر بعد قليل إلى شظايا
            n = 1 + (pw >= 15)
            for i in range(n):
                P.append(Bullet(x + (i - (n - 1) / 2) * 20, y, 0, -9, dmg * 1.2, "flak", True, 8, life=26))
            cool = 22
        elif w == "tesla":
            g.tesla(self, dmg)
            cool = 20
        elif w == "lance":
            # رمح ضوئي سريع يخترق كل شيء
            P.append(Bullet(x, y - 10, 0, -22, dmg * 4.0, "lance", True, 6, pierce=99))
            cool = 34
        elif w == "photon":
            # ثلاث كرات فوتونية تلاحق الأهداف
            for i in range(3):
                a = -math.pi / 2 + (i - 1) * 0.18
                P.append(Bullet(x, y + 8, math.cos(a) * 9, math.sin(a) * 9, dmg * 1.4, "photon", True, 6, pierce=1, homing=True))
            cool = 16
        elif w == "singularity":
            # ثقب أسود صغير يسحب الأعداء ويؤذيهم ثم ينفجر
            P.append(Bullet(x, y - 10, 0, -4.5, dmg * 0.6, "hole", True, 16, pierce=999, life=110))
            cool = 70
        if self.buffs["triple"] > 0:
            for a in (-0.3, 0.3):
                P.append(Bullet(x, y + 12, math.sin(a) * 12, -math.cos(a) * 12, dmg * 0.6, "laser", True, 5))
        particles.append(Particle(self.x, self.y - 64, 0, 0, 4, "flash", 20, WEAPON_COL.get(w, (120, 200, 255))))
        mult = (0.5 if self.buffs["rapid"] > 0 else 1.0) * SHIP_DEFS[save["ship"]]["cool"] * (1 - 0.04 * save["firerate_lv"])
        self.cool = max(2, int(cool * mult))
        sfx(w, 45)

    def special(self, g):
        if not self.alive or self.specials <= 0:
            return
        self.specials -= 1
        dmg = 6 + save["power"] * 1.5 + 3 * save["spower_lv"]
        for i in range(15):
            a = math.radians(-90 + (i - 7) * 11)
            g.pb.append(Bullet(self.x, self.y - 40, math.cos(a) * 11, math.sin(a) * 11, dmg, "special", True, 8, pierce=3))
        explode(self.x, self.y - 40, 0.5)
        sfx("special", 100)

    def toggle_shield(self):
        if self.alive and self.shield > 15:
            self.shield_on = not self.shield_on
            sfx("shield", 100)

    def hurt(self, g, n=1):
        if not self.alive or self.invuln > 0:
            return
        if self.buffs["shield"] > 0:
            self.invuln = 12
            spark(self.x, self.y - 30, (120, 220, 255), 6)
            sfx("shield", 60)
            return
        if self.shield_on and self.shield > 0:
            self.shield -= 22 * n
            if self.shield <= 0:
                self.shield = 0
                self.shield_on = False
            self.invuln = 20
            spark(self.x, self.y - 30, (120, 220, 255), 8)
            particles.append(Particle(self.x, self.y, 0, 0, 14, "ring", 60, (80, 190, 255)))
            sfx("shield", 60)
            return
        self.health -= n
        self.invuln = 100
        g.shake = max(g.shake, 14)
        g.hurt_t = 18
        sfx("hurt", 80)
        explode(self.x, self.y, 0.6)
        if self.health <= 0:
            # رمز الإحياء من المتجر: يعيدك للحياة مرة واحدة
            if save["revives"] > 0:
                save["revives"] -= 1
                write_save()
                self.health = max(2, (self.max_health + 1) // 2)
                self.invuln = 180
                explode(self.x, self.y, 1.2)
                sfx("powerup")
                texts.append([self.x, self.y - 70, "REVIVED!", GREEN, 80])
                return
            self.alive = False
            self.health = 0
            explode(self.x, self.y, 1.8)
            sfx("die", 200)
            g.shake = 26

    def draw(self, s, anim):
        if not self.alive:
            return
        if self.invuln > 0 and self.invuln < 90 and (self.invuln // 4) % 2 == 0:
            return
        ship = save["ship"]
        fl = trail_color(SHIP_DEFS[ship]["pals"][self.pid], anim)
        pw = save["power"]
        tier = 0 if pw < 10 else 1 if pw < 20 else 2
        engines = [(-9, 5, 30), (9, 5, 30), (-36, 3, 18), (36, 3, 18)]
        if tier >= 1:
            engines += [(-56, 3, 20), (56, 3, 20)]
        if tier >= 2:
            engines += [(-80, 3, 22), (80, 3, 22)]
        for ox, w, L in engines:
            draw_flame(s, self.x + ox, self.y + 58 + (-4 if abs(ox) > 20 else 0) + (6 if abs(ox) > 70 else 0), w, L, fl, anim + ox)
        if anim % 2 == 0:  # أثر المحرك المتلاشي
            particles.append(Particle(self.x + random.choice((-9, 9)), self.y + 70, random.uniform(-0.3, 0.3),
                                      random.uniform(1.5, 3), 16, "fire", 6, fl, 0.94))
        spr = get_player_sprite(self.pid, ship, tier, save["skin"])
        s.blit(spr, spr.get_rect(center=(int(self.x), int(self.y))))
        for i in range(save["drones"]):
            px, py = self.drone_pos(i)
            add_glow(s, px, py, 20, (0, 100, 150))
            s.blit(DRONE_SPR, DRONE_SPR.get_rect(center=(int(px), int(py))))
        if self.shield_on and self.shield > 0 or self.buffs["shield"] > 0:
            # فقاعة درع هولوغرافية: توهج + حلقة + أقواس دوّارة
            add_glow(s, self.x, self.y, 78, (20, 90, 180))
            pygame.draw.circle(s, (90, 190, 255), (int(self.x), int(self.y)), 62, 1)
            rect = pygame.Rect(int(self.x) - 60, int(self.y) - 60, 120, 120)
            for i in range(3):
                a0 = anim * 0.08 + i * 2.094
                pygame.draw.arc(s, (170, 235, 255), rect, a0, a0 + 0.9, 3)

# ================= الأعداء والكويكبات =================
ENEMY_SPR = {}
DIFF_HP = (0.8, 1.0, 1.35)
DIFF_BUL = (0.85, 1.0, 1.15)

# العدو: يتحرك حسب نوعه ويطلق النار، ويمكن أن يكون «نخبة» أقوى بـ 3-6 أضعاف
class Enemy:
    def __init__(self, typ, x, y, level):
        d = ENEMY_DEFS[typ]
        self.typ = typ
        self.x = self.x0 = x
        self.y = y
        mult = (1 + (level - 1) ** 0.8 * 0.06) * DIFF_HP[save["difficulty"]] * (0.6 + 0.4 * min(1.0, (level - 1) / 30.0))
        self.hp = self.max = d["hp"] * mult
        self.r = d["r"]
        self.speed = d["speed"]
        self.t = random.randint(0, 100)
        self.hold_y = random.randint(110, 270)
        self.dir = random.choice((-1, 1))
        self.fire = random.randint(40, 120)
        self.flash = 0
        self.spr = ENEMY_SPR[typ]
        self.dead = False
        self.elite = False

    def update(self, g):
        d = ENEMY_DEFS[self.typ]
        self.t += 1
        if d["hold"]:
            if self.y < self.hold_y:
                self.y += self.speed * 1.6
            else:
                self.x += self.dir * self.speed * 0.8
                if self.x < 70 or self.x > WIDTH - 70:
                    self.dir *= -1
                self.y = self.hold_y + math.sin(self.t * 0.03) * 12
        else:
            self.y += self.speed
            self.x = clamp(self.x0 + math.sin(self.t * d["freq"] + self.x0) * d["amp"], 30, WIDTH - 30)
        if d["fire"]:
            self.fire -= 1
            if self.fire <= 0 and 20 < self.y < HEIGHT - 160:
                self.shoot(g)
                lo, hi = d["fire"]
                self.fire = max(25, int(random.randint(lo, hi) * (1.8 - 0.8 * g.ease()) / (1 + min(g.level, 300) / 400.0)))
        if self.flash:
            self.flash -= 1

    def shoot(self, g):
        sp = g.bspeed()
        t = self.typ
        if t == "fighter":
            g.ebullet(self.x, self.y + 25, math.pi / 2, 5 * sp)
        elif t == "bee":
            g.ebullet(self.x, self.y + 20, g.aim(self.x, self.y), 4.6 * sp)
        elif t == "clawer":
            g.ebullet(self.x - 22, self.y + 28, math.pi / 2, 5.4 * sp)
            g.ebullet(self.x + 22, self.y + 28, math.pi / 2, 5.4 * sp)
        elif t == "shield":
            a = g.aim(self.x, self.y)
            for o in (-0.25, 0, 0.25):
                g.ebullet(self.x, self.y + 30, a + o, 4.6 * sp)
        elif t == "heavy":
            a = g.aim(self.x, self.y)
            for o in (-0.4, -0.2, 0, 0.2, 0.4):
                g.ebullet(self.x, self.y + 34, a + o, 4.4 * sp)
        sfx("enemy_fire", 90, 0.5)

    def draw(self, s, anim):
        spr = flash_version(self.spr) if self.flash else self.spr
        h = self.spr.get_height()
        for ox in (-12, 12):
            draw_flame(s, self.x + ox, self.y - h * 0.42, 4, 20, (255, 120, 40), anim + ox, up=True)
        if self.elite:
            add_glow(s, self.x, self.y, int(self.r * 2.2 + 4 * math.sin(anim * 0.15)), (150, 110, 20))
        s.blit(spr, spr.get_rect(center=(int(self.x), int(self.y))))
        if self.elite or (self.max > 6 and self.hp < self.max):
            w = 44
            pygame.draw.rect(s, RED_DARK, (self.x - w // 2, self.y - self.r - 12, w, 4))
            pygame.draw.rect(s, RED_LIGHT, (self.x - w // 2, self.y - self.r - 12, int(w * max(0, self.hp) / self.max), 4))

ROCK_SPR = []

# يرسم صخرة كويكب غير منتظمة بفوّهات
def draw_rock(p, seed):
    rng = random.Random(seed)
    n = 11
    pts = []
    for i in range(n):
        a = i * TAU / n
        r = rng.uniform(26, 38)
        pts.append((math.cos(a) * r, math.sin(a) * r))
    p.poly(pts, (92, 82, 78), (40, 34, 34), 2.5)
    p.poly([(x * 0.8 - 4, y * 0.8 - 4) for x, y in pts], (128, 116, 108))
    for _ in range(5):
        cx, cy = rng.uniform(-15, 15), rng.uniform(-15, 15)
        rr = rng.uniform(3, 7)
        p.circ(cx, cy, rr, (74, 66, 62), (46, 40, 38), 1)
        p.circ(cx - 1, cy - 1, rr * 0.4, (150, 138, 128))

# كويكب: عائق يتدحرج، يؤذيك إن اصطدمت به، ويمكن تدميره (يسقط عملات أحياناً)
class Asteroid:
    def __init__(self, level):
        self.r = random.randint(18, 42)
        self.x = random.uniform(40, WIDTH - 40)
        self.y = -self.r * 1.5
        self.vx = random.uniform(-1.2, 1.2)
        self.vy = random.uniform(1.6, 3.4) * (0.7 + 0.3 * min(1.0, (level - 1) / 30.0))
        self.rot = random.uniform(0, 360)
        self.vr = random.uniform(-2.5, 2.5)
        self.spr = random.choice(ROCK_SPR)
        mult = (1 + (level - 1) ** 0.8 * 0.06) * DIFF_HP[save["difficulty"]] * (0.6 + 0.4 * min(1.0, (level - 1) / 30.0))
        self.hp = (self.r / 9.0) * mult
        self.flash = 0
        self.dead = False

    def update(self, g):
        self.x += self.vx
        self.y += self.vy
        self.rot += self.vr
        if self.x < 30 or self.x > WIDTH - 30:
            self.vx = -self.vx
        if self.flash:
            self.flash -= 1
        if self.y > HEIGHT + 90:
            self.dead = True

    def draw(self, s):
        spr = flash_version(self.spr) if self.flash else self.spr
        img = pygame.transform.rotozoom(spr, self.rot, self.r / 38.0)
        s.blit(img, img.get_rect(center=(int(self.x), int(self.y))))

# ================= الزعيم =================
# أنماط إطلاق الزعماء العامة وفواصلها الزمنية
ALL_PATTERNS = ["fan", "aimed", "spiral", "ring", "rain", "wall"]
PAT_INTERVAL = dict(fan=55, aimed=40, spiral=5, ring=80, rain=7, wall=110)
# اسم كل تصميم، وصف قدرته، أنماط إطلاقه، معامل حياته وسرعة حركته
BOSS_TITLES = ["WARLORD", "OVERMIND", "HIVE QUEEN", "BASTION", "SPECTER", "GEMINI", "MINELAYER", "VOID EYE"]
BOSS_ABILITY = ["CHARGE DASH", "SHIELD + SUMMON", "BEE SWARMS", "DEATH LASER",
                "TELEPORT + HOMING", "TWIN CROSSFIRE", "MINEFIELD", "GRAVITY WELL"]
DESIGN_PATTERNS = {0: ["aimed", "fan", "wall"], 1: ["spiral", "ring", "aimed"], 2: ["rain", "fan", "spiral"],
                   3: ["wall", "aimed", "fan"], 4: ["ring", "aimed", "rain"], 5: ["fan", "spiral", "aimed"],
                   6: ["ring", "wall", "fan"], 7: ["spiral", "ring", "rain"]}
BOSS_HP = [1.0, 1.0, 0.95, 1.2, 0.9, 1.1, 1.3, 1.0]
BOSS_SPD = [1.0, 0.9, 1.6, 0.4, 1.0, 1.1, 0.6, 0.8]

class Boss:
    """الزعيم: 8 تصاميم، لكل تصميم قدرة خاصة (اندفاع/درع/أسراب/ليزر/انتقال/نيران متقاطعة/ألغام/جاذبية)."""
    def __init__(self, level):
        k = level // BOSS_EVERY
        self.k = k
        self.level = level
        self.design = (k - 1) % 8
        self.pal_i = ((k - 1) // 8 + (k - 1) % 8) % len(BOSS_PALS)
        self.pal = BOSS_PALS[self.pal_i]
        self.tier = (k - 1) // 20
        self.spr = get_boss_sprite(self.design, self.pal_i, self.tier)
        self.r = 84
        mult = DIFF_HP[save["difficulty"]] * BOSS_HP[self.design]
        self.max = self.hp = (120 + level * 20 * (1 + level / 300.0)) * mult * (0.7 + 0.3 * min(1.0, (level - 1) / 30.0))
        self.x, self.y = WIDTH / 2, -200.0
        self.cx, self.amp = WIDTH / 2, WIDTH / 2 - 210
        self.target_y = 170
        self.t = 0
        self.name = "%s %s" % (BOSS_ADJ[(k - 1) % 10], BOSS_TITLES[self.design])
        self.patterns = DESIGN_PATTERNS[self.design][:2 + min(1, k // 8)]
        self.pat_i = 0
        self.pat_t = 0
        self.cool = 90
        self.spin = 0.0
        self.flash = 0
        self.dying = False
        self.die_t = 0
        self.dead = False
        self.minion_t = 400
        self.col = self.pal["eye"]
        # حالات القدرات الخاصة
        self.state = "idle"
        self.st_t = 0
        self.ab_t = 0
        self.shielded = 0   # مؤقت الدرع (العقل المدبر)
        self.vis = 255      # الشفافية (الشبح)
        self.beam = None    # [x, t] الليزر القاتل (الحصن)

    def hittable(self):
        """هل يمكن إصابة الزعيم الآن؟ (لا يمكن أثناء الموت أو الاختفاء)"""
        return not self.dying and self.vis > 150 and self.y > -80

    def take(self, dmg):
        if self.dying:
            return
        if self.shielded > 0 or self.vis < 255:
            spark(self.x + random.uniform(-60, 60), self.y + random.uniform(-40, 40), (120, 200, 255), 2)
            return
        self.hp -= dmg
        self.flash = 3
        if self.hp <= 0:
            self.dying = True
            self.die_t = 130
            sfx("boom_boss", 100)

    def update(self, g):
        self.t += 1
        if self.flash:
            self.flash -= 1
        if self.dying:
            self.die_t -= 1
            if self.die_t % 6 == 0:
                explode(self.x + random.uniform(-90, 90), self.y + random.uniform(-70, 70), random.uniform(0.8, 1.6))
                sfx("boom_m", 60)
                g.shake = max(g.shake, 12)
            if self.die_t <= 0:
                self.dead = True
            return
        if self.y < self.target_y and self.state == "idle":
            self.y += 2.5
            return
        spd = 0.012 * (1 + min(self.k, 20) * 0.03) * BOSS_SPD[self.design]
        self.x = clamp(self.cx + math.sin(self.t * spd) * self.amp, 150, WIDTH - 150)
        if self.state == "idle":
            self.y = self.target_y + math.sin(self.t * 0.02) * 20
        self.ability(g)
        self.pat_t += 1
        if self.pat_t > 480:
            self.pat_t = 0
            self.pat_i = (self.pat_i + 1) % len(self.patterns)
        enr = 0.7 if self.hp < self.max * 0.5 else 1.0
        self.cool -= 1
        if self.cool <= 0 and self.state not in ("charge", "dash"):
            pat = self.patterns[self.pat_i]
            self.fire(g, pat)
            self.cool = max(3, int(PAT_INTERVAL[pat] * enr * (1.5 - 0.5 * g.ease()) / (1 + self.k * 0.01)))

    def ability(self, g):
        """القدرة الخاصة لكل تصميم."""
        d = self.design
        self.ab_t += 1
        t = self.ab_t
        if d == 0:  # القائد: يشحن ثم يندفع نحو الأسفل ثم يعود
            if self.state == "idle" and t % 420 == 300:
                self.state, self.st_t = "charge", 40
                sfx("roar", 200)
            elif self.state == "charge":
                self.st_t -= 1
                self.x += random.uniform(-3, 3)
                if self.st_t <= 0:
                    self.state, self.st_t = "dash", 45
            elif self.state == "dash":
                self.y += 13
                self.st_t -= 1
                g.shake = max(g.shake, 6)
                if self.st_t <= 0 or self.y > 560:
                    self.state = "back"
            elif self.state == "back":
                self.y -= 6
                if self.y <= self.target_y:
                    self.y = self.target_y
                    self.state = "idle"
        elif d == 1:  # العقل المدبر: درع غير قابل للإصابة + استدعاء أتباع (اقتلهم لكسر الدرع)
            if self.shielded > 0:
                self.shielded -= 1
                if not g.enemies and self.shielded < 200:
                    self.shielded = 0
                    sfx("shield")
            elif t % 620 == 400:
                self.shielded = 260
                sfx("roar", 200)
                g.spawn_group("fighter", limit=3)
                g.spawn_group("scout", limit=3)
        elif d == 2:  # ملكة الخلية: أسراب نحل
            if t % 300 == 150 and len(g.enemies) < 8:
                g.spawn_group("bee", limit=4)
                sfx("roar", 200)
        elif d == 3:  # الحصن: ليزر قاتل (تحذير ثم شعاع عمودي)
            if self.beam is None:
                if t % 540 == 240:
                    self.beam = [self.x, 0]
                    sfx("warn", 100)
            else:
                self.beam[1] += 1
                if self.beam[1] < 70:
                    pl = g.nearest_player(self.x, self.y)
                    tx = pl.x if pl else self.x
                    self.beam[0] += (tx - self.beam[0]) * 0.06
                elif self.beam[1] == 70:
                    sfx("beam", 100)
                if self.beam[1] >= 150:
                    self.beam = None
        elif d == 4:  # الشبح: يختفي وينتقل ثم يطلق رصاصاً يلاحق اللاعب
            if self.state == "idle" and t % 360 == 300:
                self.state, self.st_t = "fade", 20
                sfx("teleport")
            elif self.state == "fade":
                self.st_t -= 1
                self.vis = max(0, int(255 * self.st_t / 20))
                if self.st_t <= 0:
                    self.cx = random.uniform(260, 640)
                    self.amp = 100
                    self.y = random.uniform(172, 250)
                    self.state, self.st_t = "appear", 20
            elif self.state == "appear":
                self.st_t -= 1
                self.vis = min(255, int(255 * (1 - self.st_t / 20)))
                if self.st_t <= 0:
                    self.vis = 255
                    self.state = "idle"
                    a = g.aim(self.x, self.y + 40)
                    for o in (-0.3, 0, 0.3):
                        g.ebullet(self.x, self.y + 40, a + o, 3.2 * g.bspeed(), "orb", self.col, seek=True, life=260)
                    sfx("enemy_fire", 80, 0.8)
        elif d == 5:  # التوأم: قرنان يطلقان نيراناً مصوّبة ثم متقاطعة
            sp = g.bspeed()
            if t % 90 == 45:
                for sgn in (-1, 1):
                    px, py = self.x + sgn * 82, self.y + 20
                    a = g.aim(px, py)
                    g.ebullet(px, py, a, 6.0 * sp, "bolt", self.col)
                    g.ebullet(px, py, a + 0.12 * sgn, 6.0 * sp, "bolt", self.col)
            if t % 400 == 300:
                for i in range(9):
                    ang = math.pi / 2 + (i - 4) * 0.2
                    g.ebullet(self.x - 82, self.y + 20, ang, 4.4 * sp, "needle", self.col)
                    g.ebullet(self.x + 82, self.y + 20, math.pi - ang, 4.4 * sp, "needle", self.col)
                sfx("enemy_fire", 80, 0.8)
        elif d == 6:  # الكسّار: يزرع ألغاماً تنفجر إلى حلقة رصاص
            if t % 120 == 60 and len(g.eb) < 380:
                g.ebullet(self.x + random.uniform(-70, 70), self.y + 90, math.pi / 2 + random.uniform(-0.3, 0.3),
                          1.8, "mine", self.col, life=110)
                sfx("mine", 60)
        elif d == 7:  # عين الفراغ: تجذب اللاعبين نحوها نصف الوقت
            cyc = t % 480
            if cyc < 240:
                if cyc % 25 == 0:
                    particles.append(Particle(self.x, self.y, 0, 0, 30, "ring", 170, (160, 80, 255)))
                for p in g.players:
                    if p.alive:
                        p.x += clamp((self.x - p.x) * 0.006, -2.0, 2.0)
                        p.y += clamp((self.y + 60 - p.y) * 0.004, -1.5, 1.5)

    def fire(self, g, pat):
        """أنماط الإطلاق العامة (مروحة، مصوّب، لولب، حلقة، مطر، جدار)."""
        sp = g.bspeed()
        mx, my = self.x, self.y + 65
        k = self.k
        col = self.col
        if pat == "fan":
            n = 5 + min(8, k // 3)
            for i in range(n):
                a = math.pi / 2 + (i - (n - 1) / 2) * 1.7 / (n - 1)
                g.ebullet(mx, my, a, 4.2 * sp, "orb", col)
        elif pat == "aimed":
            a = g.aim(mx, my)
            for o in (-0.14, 0, 0.14):
                g.ebullet(mx, my, a + o, 6.2 * sp, "bolt", col)
        elif pat == "spiral":
            self.spin += 0.23
            arms = 2 + k // 10
            for i in range(arms):
                g.ebullet(mx, my - 20, self.spin + i * TAU / arms, 3.6 * sp, "orb", col)
        elif pat == "ring":
            n = 16 + min(16, k // 2)
            off = random.uniform(0, TAU)
            for i in range(n):
                g.ebullet(mx, my - 20, off + i * TAU / n, 3.4 * sp, "orb", col)
        elif pat == "rain":
            g.ebullet(random.uniform(30, WIDTH - 30), -10, math.pi / 2, (5 + random.random() * 2) * sp, "needle", col)
        elif pat == "wall":
            gap = random.randint(1, 13)
            for i in range(16):
                if abs(i - gap) <= 1:
                    continue
                g.ebullet(30 + i * 56, my + 10, math.pi / 2, 3.0 * sp, "orb", col)
        sfx("enemy_fire", 80, 0.7)

    def draw(self, s, anim):
        if self.dying and self.die_t % 4 == 0:
            return
        spr = flash_version(self.spr) if self.flash else self.spr
        h = spr.get_height()
        if self.design not in (4, 7):  # الشبح وعين الفراغ بلا لهب محركات
            for ox in (-55, 0, 55):
                draw_flame(s, self.x + ox, self.y + h * 0.36, 9, 38, (255, 140, 50), anim + ox)
        pul = 0.7 + 0.3 * math.sin(self.t * 0.1)
        add_glow(s, self.x, self.y, int(90 * pul), shade(self.pal["ring"], 0.4))
        if self.vis < 255:
            spr.set_alpha(self.vis)
        s.blit(spr, spr.get_rect(center=(int(self.x), int(self.y))))
        if self.vis < 255:
            spr.set_alpha(255)
        if self.shielded > 0:  # فقاعة الدرع
            add_glow(s, self.x, self.y, 130, (30, 90, 200))
            pygame.draw.circle(s, (120, 200, 255), (int(self.x), int(self.y)), 118, 3)
        if self.beam:  # الليزر القاتل
            bx, bt = self.beam
            top = self.y + 60
            if bt < 70:
                if (bt // 4) % 2 == 0:
                    pygame.draw.line(s, (255, 60, 60), (bx, top), (bx, HEIGHT), 2)
            elif bt < 150:
                w = 26 + int(6 * math.sin(bt * 0.6))
                pygame.draw.rect(s, (255, 90, 90), (bx - w, top, 2 * w, HEIGHT))
                pygame.draw.rect(s, WHITE, (bx - w // 3, top, 2 * (w // 3), HEIGHT))
                for yy in range(int(top), HEIGHT, 80):
                    add_glow(s, bx, yy, 70, (255, 60, 60))

# ================= منطق اللعبة =================
# اللعبة: تدير المرحلة والموجات والاصطدامات والرسم
class Game:
    def __init__(self):
        self.players = []
        self.level = 1
        self.score = save["score"]
        self.reset_lists()
        self.shake = 0
        self.flash = 0
        self.clear_timer = 0
        self.t = 0
        self.banner = 0
        self.hurt_t = 0
        self.combo = 0
        self.combo_t = 0

    def reset_lists(self):
        self.pb = []
        self.eb = []
        self.enemies = []
        self.pickups = []
        self.boss = None
        self.boss_spawned = False
        self.rocks = []
        self.arcs = []

    # بدء مرحلة: تصفير القوائم، تحديد عدد الأعداء (المراحل طويلة)، إنشاء اللاعبين، اختيار الخلفية
    def start_level(self, level, fresh=False):
        self.level = level
        self.reset_lists()
        particles.clear()
        texts.clear()
        self.is_boss = level % BOSS_EVERY == 0
        self.goal = min(300, 150 + level // 2) if self.is_boss else min(600, 300 + level)
        self.boss_started = False
        self.wave = 1
        self.wave_t = 0
        self.elites = 0
        self.rock_timer = 200
        self.rock_burst = 0
        self.spawned = 0
        self.spawn_timer = 60
        self.boss_timer = 260
        self.banner = 200
        self.clear_timer = 0
        self.shake = 0
        self.flash = 0
        self.kills = 0
        self.earned = 0
        self.hurt_t = 0
        self.combo = 0
        self.combo_t = 0
        if fresh:
            self.score = save["score"]
        n = 2 if save["two_players"] else 1
        xs = [WIDTH // 2] if n == 1 else [WIDTH // 3, 2 * WIDTH // 3]
        if fresh or len(self.players) != n:
            self.players = [Player(i) for i in range(n)]
            for p, x in zip(self.players, xs):
                p.reset_full(x)
        else:
            for p, x in zip(self.players, xs):
                p.next_level(x)
        space.set_theme((level - 1) // BOSS_EVERY)
        set_music("calm")

    # ---- دوال مساعدة ----
    def alive_players(self):
        return [p for p in self.players if p.alive]

    def aim(self, x, y):
        al = self.alive_players()
        if not al:
            return math.pi / 2
        p = min(al, key=lambda q: (q.x - x) ** 2 + (q.y - y) ** 2)
        return math.atan2(p.y - y, p.x - x)

    # معامل تسهيل: 0 في المرحلة 1 ثم يزيد حتى 1 في المرحلة 31 (البدايات أسهل)
    def ease(self):
        """0 at level 1 -> 1 at level 31: early levels are gentler."""
        return min(1.0, (self.level - 1) / 30.0)

    def bspeed(self):
        return DIFF_BUL[save["difficulty"]] * (1 + min(self.level, 300) / 500.0) * (0.72 + 0.28 * self.ease())

    def ebullet(self, x, y, ang, speed, kind="orb", col=None, seek=False, life=None):
        """رصاصة عدو. seek = تلاحق اللاعب، life = عمرها (للألغام)."""
        if len(self.eb) > 450:
            return
        r = 10 if kind == "mine" else 5 if kind == "needle" else 7
        self.eb.append(Bullet(x, y, math.cos(ang) * speed, math.sin(ang) * speed, 1, kind, False, r,
                              col=col, seek=seek, life=life))

    def nearest_player(self, x, y):
        al = self.alive_players()
        return min(al, key=lambda q: (q.x - x) ** 2 + (q.y - y) ** 2) if al else None

    def tesla(self, p, dmg):
        """سلاح تسلا: برق يقفز فوراً بين أقرب الأهداف أمام المركبة."""
        pool = [e for e in self.enemies if not e.dead] + [a for a in self.rocks if not a.dead]
        if self.boss and self.boss.hittable():
            pool.append(self.boss)
        n = min(5, 2 + save["power"] // 8)
        cx, cy = p.x, p.y - 50
        hit = []
        for _ in range(n):
            lim = 360 if not hit else 170
            cand = [t for t in pool if t not in hit and t.y < cy + 20 and math.hypot(t.x - cx, t.y - cy) < lim]
            if not cand:
                break
            t = min(cand, key=lambda q: (q.x - cx) ** 2 + (q.y - cy) ** 2)
            hit.append(t)
            pts = [(cx, cy)]
            for i in range(1, 5):
                k = i / 5.0
                pts.append((lerp(cx, t.x, k) + random.uniform(-14, 14), lerp(cy, t.y, k) + random.uniform(-14, 14)))
            pts.append((t.x, t.y))
            self.arcs.append([pts, 7])
            d = dmg * 1.6
            if isinstance(t, Boss):
                t.take(d)
            elif isinstance(t, Asteroid):
                t.hp -= d
                t.flash = 3
                if t.hp <= 0:
                    self.kill_rock(t)
            else:
                t.hp -= d
                t.flash = 3
                if t.hp <= 0:
                    self.kill_enemy(t)
            cx, cy = t.x, t.y
        if not hit:
            self.arcs.append([[(p.x, p.y - 50), (p.x + random.uniform(-20, 20), p.y - 150),
                               (p.x + random.uniform(-30, 30), p.y - 230)], 5])

    def hole_tick(self, b):
        """الثقب الأسود: يسحب الأعداء القريبة ويؤذيهم في كل إطار."""
        for e in self.enemies:
            if e.dead:
                continue
            dx, dy = b.x - e.x, b.y - e.y
            d = math.hypot(dx, dy)
            if d < 170:
                if d > 6:
                    e.x += dx / d * 2.6
                    e.x0 += dx / d * 2.6
                    e.y += dy / d * 2.6
                e.hp -= b.dmg * 0.1
                e.flash = 2
                if e.hp <= 0:
                    self.kill_enemy(e)
        for a in self.rocks:
            if not a.dead and math.hypot(b.x - a.x, b.y - a.y) < 170:
                a.hp -= b.dmg * 0.1
                if a.hp <= 0:
                    self.kill_rock(a)
        if self.boss and self.boss.hittable() and math.hypot(b.x - self.boss.x, b.y - self.boss.y) < 190:
            self.boss.take(b.dmg * 0.1)
        if b.age % 25 == 0:
            particles.append(Particle(b.x, b.y, 0, 0, 20, "ring", 120, (160, 80, 255)))

    def hole_burst(self, b):
        """انفجار الثقب الأسود في نهاية عمره: ضرر كبير في دائرة."""
        explode(b.x, b.y, 2.0, (150, 90, 230))
        sfx("boom_l", 40)
        self.shake = max(self.shake, 16)
        for e in self.enemies:
            if not e.dead and math.hypot(b.x - e.x, b.y - e.y) < 210:
                e.hp -= b.dmg * 8
                e.flash = 4
                if e.hp <= 0:
                    self.kill_enemy(e)
        for a in self.rocks:
            if not a.dead and math.hypot(b.x - a.x, b.y - a.y) < 210:
                self.kill_rock(a)
        if self.boss and self.boss.hittable() and math.hypot(b.x - self.boss.x, b.y - self.boss.y) < 230:
            self.boss.take(b.dmg * 6)

    def flak_burst(self, b):
        """انفجار قذيفة الفلاك إلى 10 شظايا."""
        explode(b.x, b.y, 0.6)
        sfx("boom_s", 40)
        for i in range(10):
            a = i * TAU / 10 + random.uniform(-0.1, 0.1)
            self.pb.append(Bullet(b.x, b.y, math.cos(a) * 9, math.sin(a) * 9, b.dmg * 0.6, "spread", True, 5, life=16))

    def mine_burst(self, b):
        """انفجار لغم الزعيم إلى حلقة من الرصاص."""
        explode(b.x, b.y, 0.7)
        sfx("boom_s", 40)
        for i in range(10):
            self.ebullet(b.x, b.y, i * TAU / 10, 3.2 * self.bspeed(), "orb", b.col)

    def use_bomb(self):
        """استخدام قنبلة من المخزون (مفتاح X)."""
        if save["bombs"] > 0 and self.alive_players():
            save["bombs"] -= 1
            self.bomb()

    def nearest_target(self, x, y):
        best = None
        bd = 1e12
        for e in self.enemies:
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < bd:
                bd, best = d, e
        if self.boss and not self.boss.dying and self.boss.y > 0:
            d = (self.boss.x - x) ** 2 + (self.boss.y - y) ** 2
            if d < bd:
                best = self.boss
        return best

    def drop(self, x, y, kind=None):
        if kind is None:
            tot = sum(w for _, w in PICK_WEIGHTS)
            r = random.uniform(0, tot)
            for k, w in PICK_WEIGHTS:
                r -= w
                if r <= 0:
                    kind = k
                    break
            else:
                kind = "coin"
        self.pickups.append(Pickup(x, y, kind))

    # ---- ظهور الأعداء ----
    def pick_type(self):
        L = self.level
        pool = [("scout", 10)]
        pool.append(("fighter", 8))
        if L >= 2:
            pool.append(("bee", 7))
        if L >= 4:
            pool.append(("clawer", 6))
        if L >= 9:
            pool.append(("shield", 5))
        if L >= 16:
            pool.append(("heavy", 4))
        tot = sum(w for _, w in pool)
        r = random.uniform(0, tot)
        for t, w in pool:
            r -= w
            if r <= 0:
                return t
        return "scout"

    def spawn_elite(self):
        self.elites += 1
        L = self.level
        typ = "clawer" if L < 8 else "shield" if L < 25 else "heavy"
        e = Enemy(typ, WIDTH / 2, -60.0, L)
        e.elite = True
        e.hp = e.max = e.hp * (3 + 3 * self.ease())
        e.hold_y = 130
        e.r += 6
        self.enemies.append(e)
        self.spawned += 1
        self.banner = 120
        sfx("warn", 300)

    def spawn_rocks(self):
        if self.clear_timer > 0:
            return
        self.rock_timer -= 1
        if self.rock_burst > 0 and self.t % 14 == 0 and len(self.rocks) < 16:
            self.rocks.append(Asteroid(self.level))
            self.rock_burst -= 1
        if self.rock_timer <= 0:
            self.rock_timer = random.randint(300, 520)
            if random.random() < 0.4:
                self.rock_burst = random.randint(6, 12)
            elif len(self.rocks) < 16:
                self.rocks.append(Asteroid(self.level))

    def kill_rock(self, a):
        if a.dead:
            return
        a.dead = True
        explode(a.x, a.y, 0.5 + a.r / 50.0, (120, 108, 100))
        sfx("boom_s", 40)
        self.score += 5
        if random.random() < 0.35:
            c = 2 + self.level // 25
            c = add_coins(c)
            self.earned += c
            texts.append([a.x, a.y - 15, "+%d" % c, GOLD, 35])
        if random.random() < 0.06:
            self.drop(a.x, a.y)

    def spawn_group(self, forced=None, limit=None):
        typ = forced or self.pick_type()
        d = ENEMY_DEFS[typ]
        n = random.choice([1, 1, 2, 3]) if d["hold"] else random.choice([1, 2, 3, 3, 4, 5, 6, 8])
        if limit is not None:
            n = min(n, limit)
        if self.level < 10:
            n = min(n, 4)
        shape = random.choice(["row", "vee", "random"])
        cx = random.randint(130, WIDTH - 130)
        for i in range(n):
            off = i - (n - 1) / 2
            x = clamp(cx + off * 70, 40, WIDTH - 40)
            y = -50.0
            if shape == "vee":
                y -= abs(off) * 30
            elif shape == "random":
                y -= random.randint(0, 60)
            self.enemies.append(Enemy(typ, x, y, self.level))
        return n

    # منطق الظهور: موجات الأعداء، النخبة، الكويكبات، ثم الزعيم في مراحل العاشرة
    def spawn(self):
        if self.spawned < self.goal:
            w = min(5, int(self.spawned * 5 / self.goal) + 1)
            if w != self.wave:
                self.wave = w
                self.wave_t = 130
                self.spawn_timer = 160
                sfx("powerup", 100)
                if self.level <= 30:
                    for p in self.players:
                        if p.alive and p.health < p.max_health:
                            p.health += 1
                            texts.append([p.x, p.y - 60, "+HEALTH", ICON_COL["health"], 50])
            self.spawn_rocks()
            self.spawn_timer -= 1
            cap = min(22, 7 + self.level // 8)
            if self.spawn_timer <= 0 and len(self.enemies) < cap:
                if self.elites < 2 and self.spawned >= self.goal * (self.elites + 1) / 3.0:
                    self.spawn_elite()
                    self.spawn_timer = 120
                    return
                self.spawned += self.spawn_group(limit=self.goal - self.spawned)
                self.spawn_timer = max(28, int((75 - min(self.level, 220) * 0.12) * random.uniform(0.8, 1.2)))
            return
        if not self.is_boss:
            return
        if not self.boss_started:
            if self.enemies:
                return
            self.boss_started = True
            self.banner = 200
            set_music("boss" if (self.level // BOSS_EVERY) % 2 else "boss2")
            sfx("warn", 200)
        self.boss_timer -= 1
        if not self.boss_spawned and self.boss_timer <= 0:
            self.boss = Boss(self.level)
            self.boss_spawned = True
            sfx("roar", 100)
        if self.boss and not self.boss.dying and self.boss.y >= self.boss.target_y and self.level >= 20:
            self.boss.minion_t -= 1
            if self.boss.minion_t <= 0 and len(self.enemies) < 6:
                self.boss.minion_t = 420
                self.spawn_group(random.choice(["scout", "fighter", "bee"]))

    # ---- الأحداث (قتل، التقاط، قنبلة) ----
    # قتل عدو: انفجار، نقاط، عملات، وقد يسقط جائزة
    def kill_enemy(self, e):
        if e.dead:
            return
        e.dead = True
        d = ENEMY_DEFS[e.typ]
        explode(e.x, e.y, 0.7 + e.r / 40.0, (60, 110, 190))
        sfx("boom_s" if e.r < 30 else "boom_m" if e.r < 40 else "boom_l", 40)
        self.score += d["score"] * (1 + self.level // 10)
        c = (1 + self.level // 25 + (1 if e.r > 30 else 0)) if random.random() < 0.35 else 0
        if e.elite:
            add_pass_xp(15)
            c = 40 + self.level
            self.score += d["score"] * 5
            for _ in range(3):
                self.drop(e.x + random.uniform(-40, 40), e.y + random.uniform(-20, 20))
            explode(e.x, e.y, 2.0)
        if c:
            c = add_coins(c)
            self.earned += c
            texts.append([e.x, e.y - 20, "+%d" % c, GOLD, 40])
        if random.random() < 0.13 + (0.05 if e.r >= 38 else 0) + (0.06 if self.level < 20 else 0):
            self.drop(e.x, e.y)
        self.kills += 1
        self.combo += 1
        self.combo_t = 100
        if self.combo >= 5:
            self.score += self.combo
        self.shake = max(self.shake, 3 + e.r // 10)

    # التقاط جائزة وتطبيق أثرها (كل نوع له أثر مختلف)
    def collect(self, p, pk):
        k = pk.kind
        lvl = self.level
        msg = None
        if k == "health":
            p.health = min(p.max_health, p.health + 1)
            msg = "+HEALTH"
        elif k == "shield":
            p.shield = p.shield_max
            p.buffs["shield"] = 420
            msg = "SHIELD"
        elif k == "special":
            p.specials = min(p.max_special, p.specials + 2)
            msg = "+SPECIAL"
        elif k == "coin":
            c = 10 + lvl // 2
            c = add_coins(c)
            self.earned += c
            msg = "+%d" % c
        elif k == "gem":
            c = 50 + lvl
            c = add_coins(c)
            self.earned += c
            msg = "+%d" % c
        elif k == "power":
            p.buffs["power"] = 600
            msg = "DOUBLE DAMAGE"
        elif k == "rapid":
            p.buffs["rapid"] = 600
            msg = "RAPID FIRE"
        elif k == "triple":
            p.buffs["triple"] = 600
            msg = "EXTRA SHOTS"
        elif k == "magnet":
            p.buffs["magnet"] = 720
            msg = "MAGNET"
        elif k == "bomb":
            self.bomb()
            msg = "BOMB!"
        sfx("gem" if k == "gem" else "coin" if k == "coin" else "powerup", 30)
        texts.append([pk.x, pk.y - 20, msg, ICON_COL[k], 55])
        spark(pk.x, pk.y, ICON_COL[k], 10)

    # قنبلة: تؤذي كل الأعداء وتمسح رصاص العدو وتضر الزعيم قليلاً
    def bomb(self):
        self.flash = 22
        self.shake = 28
        sfx("bomb", 100)
        dmg = 40 + self.level * 8
        for e in self.enemies[:]:
            e.hp -= dmg
            e.flash = 4
            if e.hp <= 0:
                self.kill_enemy(e)
        if self.boss and not self.boss.dying:
            self.boss.take(self.boss.max * 0.03)
        for b in self.eb:
            b.dead = True
            spark(b.x, b.y, (255, 200, 120), 2)
        particles.append(Particle(WIDTH / 2, HEIGHT / 2, 0, 0, 40, "ring", 700, (255, 180, 100)))

    # ---- التحديث الرئيسي ----
    # التحديث الرئيسي للعبة (يُستدعى 60 مرة بالثانية)
    def update(self):
        self.t += 1
        space.update(1.0 + (2.0 if self.clear_timer > 0 else 0.0))
        for p in self.players:
            p.update(self)
        if self.clear_timer == 0:
            self.spawn()
        for b in self.pb:
            b.update(self)
        for b in self.eb:
            b.update(self)
        for e in self.enemies:
            e.update(self)
        for a in self.rocks:
            a.update(self)
        if self.boss:
            self.boss.update(self)
            if self.boss.dead:
                self.boss_killed()
        for pk in self.pickups:
            pk.update(self)
        for b in self.pb:
            if b.kind == "hole" and not b.dead:
                self.hole_tick(b)

        # اصطدام رصاص اللاعب بالأعداء والكويكبات والزعيم
        for b in self.pb:
            if b.dead:
                continue
            for e in self.enemies:
                if e.dead or id(e) in b.hit:
                    continue
                dx, dy = b.x - e.x, b.y - e.y
                rr = e.r + b.r
                if dx * dx + dy * dy < rr * rr:
                    e.hp -= b.dmg
                    e.flash = 3
                    b.hit.add(id(e))
                    spark(b.x, b.y, (255, 220, 140), 3)
                    sfx("hit", 50)
                    if e.hp <= 0:
                        self.kill_enemy(e)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        b.dead = True
                        break
            if not b.dead:
                for a in self.rocks:
                    if a.dead or id(a) in b.hit:
                        continue
                    dx, dy = b.x - a.x, b.y - a.y
                    rr = a.r + b.r
                    if dx * dx + dy * dy < rr * rr:
                        a.hp -= b.dmg
                        a.flash = 3
                        b.hit.add(id(a))
                        spark(b.x, b.y, (200, 190, 170), 3)
                        if a.hp <= 0:
                            self.kill_rock(a)
                        if b.pierce > 0:
                            b.pierce -= 1
                        else:
                            b.dead = True
                            break
            if not b.dead and self.boss and self.boss.hittable() and id(self.boss) not in b.hit:
                bs = self.boss
                dx, dy = b.x - bs.x, b.y - bs.y
                rr = bs.r + b.r
                if dx * dx + dy * dy < rr * rr:
                    bs.take(b.dmg)
                    b.hit.add(id(bs))
                    spark(b.x, b.y, (255, 220, 140), 3)
                    sfx("hit", 50)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        b.dead = True
        # اصطدام رصاص وأجسام الأعداء بالاعبين وجمع الجوائز
        for p in self.players:
            if not p.alive:
                continue
            for b in self.eb:
                if b.dead:
                    continue
                dx, dy = b.x - p.x, b.y - p.y
                rr = p.hr + b.r
                if dx * dx + dy * dy < rr * rr:
                    b.dead = True
                    p.hurt(self, 1)
            for e in self.enemies:
                if e.dead:
                    continue
                dx, dy = e.x - p.x, e.y - p.y
                rr = e.r + 20
                if dx * dx + dy * dy < rr * rr:
                    e.hp -= 6
                    e.flash = 3
                    if e.hp <= 0:
                        self.kill_enemy(e)
                    p.hurt(self, 1)
            for a in self.rocks:
                if a.dead:
                    continue
                dx, dy = a.x - p.x, a.y - p.y
                rr = a.r * 0.85 + 18
                if dx * dx + dy * dy < rr * rr:
                    self.kill_rock(a)
                    p.hurt(self, 1)
            if self.boss and self.boss.beam and 70 <= self.boss.beam[1] < 150:
                if abs(p.x - self.boss.beam[0]) < 30 and p.y > self.boss.y:
                    p.hurt(self, 1)
            if self.boss and self.boss.hittable():
                dx, dy = self.boss.x - p.x, self.boss.y - p.y
                rr = self.boss.r * 0.8 + 18
                if dx * dx + dy * dy < rr * rr:
                    p.hurt(self, 1)
            for pk in self.pickups:
                if pk.dead:
                    continue
                dx, dy = pk.x - p.x, pk.y - p.y
                if dx * dx + dy * dy < 44 * 44:
                    pk.dead = True
                    self.collect(p, pk)

        # تنظيف القوائم من العناصر الميتة
        self.pb = [b for b in self.pb if not b.dead and b.onscreen()]
        self.eb = [b for b in self.eb if not b.dead and b.onscreen()]
        self.enemies = [e for e in self.enemies if not e.dead and e.y < HEIGHT + 80]
        self.rocks = [a for a in self.rocks if not a.dead]
        self.pickups = [p for p in self.pickups if not p.dead]
        for a in self.arcs:
            a[1] -= 1
        self.arcs = [a for a in self.arcs if a[1] > 0]
        for pt in particles:
            pt.update()
        particles[:] = [pt for pt in particles if pt.life > 0]
        for tx in texts:
            tx[1] -= 0.8
            tx[4] -= 1
        texts[:] = [tx for tx in texts if tx[4] > 0]
        self.shake *= 0.9
        if self.flash > 0:
            self.flash -= 1
        if self.banner > 0:
            self.banner -= 1
        if self.hurt_t > 0:
            self.hurt_t -= 1
        if self.combo_t > 0:
            self.combo_t -= 1
            if self.combo_t == 0:
                self.combo = 0
        if self.t % 100 == 0:  # إنذار انخفاض الصحة
            for p in self.players:
                if p.alive and p.health <= 1 and p.max_health >= 3:
                    sfx("alarm", 500)
                    break

        # شروط نهاية المرحلة (موت أو فوز)
        if not self.alive_players():
            return "dead"
        if self.clear_timer > 0:
            self.clear_timer -= 1
            if self.clear_timer == 0:
                return "clear"
        else:
            done = False
            if self.is_boss:
                done = self.boss_spawned and self.boss is None
            else:
                done = self.spawned >= self.goal and not self.enemies
            if done:
                self.clear_timer = 80
        return None

    # موت الزعيم: انفجار ضخم + جوائز + مكافأة
    def boss_killed(self):
        b = self.boss
        explode(b.x, b.y, 3.2)
        sfx("boom_boss", 100)
        self.shake = 34
        self.flash = 25
        self.score += 500 * b.k
        add_pass_xp(150)
        bonus = 100 + self.level * 5
        bonus = add_coins(bonus)
        self.earned += bonus
        for _ in range(7):
            self.drop(b.x + random.uniform(-90, 90), b.y + random.uniform(-40, 40))
        self.drop(b.x, b.y, "gem")
        self.drop(b.x + 30, b.y, "health")
        self.boss = None

    # ---- الرسم ----
    # رسم المشهد كاملاً بالترتيب (خلفية ثم جوائز ثم أعداء ثم لاعب ثم رصاص ثم تأثيرات ثم الواجهة)
    def draw(self):
        space.draw(canvas)
        anim = self.t
        for pk in self.pickups:
            pk.draw(canvas)
        for a in self.rocks:
            a.draw(canvas)
        for e in self.enemies:
            e.draw(canvas, anim)
        if self.boss:
            self.boss.draw(canvas, anim)
        for p in self.players:
            p.draw(canvas, anim)
        for b in self.pb:
            b.draw(canvas)
        for b in self.eb:
            b.draw(canvas)
        for pt in particles:
            pt.draw(canvas)
        for pts, life in self.arcs:  # برق تسلا
            for i in range(len(pts) - 1):
                pygame.draw.line(canvas, (60, 120, 220), pts[i], pts[i + 1], 6)
                pygame.draw.line(canvas, (150, 210, 255), pts[i], pts[i + 1], 3)
                pygame.draw.line(canvas, WHITE, pts[i], pts[i + 1], 1)
            add_glow(canvas, pts[-1][0], pts[-1][1], 26, (60, 120, 220))
        for x, y, t, col, life in texts:
            text(t, F_S, col, x, y, center=True)
        if self.flash > 0:
            ov = pygame.Surface((WIDTH, HEIGHT))
            ov.fill((255, 255, 255))
            ov.set_alpha(int(10 * self.flash))
            canvas.blit(ov, (0, 0))
        self.draw_hud()
        self.draw_fx()

    def draw_fx(self):
        """مؤثرات الشاشة: وميض أحمر عند الإصابة، عداد الكومبو، شريطا مقدمة الزعيم."""
        if self.hurt_t > 0 and RED_VIG is not None:
            RED_VIG.set_alpha(int(13 * self.hurt_t))
            canvas.blit(RED_VIG, (0, 0))
        if self.combo >= 3:
            text("COMBO x%d" % self.combo, F_M, ORANGE, WIDTH // 2, 118, center=True)
        b = self.boss
        if b and not b.dying and b.t < 150:
            k = min(1.0, b.t / 20.0, (150 - b.t) / 20.0)
            hh = int(60 * k)
            pygame.draw.rect(canvas, (0, 0, 0), (0, 0, WIDTH, hh))
            pygame.draw.rect(canvas, (0, 0, 0), (0, HEIGHT - hh, WIDTH, hh))
            if k > 0.6:
                text(b.name, F_L, RED_LIGHT, WIDTH // 2, HEIGHT - 40, center=True)
                text("ABILITY: " + BOSS_ABILITY[b.design], F_S, GOLD_LIGHT, WIDTH // 2, 30, center=True)

    # واجهة اللعب: النتيجة، العملات، المرحلة، الموجة، شريط الزعيم وقدرته
    def draw_hud(self):
        panel(6, 4, 262, 58, (60, 120, 200))
        panel(WIDTH - 268, 4, 262, 58, (60, 120, 200))
        panel(WIDTH // 2 - 135, 2, 270, 64, (60, 120, 200))
        text("SCORE %d" % self.score, F_M, WHITE, 16, 8)
        canvas.blit(get_icon("coin", 28), (14, 32))
        text(str(save["coins"]), F_M, GOLD, 46, 36)
        canvas.blit(get_icon("crystal", 28), (146, 32))
        text(str(save["crystals"]), F_M, (210, 150, 255), 176, 36)
        if vip_active():
            text("VIP", F_S, GOLD, 236, 10)
        w = save["equipped"].upper()
        text("%s  LV %d" % (w, save["power"]), F_S, CYAN, WIDTH - 16, 10, right=True)
        text("[%s] WEAPON  [B] SHOP" % kname(save["binds"]["weapon"]), F_S, GRAY_L, WIDTH - 16, 30, right=True)
        text("[%s] BOMB x%d   REVIVE x%d" % (kname(save["binds"]["bomb"]), save["bombs"], save["revives"]),
             F_S, GRAY_L, WIDTH - 16, 48, right=True)
        # اسم المرحلة وشريط التقدم
        sec = THEMES[((self.level - 1) // BOSS_EVERY) % len(THEMES)]["name"]
        text("LEVEL %d / %d" % (self.level, MAX_LEVEL), F_M, GOLD_LIGHT, WIDTH // 2, 16, center=True)
        text(sec, F_S, GRAY_L, WIDTH // 2, 38, center=True)
        if self.wave_t > 0:
            self.wave_t -= 1
        if self.goal and not self.boss_started:
            text("WAVE %d / 5" % self.wave, F_S, CYAN, WIDTH // 2 - 110, 48, right=True)
            frac = clamp((self.spawned - len(self.enemies)) / float(self.goal), 0, 1)
            pygame.draw.rect(canvas, (20, 30, 60), (WIDTH // 2 - 100, 52, 200, 6))
            pygame.draw.rect(canvas, CYAN, (WIDTH // 2 - 100, 52, int(200 * frac), 6))
        if self.boss and self.boss.y > -50:
            b = self.boss
            pygame.draw.rect(canvas, RED_DARK, (WIDTH // 2 - 210, 56, 420, 16))
            pygame.draw.rect(canvas, RED_LIGHT, (WIDTH // 2 - 210, 56, int(420 * clamp(b.hp / b.max, 0, 1)), 16))
            pygame.draw.rect(canvas, WHITE, (WIDTH // 2 - 210, 56, 420, 16), 2)
            text("%s  (BOSS %d)" % (b.name, b.k), F_S, WHITE, WIDTH // 2, 84, center=True)
            text("ABILITY: " + BOSS_ABILITY[b.design], F_S, GOLD_LIGHT, WIDTH // 2, 100, center=True)
        for p in self.players:
            self.draw_panel(p)
        if self.banner > 0 and self.clear_timer == 0:
            a = min(1.0, self.banner / 40.0)
            if self.is_boss and self.boss_started:
                if (self.banner // 10) % 2 == 0:
                    text("WARNING", F_XL, shade(RED_LIGHT, a), WIDTH // 2, HEIGHT // 2 - 40, center=True)
                text("BOSS %d APPROACHING" % (self.level // BOSS_EVERY), F_M, shade(WHITE, a), WIDTH // 2, HEIGHT // 2 + 10, center=True)
            else:
                text("LEVEL %d" % self.level, F_XL, shade(GOLD, a), WIDTH // 2, HEIGHT // 2 - 40, center=True)
        if self.wave_t > 0 and self.clear_timer == 0:
            text("WAVE %d" % self.wave, F_XL, shade(CYAN, min(1.0, self.wave_t / 30.0)), WIDTH // 2, HEIGHT // 2 - 90, center=True)
        if self.clear_timer > 0:
            text("SECTOR CLEAR", F_XL, GREEN, WIDTH // 2, HEIGHT // 2 - 40, center=True)

    # لوحة اللاعب: القلوب، شريط الدرع، السلاح الخاص، التعزيزات النشطة
    def draw_panel(self, p):
        x = 16 if p.pid == 0 else WIDTH - 16 - 250
        y = 66
        panel(x - 8, y - 6, 258, 84, (40, 90, 160))
        text("P%d" % (p.pid + 1), F_S, CYAN if p.pid == 0 else GOLD, x, y - 2)
        for i in range(p.max_health):
            canvas.blit(HEART_ON if i < p.health else HEART_OFF, (x + 28 + i * 22, y - 4))
        pygame.draw.rect(canvas, (14, 26, 60), (x, y + 24, 170, 9))
        pygame.draw.rect(canvas, BLUE_LIGHT if not p.shield_on else WHITE, (x, y + 24, int(170 * p.shield / p.shield_max), 9))
        pygame.draw.rect(canvas, GRAY_D, (x, y + 24, 170, 9), 1)
        canvas.blit(get_icon("special", 24), (x + 176, y + 16))
        text("x%d" % p.specials, F_S, CYAN, x + 202, y + 22)
        bx = x
        for k in BUFF_KINDS:
            if p.buffs[k] > 0:
                canvas.blit(get_icon(k, 28), (bx, y + 40))
                pygame.draw.rect(canvas, ICON_COL[k], (bx, y + 70, int(28 * p.buffs[k] / 700.0) + 1, 3))
                bx += 32

HEART_ON = HEART_OFF = None
game = None

# المتجر: 6 صفحات و43 عنصراً. العمود الأخير: "c" = عملات عادية، "g" = كريستال نوفا (عملة مميزة تُشحن)
SHOP_PAGES = ["WEAPONS", "SHIPS", "UPGRADES", "EXTRAS", "PREMIUM", "STYLE", "BUNDLES"]
SHOP = [  # (المعرّف, الصفحة, الاسم, الوصف, العملة)
    ("w_spread", 0, "SPREAD SHOT", "Wide golden fan", "c"),
    ("w_rapid", 0, "RAPID FIRE", "Fast pink bolts", "c"),
    ("w_plasma", 0, "PLASMA CANNON", "Piercing energy orb", "c"),
    ("w_missile", 0, "HOMING MISSILES", "Locks on targets", "c"),
    ("w_flak", 0, "FLAK CANNON", "Bursts into shrapnel", "c"),
    ("w_tesla", 0, "TESLA COIL", "Chain lightning", "c"),
    ("w_lance", 0, "ION LANCE", "Pierces everything", "c"),
    ("upgrade", 0, "WEAPON POWER", "More damage + shots", "c"),
    ("firerate", 0, "FIRE RATE", "Shoot faster", "c"),
    ("s_vanguard", 1, "VANGUARD", "Balanced battlecruiser", "c"),
    ("s_falcon", 1, "FALCON", "Fast, light armor", "c"),
    ("s_titan", 1, "TITAN", "Heavy armor + shield", "c"),
    ("s_phantom", 1, "PHANTOM", "Glass cannon +35% dmg", "c"),
    ("hull", 2, "HULL ARMOR", "+1 max health", "c"),
    ("special", 2, "SPECIAL BAY", "+1 special capacity", "c"),
    ("shield", 2, "SHIELD CELL", "+25 shield energy", "c"),
    ("speed", 2, "ENGINE BOOST", "+0.5 move speed", "c"),
    ("regen", 2, "SHIELD REGEN", "Faster shield recharge", "c"),
    ("coinup", 2, "COIN BONUS", "+10% coins earned", "c"),
    ("luck", 2, "LUCKY DROPS", "More pickups drop", "c"),
    ("spower", 2, "SPECIAL POWER", "Stronger special", "c"),
    ("drone", 3, "WINGMAN DRONE", "Auto-firing helper", "c"),
    ("revive", 3, "REVIVE TOKEN", "Come back once", "c"),
    ("bombitem", 3, "BOMB", "Clears screen [X]", "c"),
    ("repair", 3, "FULL REPAIR", "Heal, shield, specials", "c"),
    ("s_nova", 4, "NOVA PRIME", "Elite ship +25% dmg", "g"),
    ("s_eclipse", 4, "ECLIPSE", "Elite ship +50% dmg", "g"),
    ("w_photon", 4, "PHOTON BURST", "3 homing photons", "g"),
    ("w_singularity", 4, "SINGULARITY", "Black hole cannon", "g"),
    ("prem_coin2", 4, "DOUBLE COINS", "x2 coins forever", "g"),
    ("prem_drone2", 4, "DRONE UPGRADE", "Drones deal x2", "g"),
    ("aegis", 4, "AEGIS CORE", "+50 shield (x4)", "g"),
    ("prem_revive3", 4, "REVIVE PACK", "+3 revive tokens", "g"),
    ("prem_bomb5", 4, "BOMB PACK", "+5 bombs", "g"),
    ("skin_classic", 5, "CLASSIC PAINT", "Original colors", "c"),
    ("skin_ice", 5, "ICE WING", "Frozen blue paint", "c"),
    ("skin_crimson", 5, "CRIMSON", "Blood red paint", "c"),
    ("skin_stealth", 5, "STEALTH", "Matte black paint", "c"),
    ("skin_gold", 5, "GOLDEN ARMOR", "Premium gold paint", "g"),
    ("skin_aurora", 5, "AURORA", "Premium aurora paint", "g"),
    ("skin_void", 5, "VOID WALKER", "Premium void paint", "g"),
    ("trail_pink", 5, "PINK TRAIL", "Engine trail color", "c"),
    ("trail_rainbow", 5, "RAINBOW TRAIL", "Premium color-cycling", "g"),
    ("coins_5k", 6, "COIN POUCH", "5,000 coins", "g"),
    ("coins_25k", 6, "COIN CHEST", "25,000 coins", "g"),
    ("coins_100k", 6, "COIN VAULT", "100,000 coins", "g"),
    ("bundle_warrior", 6, "WARRIOR PACK", "Coins + revives + bombs", "g"),
    ("bundle_defender", 6, "DEFENDER PACK", "Aegis + revives + coins", "g"),
    ("bundle_collector", 6, "COLLECTOR PACK", "3 paints + rainbow trail", "g"),
    ("bundle_ace", 6, "ACE PACK", "Nova + Photon + bombs", "g"),
    ("pass_unlock", 6, "PASS UNLOCK", "Premium pass track", "g"),
    ("bundle_ultimate", 6, "ULTIMATE PACK", "Everything premium", "g"),
]
WEAPON_COST = dict(spread=150, rapid=250, plasma=400, missile=600, flak=500, tesla=700, lance=900,
                   photon=600, singularity=1200)
SKIN_PRICE = dict(ice=600, crimson=600, stealth=800, gold=250, aurora=350, void=450)
TRAIL_PRICE = dict(pink=400, rainbow=300)
MAX_POWER = 30
# ترقيات متدرجة: المعرّف -> (مفتاح الحفظ, أقصى مستوى, السعر الأساسي, الزيادة لكل مستوى)
LVL_UPG = dict(firerate=("firerate_lv", 10, 150, 110), spower=("spower_lv", 10, 120, 90),
               speed=("speed_lv", 5, 200, 150), regen=("regen_lv", 5, 180, 130),
               coinup=("coin_lv", 10, 250, 200), luck=("luck_lv", 10, 220, 160))
ICON_OF = dict(bombitem="bomb", prem_coin2="coinup", prem_drone2="drone", aegis="regen",
               prem_revive3="revive", prem_bomb5="bomb", coins_5k="coin", coins_25k="coin", coins_100k="coin",
               bundle_warrior="bundle", bundle_defender="bundle", bundle_collector="bundle",
               bundle_ace="bundle", bundle_ultimate="bundle", pass_unlock="pass")
# حزم تُشترى بالكريستال: المعرّف -> (السعر, المكافآت, وصف)
BUNDLES = {
    "coins_5k": (60, dict(coins=5000), "5,000 COINS"),
    "coins_25k": (250, dict(coins=25000), "25,000 COINS"),
    "coins_100k": (900, dict(coins=100000), "100,000 COINS"),
    "bundle_warrior": (350, dict(coins=10000, revives=5, bombs=5), "10K COINS+5 REVIVES+5 BOMBS"),
    "bundle_defender": (500, dict(coins=5000, aegis=2, revives=3), "2 AEGIS+3 REVIVES+5K"),
    "bundle_collector": (800, dict(skins=["gold", "aurora", "void"], trails=["rainbow"]), "3 PAINTS+RAINBOW TRAIL"),
    "bundle_ace": (1300, dict(ships=["nova"], weapons=["photon"], bombs=3), "NOVA+PHOTON+3 BOMBS"),
    "pass_unlock": (800, dict(pass_premium=True), "UNLOCK PREMIUM PASS TRACK"),
    "bundle_ultimate": (3500, dict(ships=["nova", "eclipse"], weapons=["photon", "singularity"],
                                   skins=["gold", "aurora", "void"], trails=["rainbow"], coin2=True, drone2=True,
                                   pass_premium=True), "ALL PREMIUM SHIPS/GUNS/PAINTS+x2"),
}


def bundle_owned(gr):
    """هل يملك اللاعب كل محتويات الحزمة (الحزم الاستهلاكية تُشترى دائماً)؟"""
    if any(gr.get(k) for k in ("coins", "crystals", "revives", "bombs", "aegis", "vip_days")):
        return False
    ok = all(i in save[k] for k in ("ships", "weapons", "skins", "trails") for i in gr.get(k, []))
    if gr.get("coin2") and not save["coin2"]:
        ok = False
    if gr.get("drone2") and not save["drone2"]:
        ok = False
    if gr.get("pass_premium") and not save["pass_prem"]:
        ok = False
    return ok


def shop_icon_kind(item_id):
    """اسم الأيقونة المناسبة لعنصر المتجر."""
    if item_id.startswith("s_"):
        return "ship_" + item_id[2:]
    return ICON_OF.get(item_id, item_id)


def page_items():
    """فهارس عناصر الصفحة الحالية في قائمة SHOP."""
    return [i for i, it in enumerate(SHOP) if it[1] == U.page]


def shop_info(i):
    """يعيد (حالة نصية أو None, السعر أو None, سطر معلومات)."""
    kind = SHOP[i][0]
    if kind in BUNDLES:
        price, gr, line = BUNDLES[kind]
        return ("OWNED", None, line) if bundle_owned(gr) else (None, price, line)
    if kind.startswith("w_"):
        w = kind[2:]
        if w in save["weapons"]:
            return ("EQUIPPED" if save["equipped"] == w else "OWNED - PRESS TO EQUIP"), None, ""
        return None, WEAPON_COST[w], ""
    if kind.startswith("s_"):
        sh = kind[2:]
        sd = SHIP_DEFS[sh]
        line = "SPD %.1f HP %+d DMG x%.2f" % (sd["speed"], sd["hp"], sd["dmg"])
        if sh in save["ships"]:
            return ("EQUIPPED" if save["ship"] == sh else "OWNED - PRESS TO EQUIP"), None, line
        return None, sd["price"], line
    if kind.startswith("skin_"):
        sk = kind[5:]
        if sk in save["skins"]:
            return ("EQUIPPED" if save["skin"] == sk else "OWNED - PRESS TO EQUIP"), None, ""
        return None, SKIN_PRICE[sk], ""
    if kind.startswith("trail_"):
        tr = kind[6:]
        if tr in save["trails"]:
            return ("EQUIPPED - PRESS TO REMOVE" if save["trail"] == tr else "OWNED - PRESS TO EQUIP"), None, ""
        return None, TRAIL_PRICE[tr], ""
    if kind == "upgrade":
        line = "LEVEL %d / %d" % (save["power"], MAX_POWER)
        if save["power"] >= MAX_POWER:
            return "MAX LEVEL", None, line
        return None, 80 + 45 * save["power"], line
    if kind in LVL_UPG:
        key, mx, base, step = LVL_UPG[kind]
        line = "LEVEL %d / %d" % (save[key], mx)
        if save[key] >= mx:
            return "MAX LEVEL", None, line
        return None, base + step * save[key], line
    if kind == "hull":
        line = "HEALTH %d / 10" % save["max_health"]
        if save["max_health"] >= 10:
            return "MAX LEVEL", None, line
        return None, 120 + 90 * max(0, save["max_health"] - 5), line
    if kind == "special":
        line = "CAPACITY %d / 9" % save["max_special"]
        if save["max_special"] >= 9:
            return "MAX LEVEL", None, line
        return None, 100 + 60 * (save["max_special"] - 3), line
    if kind == "shield":
        line = "ENERGY %d / 300" % save["max_shield"]
        if save["max_shield"] >= 300:
            return "MAX LEVEL", None, line
        return None, 60 + 2 * (save["max_shield"] - 100), line
    if kind == "drone":
        line = "DRONES %d / 3" % save["drones"]
        if save["drones"] >= 3:
            return "MAX", None, line
        return None, 400 + 300 * save["drones"], line
    if kind == "revive":
        line = "OWNED %d / 9" % save["revives"]
        return (None, 150, line) if save["revives"] < 9 else ("MAX", None, line)
    if kind == "bombitem":
        line = "OWNED %d / 9" % save["bombs"]
        return (None, 60, line) if save["bombs"] < 9 else ("MAX", None, line)
    if kind == "prem_coin2":
        return ("ACTIVE", None, "x2 COINS FOREVER") if save["coin2"] else (None, 800, "x2 COINS FOREVER")
    if kind == "prem_drone2":
        return ("ACTIVE", None, "DRONES x2 DAMAGE") if save["drone2"] else (None, 500, "DRONES x2 DAMAGE")
    if kind == "aegis":
        line = "AEGIS %d / 4" % save["aegis"]
        return (None, 300 + 150 * save["aegis"], line) if save["aegis"] < 4 else ("MAX", None, line)
    if kind == "prem_revive3":
        line = "OWNED %d / 9" % save["revives"]
        return (None, 200, line) if save["revives"] <= 6 else ("MAX", None, line)
    if kind == "prem_bomb5":
        line = "OWNED %d / 9" % save["bombs"]
        return (None, 200, line) if save["bombs"] <= 4 else ("MAX", None, line)
    return None, 40, ""


def equip_item(kind):
    """تجهيز عنصر مملوك (سلاح / مركبة / طلاء / أثر)."""
    if kind.startswith("w_"):
        save["equipped"] = kind[2:]
    elif kind.startswith("s_"):
        save["ship"] = kind[2:]
        for p in (game.players if game else []):
            p.stats()
            p.health = min(p.health, p.max_health)
            p.shield = min(p.shield, p.shield_max)
            p.specials = min(p.specials, p.max_special)
        _menu_ship_cache.clear()
    elif kind.startswith("skin_"):
        save["skin"] = kind[5:]
    elif kind.startswith("trail_"):
        save["trail"] = kind[6:]


def shop_buy(i):
    """ينفذ الشراء أو التجهيز ويعيد رسالة للاعب. العملة: عادية أو كريستال."""
    kind, _, _, _, cur = SHOP[i]
    status, price, _ = shop_info(i)
    if price is None:
        if kind in BUNDLES:
            sfx("deny")
            return "ALREADY OWNED"
        if status and status.startswith("OWNED"):
            equip_item(kind)
            sfx("buy")
            write_save()
            return "EQUIPPED"
        if status and status.startswith("EQUIPPED - PRESS"):
            save["trail"] = "cyan"
            sfx("click")
            write_save()
            return "TRAIL REMOVED"
        sfx("deny")
        return "ALREADY AT MAX" if status in ("MAX", "MAX LEVEL") else "ALREADY OWNED"
    bal = save["crystals"] if cur == "g" else save["coins"]
    if bal < price:
        sfx("deny")
        return "NOT ENOUGH CRYSTALS - PRESS R TO RECHARGE" if cur == "g" else "NOT ENOUGH COINS"
    if cur == "g":
        save["crystals"] -= price
    else:
        save["coins"] -= price
    ps = game.players if game else []
    if kind.startswith("w_"):
        save["weapons"].append(kind[2:])
        save["equipped"] = kind[2:]
    elif kind.startswith("s_"):
        save["ships"].append(kind[2:])
        equip_item(kind)
    elif kind.startswith("skin_"):
        save["skins"].append(kind[5:])
        save["skin"] = kind[5:]
    elif kind.startswith("trail_"):
        save["trails"].append(kind[6:])
        save["trail"] = kind[6:]
    elif kind in BUNDLES:
        apply_grants(BUNDLES[kind][1])
    elif kind == "upgrade":
        save["power"] += 1
    elif kind in LVL_UPG:
        save[LVL_UPG[kind][0]] += 1
    elif kind == "hull":
        save["max_health"] += 1
    elif kind == "special":
        save["max_special"] += 1
    elif kind == "shield":
        save["max_shield"] += 25
    elif kind == "drone":
        save["drones"] += 1
    elif kind == "revive":
        save["revives"] += 1
    elif kind == "bombitem":
        save["bombs"] += 1
    elif kind == "prem_coin2":
        save["coin2"] = True
    elif kind == "prem_drone2":
        save["drone2"] = True
    elif kind == "aegis":
        save["aegis"] += 1
    elif kind == "prem_revive3":
        save["revives"] = min(9, save["revives"] + 3)
    elif kind == "prem_bomb5":
        save["bombs"] = min(9, save["bombs"] + 5)
    for p in ps:  # تطبيق القدرات الجديدة فوراً على اللاعبين الحاليين
        p.stats()
        if kind in ("hull", "repair") or kind.startswith("s_"):
            p.health = p.max_health
        if kind in ("shield", "repair", "aegis") or kind.startswith("s_"):
            p.shield = p.shield_max
        if kind in ("special", "repair"):
            p.specials = p.max_special
        if kind == "repair":
            p.alive = True
            p.health = p.max_health
    sfx("crystal" if cur == "g" else "buy")
    write_save()
    return "PURCHASED!"

# ================= الواجهة والقوائم =================
U = SimpleNamespace(state="menu", sel=dict(menu=0, shop=0, settings=0, recharge=0), menu_level=1, page=0, tabs=[], pass_view=1, dmsg="", dmsg_t=0,
                    code="", rmsg="", rmsg_ok=False, rmsg_t=0, recharge_back="menu",
                    confirm=False, rebind=None, msg="", msg_t=0, rects=[], running=True,
                    shop_back="menu", earned=0, ad_rects=[], ad_pending=False, ad_msg="", dead_ad_used=False, reward_doubled=False,
                    recharge_ad_rect=None, crystal_ad_count=0)
MENU_ROWS = ["play", "mode", "shop", "recharge", "pass", "daily", "settings", "new", "quit"]
SET_ROWS = ["sfx", "music", "difficulty", "shake", "bloom", "scan", "autofire", "b_shield", "b_special",
            "b_weapon", "b_pause", "b_bomb", "fullscreen", "back"]
DIFF_NAMES = ["EASY", "NORMAL", "HARD"]

# دوال رسم القوائم: panel = لوحة شفافة، draw_row = صف قائمة
def panel(x, y, w, h, border=GOLD):
    """لوحة هولوغرامية بزوايا مقطوعة وخطوط مسح خفيفة (واجهة عام 2500)."""
    c = 10
    local = [(c, 0), (w - c, 0), (w, c), (w, h - c), (w - c, h), (c, h), (0, h - c), (0, c)]
    sf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(sf, (6, 14, 36, 190), local)
    for yy in range(4, h, 6):
        pygame.draw.line(sf, (60, 120, 200, 22), (3, yy), (w - 3, yy))
    canvas.blit(sf, (x, y))
    pygame.draw.polygon(canvas, border, [(x + px, y + py) for px, py in local], 2)
    pygame.draw.line(canvas, WHITE, (x + c, y), (x + c + 12, y), 2)
    pygame.draw.line(canvas, WHITE, (x + w - c - 12, y + h), (x + w - c, y + h), 2)

def draw_row(rect, selected, label, value=None, col=WHITE):
    if selected:
        add_glow(canvas, rect.centerx, rect.centery, rect.w // 2, (40, 40, 10))
        pygame.draw.rect(canvas, GOLD, rect, 2, border_radius=8)
    text(label, F_M, GOLD_LIGHT if selected else col, rect.x + 16, rect.centery - 11)
    if value is not None:
        text(value, F_M, CYAN if selected else GRAY_L, rect.right - 16, rect.centery - 11, right=True)

def start_run(level, ad_continue=False):
    if not ad_continue:
        U.dead_ad_used = False
    game.start_level(level, fresh=True)
    U.ad_pending = False
    U.ad_msg = ""
    U.state = "playing"

def go_menu():
    write_save()
    U.menu_level = save["level"]
    U.state = "menu"
    set_music("menu")

# شاشة القائمة الرئيسية
def draw_menu():
    space.draw(canvas)
    t = pygame.time.get_ticks() / 1000.0
    add_glow(canvas, WIDTH // 2, 120, 190, (70, 25, 130))
    text("STARFALL", F_T, RED_LIGHT, WIDTH // 2, 98, center=True)
    text("GALAXY ATTACK", F_XL, CYAN, WIDTH // 2, 162, center=True)
    text("THE LAST FLEET  -  YEAR 2500", F_S, GOLD_LIGHT, WIDTH // 2, 200, center=True)
    if vip_active():
        text("VIP ACTIVE - %d DAYS LEFT" % max(1, int((save["vip_until"] - time.time()) // 86400)), F_S, GOLD, WIDTH // 2, 216, center=True)
    sweep = int((pygame.time.get_ticks() / 12) % HEIGHT)
    pygame.draw.line(canvas, (40, 90, 140), (0, sweep), (WIDTH, sweep), 1)
    ms = get_menu_ship()
    canvas.blit(ms, ms.get_rect(center=(130, int(480 + math.sin(t * 2) * 8))))
    canvas.blit(MENU_BOSS, MENU_BOSS.get_rect(center=(WIDTH - 130, int(470 + math.sin(t * 1.6) * 8))))
    U.rects = []
    for i, row in enumerate(MENU_ROWS):
        r = pygame.Rect(WIDTH // 2 - 230, 222 + i * 38, 460, 34)
        U.rects.append((r, i))
        if row == "play":
            ml = U.menu_level
            lab = "CONTINUE" if save["level"] > 1 else "START"
            val = "< LEVEL %d >%s" % (ml, " BOSS" if ml % BOSS_EVERY == 0 else "")
            draw_row(r, U.sel["menu"] == i, lab, val)
        elif row == "mode":
            draw_row(r, U.sel["menu"] == i, "MODE", "2 PLAYERS" if save["two_players"] else "1 PLAYER")
        elif row == "shop":
            draw_row(r, U.sel["menu"] == i, "SHOP", "COINS %d" % save["coins"])
        elif row == "recharge":
            draw_row(r, U.sel["menu"] == i, "RECHARGE", "CRYSTALS %d" % save["crystals"], (210, 150, 255))
        elif row == "pass":
            draw_row(r, U.sel["menu"] == i, "STARFALL PASS", "TIER %d / %d" % (pass_tier(), PASS_TIERS), GOLD_LIGHT)
        elif row == "daily":
            draw_row(r, U.sel["menu"] == i, "DAILY REWARD", "READY!" if daily_state()[1] else "CLAIMED",
                     GREEN if daily_state()[1] else WHITE)
        elif row == "settings":
            draw_row(r, U.sel["menu"] == i, "SETTINGS")
        elif row == "new":
            draw_row(r, U.sel["menu"] == i, "NEW GAME", "PRESS AGAIN TO ERASE!" if U.confirm else None,
                     RED_LIGHT if U.confirm else WHITE)
        else:
            draw_row(r, U.sel["menu"] == i, "QUIT")
    text("REACHED LEVEL %d / %d    HIGH SCORE %d" % (save["level"], MAX_LEVEL, save["high_score"]),
         F_S, GOLD, WIDTH // 2, 582, center=True)
    b = save["binds"]
    text("MOVE ARROWS/WASD   %s SHIELD   %s SPECIAL   %s WEAPON   B SHOP   %s PAUSE" %
         (kname(b["shield"]), kname(b["special"]), kname(b["weapon"]), kname(b["pause"])),
         F_S, GRAY_L, WIDTH // 2, 640, center=True)
    text("PROGRESS IS SAVED AUTOMATICALLY", F_S, GRAY_L, WIDTH // 2, 662, center=True)

# نص قيمة كل صف في شاشة الإعدادات
def setting_value(row):
    if row == "sfx":
        return "< %d / 10 >" % save["sfx"]
    if row == "music":
        return "< %d / 10 >" % save["music"]
    if row == "difficulty":
        return "< %s >" % DIFF_NAMES[save["difficulty"]]
    if row == "shake":
        return "ON" if save["shake"] else "OFF"
    if row in ("bloom", "scan"):
        return "ON" if save[row] else "OFF"
    if row == "autofire":
        return "ON" if save["autofire"] else "OFF (HOLD SPACE / ENTER)"
    if row.startswith("b_"):
        if U.rebind == row[2:]:
            return "PRESS A KEY..."
        return kname(save["binds"][row[2:]])
    return None

SET_LABELS = dict(sfx="SOUND EFFECTS", music="MUSIC", difficulty="DIFFICULTY", shake="SCREEN SHAKE",
                  bloom="GLOW EFFECT (BLOOM)", scan="SCANLINES",
                  autofire="AUTO FIRE", b_shield="KEY: SHIELD", b_special="KEY: SPECIAL",
                  b_weapon="KEY: SWITCH WEAPON", b_pause="KEY: PAUSE", b_bomb="KEY: USE BOMB", fullscreen="FULLSCREEN (F11)", back="BACK")

# تغيير إعداد (d = -1/+1 للأسهم، 0 للضغط على Enter)
def change_setting(row, d):
    if row == "sfx":
        save["sfx"] = clamp(save["sfx"] + d, 0, 10)
        apply_volumes()
        sfx("coin")
    elif row == "music":
        save["music"] = clamp(save["music"] + d, 0, 10)
        apply_volumes()
    elif row == "difficulty":
        save["difficulty"] = clamp(save["difficulty"] + d, 0, 2)
    elif row == "shake" and d == 0:
        save["shake"] = not save["shake"]
    elif row in ("bloom", "scan") and d == 0:
        save[row] = not save[row]
    elif row == "autofire" and d == 0:
        save["autofire"] = not save["autofire"]
    elif row.startswith("b_") and d == 0:
        U.rebind = row[2:]
    elif row == "fullscreen" and d == 0:
        pygame.display.toggle_fullscreen()
    elif row == "back" and d == 0:
        write_save()
        U.state = U.shop_back if U.shop_back == "pause" else "menu"
    write_save() if row not in ("back",) else None

# شاشة الإعدادات
def draw_settings():
    space.draw(canvas)
    text("SETTINGS", F_XL, GOLD, WIDTH // 2, 54, center=True)
    U.rects = []
    for i, row in enumerate(SET_ROWS):
        r = pygame.Rect(WIDTH // 2 - 300, 100 + i * 36, 600, 32)
        U.rects.append((r, i))
        draw_row(r, U.sel["settings"] == i, SET_LABELS[row], setting_value(row))
    text("LEFT / RIGHT TO CHANGE   ENTER TO SELECT   ESC TO GO BACK", F_S, GRAY_L, WIDTH // 2, 672, center=True)

def draw_shop():
    """يرسم المتجر: تبويبات الصفحات الست ثم بطاقات العناصر (3 × 3) مع رصيد العملتين."""
    space.draw(canvas)
    text("STARFALL SHOP", F_XL, GOLD, WIDTH // 2, 36, center=True)
    canvas.blit(get_icon("coin", 32), (40, 62))
    text("COINS %d" % save["coins"], F_M, GOLD, 78, 68)
    canvas.blit(get_icon("crystal", 32), (WIDTH - 262, 62))
    text("CRYSTALS %d" % save["crystals"], F_M, (210, 150, 255), WIDTH - 224, 68)
    text("[R] RECHARGE CRYSTALS", F_S, (210, 150, 255), WIDTH - 40, 100, right=True)
    text("WEAPON: %s LV %d     SHIP: %s" % (save["equipped"].upper(), save["power"], SHIP_DEFS[save["ship"]]["name"]),
         F_S, CYAN, 40, 100)
    U.rects = []
    U.tabs = []
    for pi, name in enumerate(SHOP_PAGES):
        r = pygame.Rect(30 + pi * 122, 126, 116, 30)
        U.tabs.append((r, pi))
        on = pi == U.page
        prem = name in ("PREMIUM", "BUNDLES")
        pygame.draw.rect(canvas, (60, 40, 100) if on and prem else (40, 50, 90) if on else (14, 20, 44), r, border_radius=6)
        pygame.draw.rect(canvas, (210, 150, 255) if prem else GOLD if on else (60, 80, 130), r, 2, border_radius=6)
        text(name, F_S, (230, 190, 255) if prem else GOLD_LIGHT if on else GRAY_L, r.centerx, r.centery, center=True)
    items = page_items()
    U.sel["shop"] = min(U.sel["shop"], len(items) - 1)
    cw, ch = 270, 132
    for n, i in enumerate(items):
        kind, _, name, desc, cur = SHOP[i]
        cx = 30 + (n % 3) * 285
        cy = 168 + (n // 3) * 142
        r = pygame.Rect(cx, cy, cw, ch)
        U.rects.append((r, n))
        sel = U.sel["shop"] == n
        status, price, line = shop_info(i)
        panel(cx, cy, cw, ch, GOLD if sel else (190, 120, 255) if cur == "g" else (60, 80, 130))
        if sel:
            add_glow(canvas, r.centerx, r.centery, 150, (40, 36, 10))
        canvas.blit(get_icon(shop_icon_kind(kind), 84), (cx + 8, cy + 24))
        text("%d" % (n + 1), F_S, GRAY_L, cx + 10, cy + 8)
        text(name, F_M, GOLD_LIGHT if sel else WHITE, cx + 100, cy + 14)
        text(desc, F_S, GRAY_L, cx + 100, cy + 42)
        if line:
            text(line, F_S, CYAN, cx + 100, cy + 62)
        if price is not None:
            bal = save["crystals"] if cur == "g" else save["coins"]
            can = bal >= price
            canvas.blit(get_icon("crystal" if cur == "g" else "coin", 28), (cx + 96, cy + 92))
            okcol = (210, 150, 255) if cur == "g" else GOLD
            text(str(price), F_M, okcol if can else RED_LIGHT, cx + 128, cy + 96)
        else:
            text(status, F_S, GREEN if "EQUIP" in status or status == "ACTIVE" else GOLD, cx + 100, cy + 100)
    if U.msg_t > 0:
        text(U.msg, F_M, GOLD_LIGHT, WIDTH // 2, 626, center=True)
    text("ARROWS: SELECT   Q / E / TAB: PAGE   ENTER or 1-9: BUY   R: RECHARGE   ESC or B: BACK", F_S, GRAY_L, WIDTH // 2, 668, center=True)
    if ANDROID:
        pygame.draw.rect(canvas, (25, 55, 90), TOUCH_BACK_RECT, border_radius=8)
        pygame.draw.rect(canvas, LIGHT_BLUE, TOUCH_BACK_RECT, 2, border_radius=8)
        text("BACK", F_M, WHITE, TOUCH_BACK_RECT.centerx, TOUCH_BACK_RECT.centery, center=True)


def draw_recharge():
    """شاشة المبيعات: منتجات الشحن + خانة كود الشحن. الأسهم لاختيار منتج، ENTER للشراء أو لاستبدال الكود."""
    space.draw(canvas)
    text("STORE  -  RECHARGE", F_XL, (210, 150, 255), WIDTH // 2, 40, center=True)
    canvas.blit(get_icon("crystal", 32), (WIDTH // 2 - 120, 74))
    text("BALANCE: %d" % save["crystals"], F_M, WHITE, WIDTH // 2 - 80, 80)
    for i, sku in enumerate(CODE_SKUS):
        name, price, gr = PRODUCTS[sku]
        r = pygame.Rect(60 + (i // 5) * 395, 118 + (i % 5) * 58, 380, 52)
        sel = U.sel["recharge"] == i
        panel(r.x, r.y, r.w, r.h, GOLD if sel else (190, 120, 255))
        canvas.blit(get_icon("crystal" if "crystals" in sku else "pass" if "pass" in sku else "bundle", 38), (r.x + 8, r.y + 7))
        text(name, F_M, GOLD_LIGHT if sel else WHITE, r.x + 56, r.y + 6)
        text(reward_text(gr)[:34], F_S, GRAY_L, r.x + 56, r.y + 30)
        text(price, F_M, GOLD, r.right - 12, r.y + 14, right=True)
    # زر إعلان مكافأة: لا يمنح شيئاً إلا بعد تأكيد جسر الإعلانات مشاهدة الإعلان كاملاً.
    U.recharge_ad_rect = pygame.Rect(230, 410, 440, 42)
    ad_ready = not U.ad_pending and U.crystal_ad_count < 5
    pygame.draw.rect(canvas, (10, 48, 38) if ad_ready else (35, 42, 55), U.recharge_ad_rect, border_radius=8)
    pygame.draw.rect(canvas, GREEN if ad_ready else GRAY, U.recharge_ad_rect, 2, border_radius=8)
    ad_label = "WATCH AD: +25 NOVA CRYSTALS (%d/5)" % U.crystal_ad_count if ad_ready else ("AD IN PROGRESS..." if U.ad_pending else "SESSION CRYSTAL ADS USED")
    text(ad_label, F_M, WHITE if ad_ready else GRAY_L, U.recharge_ad_rect.centerx, U.recharge_ad_rect.centery, center=True)
    text("Arrows: choose product   ENTER (empty box): buy   F1: open store page", F_S, GRAY_L, WIDTH // 2, 465, center=True)
    text("After buying a code, type or paste it below (Ctrl+V) and press ENTER", F_S, GRAY_L, WIDTH // 2, 442, center=True)
    box = pygame.Rect(150, 500, 600, 50)
    panel(box.x, box.y, box.w, box.h, (210, 150, 255))
    cursor = "_" if (pygame.time.get_ticks() // 400) % 2 == 0 else " "
    text((U.code + cursor) if U.code else "SF-XXXXX-XXXXX-XXXXX-XXXXX", F_L,
         WHITE if U.code else GRAY_D, box.centerx, box.centery, center=True)
    if U.rmsg_t > 0:
        text(U.rmsg, F_M, GREEN if U.rmsg_ok else RED_LIGHT, WIDTH // 2, 570, center=True)
    text("Crystals come from purchases/codes or confirmed rewarded ads.", F_S, GRAY_L, WIDTH // 2, 615, center=True)
    text("ENTER: BUY / REDEEM    CTRL+V: PASTE    BACKSPACE: DELETE    ESC: BACK", F_S, GRAY_L, WIDTH // 2, 668, center=True)
    if ANDROID:
        pygame.draw.rect(canvas, (25, 55, 90), TOUCH_BACK_RECT, border_radius=8)
        pygame.draw.rect(canvas, LIGHT_BLUE, TOUCH_BACK_RECT, 2, border_radius=8)
        text("BACK", F_M, WHITE, TOUCH_BACK_RECT.centerx, TOUCH_BACK_RECT.centery, center=True)


def draw_pass():
    """تذكرة ستارفول: 30 مستوى، مسار مجاني ومسار مميز (يُفتح بالشراء)."""
    space.draw(canvas)
    tier = pass_tier()
    text("STARFALL PASS", F_XL, GOLD, WIDTH // 2, 40, center=True)
    text("TIER %d / %d      XP %d" % (tier, PASS_TIERS, save["pass_xp"]), F_M, WHITE, WIDTH // 2, 84, center=True)
    pygame.draw.rect(canvas, (20, 30, 60), (WIDTH // 2 - 200, 104, 400, 10))
    frac = 1.0 if tier >= PASS_TIERS else (save["pass_xp"] % PASS_XP_PER_TIER) / float(PASS_XP_PER_TIER)
    pygame.draw.rect(canvas, CYAN, (WIDTH // 2 - 200, 104, int(400 * frac), 10))
    text("PREMIUM TRACK: UNLOCKED" if save["pass_prem"] else "PREMIUM TRACK LOCKED  -  unlock in STORE (F1) or SHOP > BUNDLES",
         F_S, (210, 150, 255) if save["pass_prem"] else RED_LIGHT, WIDTH // 2, 126, center=True)
    for n in range(8):
        t = U.pass_view + n
        if t > PASS_TIERS:
            break
        y = 146 + n * 58
        panel(50, y, 800, 52, (60, 120, 200) if t <= tier else (50, 60, 90))
        text("TIER %d" % t, F_M, GOLD if t <= tier else GRAY, 66, y + 14)
        fs = "CLAIMED" if t in save["pass_free"] else ("READY" if t <= tier else "LOCKED")
        ps = "CLAIMED" if t in save["pass_paid"] else ("READY" if (t <= tier and save["pass_prem"]) else "LOCKED")
        text("FREE:    " + reward_text(pass_reward(t, False)) + "   [" + fs + "]", F_S, WHITE, 190, y + 8)
        text("PREMIUM: " + reward_text(pass_reward(t, True)) + "   [" + ps + "]", F_S, (210, 150, 255), 190, y + 28)
    if U.dmsg_t > 0:
        text(U.dmsg, F_M, GOLD_LIGHT, WIDTH // 2, 626, center=True)
    text("Earn XP by clearing levels and bosses.   UP/DOWN: scroll   ENTER: claim all   F1: store   ESC: back",
         F_S, GRAY_L, WIDTH // 2, 668, center=True)


def draw_daily():
    """المكافأة اليومية: 7 أيام متتالية، وفي اليوم السابع جائزة كبيرة."""
    space.draw(canvas)
    text("DAILY REWARD", F_XL, GOLD, WIDTH // 2, 54, center=True)
    day, ok = daily_state()
    for i, gr in enumerate(DAILY_REWARDS):
        r = pygame.Rect(40 + (i % 4) * 210, 130 + (i // 4) * 170, 190, 150)
        here = ok and i == day
        done = (i < day) if ok else (i <= (save["daily_day"] - 1) % 7 and save["daily_day"] != 0 or save["daily_day"] == 0)
        panel(r.x, r.y, r.w, r.h, GREEN if here else (60, 80, 130))
        text("DAY %d" % (i + 1), F_M, GOLD_LIGHT if here else WHITE, r.centerx, r.y + 20, center=True)
        for k, part in enumerate(reward_text(gr).split(" + ")):
            text(part, F_S, WHITE, r.centerx, r.y + 62 + k * 22, center=True)
        if here:
            text("READY!", F_M, GREEN, r.centerx, r.bottom - 22, center=True)
    if vip_active():
        text("VIP BONUS: +25 CRYSTALS EVERY DAY", F_M, GOLD, WIDTH // 2, 480, center=True)
    else:
        text("Tip: VIP members get +25 crystals every day and +50% coins", F_S, GRAY_L, WIDTH // 2, 480, center=True)
    if U.dmsg_t > 0:
        text(U.dmsg, F_M, GOLD_LIGHT, WIDTH // 2, 540, center=True)
    text("ENTER: CLAIM TODAY'S REWARD    ESC: BACK", F_S, GRAY_L, WIDTH // 2, 668, center=True)


# ================= الإعلانات الاختيارية (Rewarded Ads) =================
# لا تُمنح أي مكافأة بمجرد الضغط على الزر؛ يجب أن يؤكد جسر AdMob
# اكتمال مشاهدة الإعلان. ملف الجسر الأصلي يُضاف عند ربط SDK الخاص بأندرويد.
ADS_RESULT_EVENT = pygame.USEREVENT + 17

def request_rewarded_ad(placement):
    """يطلب إعلاناً مكافئاً من جسر أندرويد، ويرجع False إن لم يكن الجسر جاهزاً."""
    if U.ad_pending:
        return False
    try:
        # الجسر يضاف فقط في نسخة Android المربوطة بـ AdMob؛ لا ينبغي
        # أن يمنع غيابه بناء اللعبة أو تشغيلها على الكمبيوتر.
        starfall_ads_native = importlib.import_module("starfall_ads_native")
        def finished(watched_completely):
            try:
                pygame.event.post(pygame.event.Event(
                    ADS_RESULT_EVENT,
                    placement=placement,
                    rewarded=bool(watched_completely)))
            except Exception:
                pass
        started = starfall_ads_native.show_rewarded_ad(placement, finished)
        if started:
            U.ad_pending = True
            U.ad_msg = "LOADING REWARDED AD..."
            return True
    except Exception:
        pass
    U.ad_msg = "REWARDED ADS ARE NOT CONNECTED YET"
    U.ad_pending = False
    return False


def request_crystal_ad():
    """يطلب إعلاناً مكافئاً يمنح 25 كريستالة بعد تأكيد المشاهدة الكاملة."""
    if U.crystal_ad_count >= 5:
        U.ad_msg = "DAILY CRYSTAL ADS USED"
        return False
    return request_rewarded_ad("crystal_reward")

def draw_ad_actions():
    """أزرار اختيارية تظهر بعد الخسارة أو إنهاء المرحلة، وتعمل باللمس والفأرة."""
    U.ad_rects = []
    if U.state not in ("dead", "clear", "win"):
        return
    y = 555
    left = pygame.Rect(105, y, 330, 58)
    right = pygame.Rect(465, y, 330, 58)
    if U.state == "dead":
        enabled = not U.dead_ad_used and not U.ad_pending
        label = "WATCH AD: CONTINUE" if enabled else ("AD IN PROGRESS..." if U.ad_pending else "CONTINUE AD USED")
        color = GREEN if enabled else GRAY
        pygame.draw.rect(canvas, (10, 48, 38), left, border_radius=10)
        pygame.draw.rect(canvas, color, left, 2, border_radius=10)
        text(label, F_M, WHITE if enabled else GRAY_L, left.centerx, left.centery, center=True)
        pygame.draw.rect(canvas, (35, 25, 12), right, border_radius=10)
        pygame.draw.rect(canvas, GOLD, right, 2, border_radius=10)
        text("RETRY LEVEL", F_M, GOLD_LIGHT, right.centerx, right.centery, center=True)
        U.ad_rects = [(left, "dead_ad"), (right, "dead_retry")]
    else:
        enabled = not U.reward_doubled and not U.ad_pending
        label = "WATCH AD: DOUBLE COINS" if enabled else ("AD IN PROGRESS..." if U.ad_pending else "REWARD ALREADY DOUBLED")
        color = GREEN if enabled else GRAY
        pygame.draw.rect(canvas, (10, 48, 38), left, border_radius=10)
        pygame.draw.rect(canvas, color, left, 2, border_radius=10)
        text(label, F_M, WHITE if enabled else GRAY_L, left.centerx, left.centery, center=True)
        pygame.draw.rect(canvas, (12, 30, 55), right, border_radius=10)
        pygame.draw.rect(canvas, CYAN, right, 2, border_radius=10)
        right_label = "MAIN MENU" if U.state == "win" else "NEXT LEVEL"
        text(right_label, F_M, CYAN, right.centerx, right.centery, center=True)
        U.ad_rects = [(left, "clear_ad"), (right, "win_menu" if U.state == "win" else "clear_next")]
    if U.ad_msg:
        text(U.ad_msg, F_S, GOLD_LIGHT if "NOT CONNECTED" not in U.ad_msg else RED_LIGHT,
             WIDTH // 2, 635, center=True)

def handle_ad_action(action):
    if action == "dead_ad" and U.state == "dead" and not U.dead_ad_used:
        request_rewarded_ad("continue_after_defeat")
    elif action == "dead_retry" and U.state == "dead":
        start_run(game.level)
    elif action == "clear_ad" and U.state in ("clear", "win") and not U.reward_doubled:
        request_rewarded_ad("double_level_coins")
    elif action == "clear_next" and U.state == "clear":
        game.start_level(game.level + 1)
        U.state = "playing"
    elif action == "win_menu" and U.state == "win":
        go_menu()

# شاشة نصية فوق المشهد (إنهاء مرحلة / خسارة / فوز)
def draw_center_screen(title, tcol, lines, hint):
    game.draw()
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 170))
    canvas.blit(ov, (0, 0))
    text(title, F_XL, tcol, WIDTH // 2, 190, center=True)
    y = 270
    for ln, col in lines:
        text(ln, F_M, col, WIDTH // 2, y, center=True)
        y += 38
    text(hint, F_S, GRAY_L, WIDTH // 2, y + 40, center=True)

# ================= الإدخال (لوحة المفاتيح والفأرة) =================

# تنفيذ اختيار من القائمة الرئيسية
def menu_activate():
    row = MENU_ROWS[U.sel["menu"]]
    sfx("click")
    if row != "new":
        U.confirm = False
    if row == "play":
        start_run(U.menu_level)
    elif row == "mode":
        save["two_players"] = not save["two_players"]
        write_save()
    elif row == "shop":
        U.shop_back = "menu"
        U.state = "shop"
    elif row == "recharge":
        U.recharge_back = "menu"
        U.code = ""
        U.state = "recharge"
    elif row == "pass":
        U.pass_view = max(1, min(PASS_TIERS - 7, pass_tier() - 1))
        U.state = "pass"
    elif row == "daily":
        U.state = "daily"
    elif row == "settings":
        U.shop_back = "menu"
        U.state = "settings"
    elif row == "new":
        if U.confirm:
            keep = {k: save[k] for k in ("high_score", "sfx", "music", "difficulty", "shake", "autofire", "two_players", "binds")}
            save.clear()
            save.update(default_save())
            save.update(keep)
            write_save()
            U.menu_level = 1
            U.confirm = False
            game.score = 0
        else:
            U.confirm = True
    elif row == "quit":
        U.running = False

def settings_activate():
    change_setting(SET_ROWS[U.sel["settings"]], 0)

def shop_activate():
    items = page_items()
    n = U.sel["shop"]
    if n < len(items):
        U.msg = shop_buy(items[n])
        U.msg_t = 90

def set_page(d):
    U.page = (U.page + d) % len(SHOP_PAGES)
    U.sel["shop"] = 0
    sfx("click")

# معالجة ضغط المفاتيح حسب حالة اللعبة (قائمة / لعب / إيقاف / متجر / ...)
def key_down(key):
    st = U.state
    b = save["binds"]
    if key == pygame.K_F11:
        pygame.display.toggle_fullscreen()
        return
    if U.rebind:
        if key != pygame.K_ESCAPE:
            save["binds"][U.rebind] = key
            write_save()
        U.rebind = None
        return
    if st == "menu":
        n = len(MENU_ROWS)
        s = U.sel["menu"]
        if key == pygame.K_UP:
            U.sel["menu"] = (s - 1) % n
            sfx("click")
        elif key == pygame.K_DOWN:
            U.sel["menu"] = (s + 1) % n
            sfx("click")
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            d = -1 if key == pygame.K_LEFT else 1
            if MENU_ROWS[s] == "play":
                U.menu_level = clamp(U.menu_level + d, 1, save["level"])
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    U.menu_level = clamp(U.menu_level + 9 * d, 1, save["level"])
                sfx("click")
            elif MENU_ROWS[s] == "mode":
                save["two_players"] = not save["two_players"]
                write_save()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            menu_activate()
        elif key == pygame.K_ESCAPE:
            U.running = False
    elif st == "settings":
        n = len(SET_ROWS)
        s = U.sel["settings"]
        if key == pygame.K_UP:
            U.sel["settings"] = (s - 1) % n
        elif key == pygame.K_DOWN:
            U.sel["settings"] = (s + 1) % n
        elif key == pygame.K_LEFT:
            change_setting(SET_ROWS[s], -1)
        elif key == pygame.K_RIGHT:
            change_setting(SET_ROWS[s], 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            settings_activate()
        elif key == pygame.K_ESCAPE:
            write_save()
            U.state = U.shop_back if U.shop_back == "pause" else "menu"
    elif st == "shop":
        n = len(page_items())
        s = min(U.sel["shop"], n - 1)
        if key == pygame.K_LEFT:
            U.sel["shop"] = (s - 1) % n
        elif key == pygame.K_RIGHT:
            U.sel["shop"] = (s + 1) % n
        elif key == pygame.K_UP:
            U.sel["shop"] = s - 3 if s >= 3 else s
        elif key == pygame.K_DOWN:
            U.sel["shop"] = s + 3 if s + 3 < n else s
        elif key == pygame.K_q:
            set_page(-1)
        elif key in (pygame.K_e, pygame.K_TAB):
            set_page(1)
        elif key == pygame.K_r:
            U.recharge_back = "shop"
            U.code = ""
            U.state = "recharge"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            shop_activate()
        elif pygame.K_1 <= key <= pygame.K_9:
            if key - pygame.K_1 < n:
                U.sel["shop"] = key - pygame.K_1
                shop_activate()
        elif key in (pygame.K_ESCAPE, pygame.K_b):
            write_save()
            U.state = U.shop_back
    elif st == "recharge":
        if key == pygame.K_ESCAPE:
            U.state = U.recharge_back
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if U.code:
                ok, U.rmsg = redeem_code(U.code)
                U.rmsg_ok = ok
                if ok:
                    U.code = ""
                    sfx("crystal")
                else:
                    sfx("deny")
            else:  # بلا كود: زر الشراء للمنتج المحدد
                U.rmsg = request_purchase(CODE_SKUS[U.sel["recharge"]])
                U.rmsg_ok = True
            U.rmsg_t = 300
        elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            d = {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_LEFT: -5, pygame.K_RIGHT: 5}[key]
            U.sel["recharge"] = (U.sel["recharge"] + d) % len(CODE_SKUS)
        elif key == pygame.K_BACKSPACE:
            U.code = U.code[:-1]
        elif key == pygame.K_F1:
            try:
                webbrowser.open(STORE_URL)
            except Exception:
                pass
    elif st == "pass":
        if key == pygame.K_ESCAPE:
            U.state = "menu"
        elif key == pygame.K_UP:
            U.pass_view = max(1, U.pass_view - 1)
        elif key == pygame.K_DOWN:
            U.pass_view = min(PASS_TIERS - 7, U.pass_view + 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            n = claim_pass()
            U.dmsg = "CLAIMED %d REWARDS" % n if n else "NOTHING TO CLAIM"
            U.dmsg_t = 200
            sfx("powerup" if n else "deny")
        elif key == pygame.K_F1:
            U.recharge_back = "pass"
            U.state = "recharge"
            U.code = ""
    elif st == "daily":
        if key == pygame.K_ESCAPE:
            U.state = "menu"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            U.dmsg = claim_daily()
            U.dmsg_t = 240
            sfx("powerup" if U.dmsg.startswith("CLAIMED") else "deny")
    elif st == "playing":
        if key == b["pause"] or key == pygame.K_ESCAPE:
            U.state = "pause"
        elif key == pygame.K_b:
            U.shop_back = "pause"
            U.state = "shop"
        elif key == b["shield"]:
            game.players[0].toggle_shield()
        elif key == pygame.K_RSHIFT and len(game.players) > 1:
            game.players[1].toggle_shield()
        elif key == b["bomb"]:
            game.use_bomb()
        elif key == b["special"]:
            game.players[0].special(game)
        elif key == pygame.K_RCTRL and len(game.players) > 1:
            game.players[1].special(game)
        elif key == b["weapon"]:
            ws = save["weapons"]
            save["equipped"] = ws[(ws.index(save["equipped"]) + 1) % len(ws)]
            sfx("click")
    elif st == "pause":
        if key in (b["pause"], pygame.K_ESCAPE, pygame.K_RETURN):
            U.state = "playing"
        elif key == pygame.K_b:
            U.shop_back = "pause"
            U.state = "shop"
        elif key == pygame.K_o:
            U.shop_back = "pause"
            U.state = "settings"
        elif key == pygame.K_m:
            go_menu()
    elif st == "clear":
        if key == pygame.K_d and not U.reward_doubled:
            request_rewarded_ad("double_level_coins")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            game.start_level(game.level + 1)
            U.state = "playing"
        elif key == pygame.K_b:
            U.shop_back = "clear"
            U.state = "shop"
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            go_menu()
    elif st == "dead":
        if key == pygame.K_a and not U.dead_ad_used:
            request_rewarded_ad("continue_after_defeat")
        elif key in (pygame.K_r, pygame.K_RETURN):
            start_run(game.level)
        elif key == pygame.K_b:
            U.shop_back = "dead"
            U.state = "shop"
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            go_menu()
    elif st == "win":
        if key == pygame.K_d and not U.reward_doubled:
            request_rewarded_ad("double_level_coins")
        elif key in (pygame.K_RETURN, pygame.K_m, pygame.K_ESCAPE):
            go_menu()

def clipboard_text():
    """يقرأ نص الحافظة (للصق كود الشحن) إن توفر tkinter."""
    try:
        tkinter = importlib.import_module("tkinter")
        r = tkinter.Tk()
        r.withdraw()
        t = r.clipboard_get()
        r.destroy()
        return t
    except Exception:
        return ""


def char_input(ev):
    """إدخال الحروف في شاشة الشحن (Ctrl+V للصق)."""
    if U.state != "recharge":
        return
    if ev.mod & pygame.KMOD_CTRL and ev.key == pygame.K_v:
        U.code = "".join(c for c in clipboard_text().upper() if c.isalnum() or c == "-")[:28]
        return
    ch = ev.unicode.upper() if ev.unicode else ""
    if ch and (ch.isalnum() or ch == "-") and len(U.code) < 28:
        U.code += ch


# دعم الفأرة في القوائم والمتجر
def mouse_event(ev):
    st = U.state
    if st in ("shop", "recharge") and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if TOUCH_BACK_RECT.collidepoint(ev.pos):
            write_save()
            U.state = U.shop_back if st == "shop" else U.recharge_back
            sfx("click")
            return
    if st == "recharge":
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if U.recharge_ad_rect and U.recharge_ad_rect.collidepoint(ev.pos):
                request_crystal_ad()
                return
        return
    if st in ("dead", "clear", "win") and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        for rect, action in U.ad_rects:
            if rect.collidepoint(ev.pos):
                handle_ad_action(action)
                return
        return
    if st not in ("menu", "settings", "shop"):
        return
    key = "menu" if st == "menu" else "settings" if st == "settings" else "shop"
    if st == "shop" and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        for r, pi in U.tabs:
            if r.collidepoint(ev.pos):
                U.page = pi
                U.sel["shop"] = 0
                sfx("click")
                return
    for r, i in U.rects:
        if r.collidepoint(ev.pos):
            if ev.type == pygame.MOUSEMOTION:
                U.sel[key] = i
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                U.sel[key] = i
                if st == "menu":
                    menu_activate()
                elif st == "settings":
                    settings_activate()
                else:
                    shop_activate()
            break

# ================= الانتقال بين المراحل =================

# عند إنهاء المرحلة: مكافأة + حفظ التقدم + فتح المرحلة التالية
def on_level_clear():
    U.reward_doubled = False
    U.ad_msg = ""
    lvl = game.level
    add_pass_xp(50)
    bonus = 60 + lvl * 3
    bonus = add_coins(bonus)
    game.earned += bonus
    game.score += lvl * 50
    save["score"] = game.score
    save["level"] = max(save["level"], min(MAX_LEVEL, lvl + 1))
    if game.score > save["high_score"]:
        save["high_score"] = game.score
    write_save()
    sfx("clear" if lvl < MAX_LEVEL else "win")
    set_music("calm")
    U.state = "win" if lvl >= MAX_LEVEL else "clear"

# عند موت كل اللاعبين: حفظ أعلى نتيجة (العملات والترقيات تبقى)
def on_dead():
    if game.score > save["high_score"]:
        save["high_score"] = game.score
    save["score"] = game.score
    write_save()
    set_music("calm")
    U.state = "dead"


# ================= التحكم باللمس (أندرويد) =================
TOUCH = SimpleNamespace(last=None, fingers={})
TOUCH_BACK_RECT = pygame.Rect(WIDTH - 150, HEIGHT - 58, 130, 42)
TBTN = [("shield", "SHD", pygame.Rect(WIDTH - 90, HEIGHT - 150, 78, 60)),
        ("special", "SPC", pygame.Rect(WIDTH - 90, HEIGHT - 220, 78, 60)),
        ("bomb", "BMB", pygame.Rect(WIDTH - 90, HEIGHT - 290, 78, 60)),
        ("weapon", "WPN", pygame.Rect(12, HEIGHT - 150, 78, 60)),
        ("pause", "II", pygame.Rect(12, HEIGHT - 220, 78, 60)),
        ("shop", "SHOP", pygame.Rect(12, HEIGHT - 290, 78, 60))]

TPAUSE = [("resume", "RESUME", pygame.Rect(WIDTH // 2 - 180, 430, 160, 52)),
          ("shop", "SHOP", pygame.Rect(WIDTH // 2 + 20, 430, 160, 52)),
          ("settings", "SETTINGS", pygame.Rect(WIDTH // 2 - 180, 500, 160, 52)),
          ("menu", "MENU", pygame.Rect(WIDTH // 2 + 20, 500, 160, 52))]

def finger_pos(ev):
    ww, wh = pygame.display.get_window_size()
    # في Android نمدد canvas إلى مساحة النافذة كاملة، لذلك لا توجد حواف
    # letterbox ويصبح التحويل خطياً ومباشراً.
    return ev.x * ww * WIDTH / float(max(1, ww)), ev.y * wh * HEIGHT / float(max(1, wh))

def touch_event(ev):
    """زر = إجراء، وأي مكان آخر = سحب لتحريك المركبة. خارج اللعب يعمل اللمس كفأرة."""
    fid = ev.finger_id
    x, y = finger_pos(ev)
    if ev.type == pygame.FINGERDOWN:
        if U.state == "playing":
            for name, _, r in TBTN:
                if r.collidepoint(x, y):
                    TOUCH.fingers[fid] = name
                    if name == "shield":
                        game.players[0].toggle_shield()
                    elif name == "special":
                        game.players[0].special(game)
                    elif name == "bomb":
                        game.use_bomb()
                    elif name == "shop":
                        U.shop_back = "pause"
                        U.state = "shop"
                    else:
                        key_down(save["binds"].get(name, pygame.K_p))
                    return
            TOUCH.fingers[fid] = "move"
            TOUCH.last = (x, y)
        elif U.state == "pause":
            for name, _, r in TPAUSE:
                if r.collidepoint(x, y):
                    TOUCH.fingers[fid] = name
                    if name == "resume":
                        U.state = "playing"
                    elif name == "shop":
                        U.shop_back = "pause"
                        U.state = "shop"
                    elif name == "settings":
                        U.shop_back = "pause"
                        U.state = "settings"
                    elif name == "menu":
                        go_menu()
                    return
        else:
            pos = (int(x), int(y))
            mouse_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos))
            mouse_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    elif ev.type == pygame.FINGERMOTION:
        if TOUCH.fingers.get(fid) == "move" and TOUCH.last and game and game.players:
            dx, dy = x - TOUCH.last[0], y - TOUCH.last[1]
            TOUCH.last = (x, y)
            p = game.players[0]
            if p.alive:
                p.x = clamp(p.x + dx * 1.6, 50, WIDTH - 50)
                p.y = clamp(p.y + dy * 1.6, 140, HEIGHT - 60)
    elif ev.type == pygame.FINGERUP:
        TOUCH.fingers.pop(fid, None)

def draw_touch_buttons():
    for name, lab, r in TBTN:
        sf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(sf, (40, 90, 160, 110), sf.get_rect(), border_radius=14)
        pygame.draw.rect(sf, (120, 200, 255, 200), sf.get_rect(), 2, border_radius=14)
        canvas.blit(sf, r.topleft)
        text(lab, F_S, WHITE, r.centerx, r.centery, center=True, shadow=False)


def draw_pause_touch_buttons():
    for _, lab, r in TPAUSE:
        pygame.draw.rect(canvas, (30, 70, 115), r, border_radius=10)
        pygame.draw.rect(canvas, (120, 200, 255), r, 2, border_radius=10)
        text(lab, F_S, WHITE, r.centerx, r.centery, center=True, shadow=False)

# ================= التشغيل الرئيسي =================
MENU_BOSS = None
_menu_ship_cache = {}

def get_menu_ship():
    """صورة المركبة الكبيرة في القائمة (تتغير حسب المركبة المختارة)."""
    key = (save["ship"], save["skin"])
    if key not in _menu_ship_cache:
        _menu_ship_cache[key] = pygame.transform.smoothscale(get_player_sprite(0, key[0], 2, key[1]), (285, 255))
    return _menu_ship_cache[key]

_scan_surf = None
RED_VIG = None


def make_red_vignette():
    """وميض أحمر على الأطراف يظهر عند إصابة اللاعب."""
    sm = pygame.Surface((32, 24), pygame.SRCALPHA)
    for yy in range(24):
        for xx in range(32):
            d = math.hypot((xx - 15.5) / 16, (yy - 11.5) / 12)
            sm.set_at((xx, yy), (230, 10, 20, clamp(int((d - 0.35) * 255), 0, 255)))
    return pygame.transform.smoothscale(sm, (WIDTH, HEIGHT))


def make_scanlines():
    sf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for yy in range(0, HEIGHT, 3):
        pygame.draw.line(sf, (0, 0, 0, 34), (0, yy), (WIDTH, yy))
    return sf


def post_fx(surf):
    """مؤثرات ما بعد الرسم: توهج (Bloom) للأجزاء المضيئة + خطوط مسح سينمائية."""
    if save["bloom"]:
        small = pygame.transform.smoothscale(surf, (WIDTH // 4, HEIGHT // 4))
        small.fill((90, 90, 90), special_flags=pygame.BLEND_RGB_SUB)
        big = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
        surf.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    if save["scan"] and _scan_surf is not None:
        surf.blit(_scan_surf, (0, 0))


# تجهيز كل الرسومات والأصوات عند بدء التشغيل (يستغرق عدة ثوانٍ)
def init_assets():
    global space, HEART_ON, HEART_OFF, MISSILE_SPR, MENU_BOSS, MUSIC_CH, ENGINE_CH, game, DRONE_SPR, _scan_surf, RED_VIG
    show_loading("LOADING SPRITES...")
    for i in range(2):
        for t in range(3):
            get_player_sprite(i, save["ship"], t, save["skin"])
    DRONE_SPR = make_sprite(40, 40, draw_drone)
    for t, d in ENEMY_DEFS.items():
        spr = make_sprite(d["size"][0], d["size"][1], d["fn"])
        ENEMY_SPR[t] = pygame.transform.flip(spr, False, True)
    HEART_ON = make_sprite(22, 22, draw_heart_small, (240, 70, 95))
    HEART_OFF = make_sprite(22, 22, draw_heart_small, (60, 30, 45))
    MISSILE_SPR = make_sprite(24, 40, draw_missile_sprite)
    for i in range(4):
        ROCK_SPR.append(make_sprite(90, 90, draw_rock, 100 + i * 17))
    MENU_BOSS = pygame.transform.smoothscale(get_boss_sprite(0, 0, 0), (240, 200))
    if SOUND_ENABLED:
        show_loading("SYNTHESIZING SOUND...")
        MUSIC_CH = pygame.mixer.Channel(0)
        ENGINE_CH = pygame.mixer.Channel(1)
        build_sounds()
    space = Space()
    space.set_theme(0)
    _scan_surf = make_scanlines()
    RED_VIG = make_red_vignette()
    game = Game()
    U.menu_level = save["level"]
    set_music("menu")

# الحلقة الرئيسية للبرنامج: أحداث ثم تحديث ثم رسم
def main():
    init_assets()
    while U.running:
        clock.tick(FPS)
        for ev in pygame.event.get():
            if ev.type == ADS_RESULT_EVENT:
                U.ad_pending = False
                if getattr(ev, "rewarded", False):
                    placement = getattr(ev, "placement", "")
                    if placement == "continue_after_defeat" and U.state == "dead" and not U.dead_ad_used:
                        U.dead_ad_used = True
                        start_run(game.level, ad_continue=True)
                        U.dead_ad_used = True
                    elif placement == "double_level_coins" and U.state in ("clear", "win") and not U.reward_doubled:
                        # game.earned يحتوي بالفعل على قيمة العملات المضافة بعد المضاعفات والترقيات.
                        save["coins"] += int(game.earned)
                        game.earned *= 2
                        U.reward_doubled = True
                        U.ad_msg = "COINS DOUBLED!"
                        write_save()
                        sfx("coin")
                    elif placement == "crystal_reward" and U.state == "recharge":
                        save["crystals"] += 25
                        U.crystal_ad_count += 1
                        U.rmsg = "25 NOVA CRYSTALS ADDED!"
                        U.rmsg_ok = True
                        U.rmsg_t = 240
                        write_save()
                        sfx("crystal")
                else:
                    U.ad_msg = "AD WAS NOT COMPLETED - NO REWARD"
            elif ev.type == pygame.QUIT:
                U.running = False
            elif ev.type == pygame.KEYDOWN:
                key_down(ev.key)
                char_input(ev)
            elif ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                touch_event(ev)
            elif ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                if not ANDROID:
                    mouse_event(ev)
        st = U.state
        set_engine(st == "playing")
        if U.msg_t > 0:
            U.msg_t -= 1
        if st == "playing":
            r = game.update()
            if r == "dead":
                on_dead()
            elif r == "clear":
                on_level_clear()
            game.draw()
        elif st == "pause":
            game.draw()
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            canvas.blit(ov, (0, 0))
            text("PAUSED", F_XL, GOLD, WIDTH // 2, 240, center=True)
            text("P / ESC / ENTER: RESUME", F_M, WHITE, WIDTH // 2, 320, center=True)
            text("B: SHOP    O: SETTINGS    M: MAIN MENU (SAVES)", F_M, WHITE, WIDTH // 2, 360, center=True)
            if ANDROID:
                draw_pause_touch_buttons()
        elif st == "clear":
            space.update(2.0)
            draw_center_screen("LEVEL %d CLEAR!" % game.level, GREEN,
                               [("COINS EARNED: %d" % game.earned, GOLD),
                                ("TOTAL COINS: %d" % save["coins"], GOLD_LIGHT),
                                ("SCORE: %d" % game.score, WHITE),
                                ("NEXT: LEVEL %d%s" % (game.level + 1, "  (BOSS!)" if (game.level + 1) % BOSS_EVERY == 0 else ""), CYAN),
                                ("PROGRESS SAVED", GRAY_L)],
                               "ENTER: NEXT LEVEL     B: SHOP     M: MENU")
            draw_ad_actions()
        elif st == "dead":
            space.update(1.0)
            draw_center_screen("GAME OVER", RED_LIGHT,
                               [("YOU REACHED LEVEL %d" % game.level, WHITE),
                                ("SCORE: %d" % game.score, WHITE),
                                ("HIGH SCORE: %d" % save["high_score"], GOLD),
                                ("YOUR COINS AND UPGRADES ARE KEPT", CYAN)],
                               "R / ENTER: RETRY THIS LEVEL     B: SHOP     M: MENU")
            draw_ad_actions()
        elif st == "win":
            space.update(1.0)
            draw_center_screen("YOU WIN!", GOLD,
                               [("ALL %d LEVELS COMPLETED" % MAX_LEVEL, CYAN),
                                ("THE GALAXY IS SAFE", WHITE),
                                ("FINAL SCORE: %d" % game.score, GOLD_LIGHT)],
                               "ENTER: MAIN MENU")
            draw_ad_actions()
        elif st == "menu":
            space.update(1.0)
            draw_menu()
        elif st == "settings":
            space.update(1.0)
            draw_settings()
        elif st == "shop":
            space.update(1.0)
            draw_shop()
        elif st == "recharge":
            space.update(1.0)
            draw_recharge()
        elif st == "pass":
            space.update(1.0)
            draw_pass()
        elif st == "daily":
            space.update(1.0)
            draw_daily()
        if U.rmsg_t > 0:
            U.rmsg_t -= 1
        if U.dmsg_t > 0:
            U.dmsg_t -= 1
        sx = sy = 0
        if st == "playing" and save["shake"] and game.shake > 0.5:
            sx = int(random.uniform(-1, 1) * game.shake * 0.6)
            sy = int(random.uniform(-1, 1) * game.shake * 0.6)
        if ANDROID and st == "playing":
            draw_touch_buttons()
        post_fx(canvas)
        window.fill((0, 0, 0))
        if ANDROID:
            # تمديد اللوحة المنطقية إلى كامل شاشة الهاتف بدلاً من ترك أشرطة سوداء.
            ww, wh = window.get_size()
            full_frame = pygame.transform.scale(canvas, (ww, wh))
            window.blit(full_frame, (0, 0))
        else:
            window.blit(canvas, (sx, sy))
        pygame.display.flip()
    write_save()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
# ===== نهاية الملف: إن وصلت لهذا السطر فالكود كامل =====
