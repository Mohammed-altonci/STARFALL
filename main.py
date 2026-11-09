# -*- coding: utf-8 -*-
"""
STARFALL - ANDROID DIAGNOSTIC BOOTLOADER
"""

import os
import sys
import time
import json
import traceback

GAME_MODULE = "starfall_game"
ANDROID = "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")
FORCE_MODE = os.environ.get("STARFALL_FORCE_MODE")

# خط بكسلات مدمج
_FONT_HEX = (
    "000000000000005F00000007000700147F147F14242A7F2A12231308646236495620500008070300001C2241000041221C002A1C7F1C2A08083E080800807030000808080808000060600020100804023E5149453E00427F40007249494946"
    "2141494D331814127F1027454545393C4A49493141211109073649494936464949291E0000140000004034000000081422411414141414004122140802015909063E415D594E7C1211127C7F494949363E414141227F4141413E7F49494941"
    "7F090909013E414151737F0808087F00417F41002040413F017F081422417F404040407F021C027F7F0408107F3E4141413E7F090909063E4151215E7F09192946264949493203017F01033F4040403F1F2040201F3F4038403F6314081463"
    "03047804036159494D43007F4141410204081020004141417F04020102044040404040000307080020545478407F284444383844444428384444287F385454541800087E090218A4A49C787F0804047800447D40002040403D007F10284400"
    "00417F40007C047804787C080404783844444438FC1824241818242418FC7C08040408485454542404043F44243C4040207C1C2040201C3C4030403C44281028444C9090907C4464544C440008364100000077000000413608000201020402"
)

GLYPHS = {}

for _i in range(95):
    _h = _FONT_HEX[_i * 10:(_i + 1) * 10]
    GLYPHS[32 + _i] = [
        int(_h[j:j + 2], 16)
        for j in range(0, 10, 2)
    ]


def _base_dir():
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except Exception:
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()


BASE = _base_dir()
STATE_FILE = os.path.join(BASE, "starfall_boot.json")
FAULT_FILE = os.path.join(BASE, "starfall_fault.log")

_state = {}
T0 = time.time()
_fault_fh = None


def read_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_state(**kw):
    _state.update(kw)

    try:
        tmp = STATE_FILE + ".tmp"

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_state, f)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, STATE_FILE)

    except Exception:
        pass


def stage(name):
    write_state(
        stage=str(name)[:120],
        t=round(time.time() - T0, 1)
    )


def toast(msg):
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def _show():
            Toast = autoclass("android.widget.Toast")
            Activity = autoclass(
                "org.kivy.android.PythonActivity"
            ).mActivity

            Toast.makeText(
                Activity,
                str(msg)[:200],
                1
            ).show()

        _show()

    except Exception:
        pass


# --------------------------------------------------
# رسم النصوص
# --------------------------------------------------

def draw_text(surf, x, y, s, color, scale):
    for ch in str(s):
        g = GLYPHS.get(ord(ch), GLYPHS[63])

        for cx in range(5):
            col = g[cx]

            if col:
                for ry in range(8):
                    if (col >> ry) & 1:
                        surf.fill(
                            color,
                            (
                                x + cx * scale,
                                y + ry * scale,
                                scale,
                                scale
                            )
                        )

        x += 6 * scale


def wrap_lines(lines, width_chars):
    out = []

    for ln in lines:
        ln = str(ln).replace("\t", "    ")

        if not ln:
            out.append("")
            continue

        while ln:
            out.append(ln[:width_chars])
            ln = ln[width_chars:]

    return out


# --------------------------------------------------
# شاشة تقرير الأخطاء
# --------------------------------------------------

def show_report(pg, title, lines, flip):
    try:
        if "diag" in COMPAT:
            scr = COMPAT["diag"]()
        else:
            scr = pg.display.get_surface()

            if scr is None:
                scr = pg.display.set_mode((0, 0))

    except Exception:
        return

    w, h = scr.get_size()

    scale = max(1, w // 384)

    cw = 6 * scale
    chh = 9 * scale

    cols = max(10, w // cw - 2)
    rows = max(5, h // chh - 4)

    body = wrap_lines(lines, cols)

    pages = [
        body[i:i + rows]
        for i in range(0, max(1, len(body)), rows)
    ] or [[]]

    for pi, page in enumerate(pages):

        scr.fill((60, 0, 10))

        draw_text(
            scr,
            cw,
            chh // 2,
            title,
            (255, 220, 90),
            scale
        )

        for li, ln in enumerate(page):
            draw_text(
                scr,
                cw,
                chh * 2 + li * chh,
                ln,
                (255, 255, 255),
                scale
            )

        draw_text(
            scr,
            cw,
            int(h - chh * 1.5),
            "TAP = NEXT (%d/%d)" % (pi + 1, len(pages)),
            (120, 230, 255),
            scale
        )

        try:
            flip()
        except Exception:
            return

        t_end = time.time() + 600

        while time.time() < t_end:

            try:
                events = pg.event.get()
            except Exception:
                return

            for ev in events:

                if ev.type == pg.QUIT:
                    return

                if ev.type in (
                    pg.KEYDOWN,
                    pg.MOUSEBUTTONDOWN,
                    pg.FINGERDOWN
                ):
                    break
            else:
                pg.time.wait(50)
                continue

            break


# --------------------------------------------------
# توافق الشاشة في الوضع الآمن
# --------------------------------------------------

COMPAT = {}


def install_compat_display(pg):

    real_set_mode = pg.display.set_mode
    real_flip = pg.display.flip
    real_get = pg.event.get

    def set_mode(size=(0, 0), flags=0, *a, **k):

        if not size or size == (0, 0):
            size = (900, 700)

        try:
            real = real_set_mode(
                (0, 0),
                pg.FULLSCREEN
            )

        except Exception:
            real = real_set_mode(
                size,
                pg.FULLSCREEN
            )

        virt = pg.Surface(
            (int(size[0]), int(size[1]))
        )

        COMPAT.update(
            real=real,
            virt=virt,
            flip=real_flip
        )

        return virt

    def geometry():

        real = COMPAT["real"]
        virt = COMPAT["virt"]

        rw, rh = real.get_size()
        vw, vh = virt.get_size()

        sc = min(
            rw / float(vw),
            rh / float(vh)
        )

        ox = (rw - vw * sc) / 2.0
        oy = (rh - vh * sc) / 2.0

        return rw, rh, vw, vh, sc, ox, oy

    def flip():

        if "real" not in COMPAT:
            return real_flip()

        rw, rh, vw, vh, sc, ox, oy = geometry()

        real = COMPAT["real"]

        real.fill((0, 0, 0))

        scaled = pg.transform.scale(
            COMPAT["virt"],
            (
                max(1, int(vw * sc)),
                max(1, int(vh * sc))
            )
        )

        real.blit(
            scaled,
            (int(ox), int(oy))
        )

        real_flip()

    def update(*a, **k):
        return flip()

    def get(*a, **k):

        evs = real_get(*a, **k)

        if "real" not in COMPAT:
            return evs

        out = []

        rw, rh, vw, vh, sc, ox, oy = geometry()

        for e in evs:

            if e.type in (
                pg.FINGERDOWN,
                pg.FINGERUP,
                pg.FINGERMOTION
            ):

                d = dict(e.dict)

                d["x"] = (
                    e.x * rw - ox
                ) / (vw * sc)

                d["y"] = (
                    e.y * rh - oy
                ) / (vh * sc)

                if "dx" in d:
                    d["dx"] = (
                        e.dx * rw
                    ) / (vw * sc)

                    d["dy"] = (
                        e.dy * rh
                    ) / (vh * sc)

                e = pg.event.Event(e.type, d)

            elif e.type in (
                pg.MOUSEBUTTONDOWN,
                pg.MOUSEBUTTONUP,
                pg.MOUSEMOTION
            ):

                d = dict(e.dict)

                if "pos" in d:
                    px, py = d["pos"]

                    d["pos"] = (
                        (px - ox) / (vw * sc),
                        (py - oy) / (vh * sc)
                    )

                if "rel" in d:
                    rx, ry = d["rel"]

                    d["rel"] = (
                        rx / (vw * sc),
                        ry / (vh * sc)
                    )

                e = pg.event.Event(e.type, d)

            out.append(e)

        return out

    def diag_screen():

        if "diag_surf" not in COMPAT:

            COMPAT["diag_surf"] = real_set_mode(
                (0, 0),
                pg.FULLSCREEN
            )

        return COMPAT["diag_surf"]

    COMPAT["diag"] = diag_screen

    pg.display.set_mode = set_mode
    pg.display.flip = flip
    pg.display.update = update
    pg.event.get = get

    return real_flip


# --------------------------------------------------
# التشغيل الرئيسي
# --------------------------------------------------

def main():

    global T0
    global _fault_fh

    T0 = time.time()

    prev = read_state()

    crashed = (
        bool(prev)
        and not prev.get("ok", True)
    )

    mode = prev.get("mode", "normal")

    if crashed:
        mode = {
            "normal": "safe",
            "safe": "minimal"
        }.get(mode, "minimal")

    if FORCE_MODE in ("normal", "safe", "minimal"):
        mode = FORCE_MODE

    prev_fault = ""

    try:
        with open(
            FAULT_FILE,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:
            prev_fault = f.read()[-1500:]

    except Exception:
        pass

    write_state(
        mode=mode,
        ok=False,
        stage="boot",
        err="",
        launches=int(prev.get("launches", 0)) + 1
    )

    # تسجيل أخطاء الانهيار الأصلي إن أمكن
    try:
        import faulthandler

        _fault_fh = open(FAULT_FILE, "w")

        faulthandler.enable(
            file=_fault_fh,
            all_threads=True
        )

    except Exception:
        pass

    # --------------------------------------------------
    # استيراد Pygame
    # --------------------------------------------------

    stage("import pygame")

    try:
        import pygame as pg

    except BaseException:

        tb = traceback.format_exc()

        write_state(
            ok=False,
            err=tb[-2500:],
            stage="import pygame FAILED"
        )

        toast(
            "PYGAME IMPORT FAILED: "
            + tb.strip().splitlines()[-1]
        )

        raise

    real_flip = pg.display.flip

    # --------------------------------------------------
    # تفعيل الوضع الآمن
    # --------------------------------------------------

    if mode in ("safe", "minimal"):

        stage("install compat display")

        try:
            real_flip = install_compat_display(pg)

        except BaseException:

            tb = traceback.format_exc()

            write_state(
                ok=False,
                err=tb[-2500:],
                stage="compat display FAILED"
            )

            raise

    # --------------------------------------------------
    # عرض تقرير الانهيار السابق
    # --------------------------------------------------

    if crashed:

        lines = [
            "PREVIOUS LAUNCH DID NOT FINISH.",
            "LAST STAGE: %s (%s s)" % (
                prev.get("stage"),
                prev.get("t")
            ),
            "NOW RUNNING MODE: " + mode.upper(),
            ""
        ]

        if prev.get("err"):
            lines += (
                ["PYTHON ERROR:"]
                + prev["err"].splitlines()
            )

        if prev_fault.strip():
            lines += (
                ["", "NATIVE FAULT LOG:"]
                + prev_fault.splitlines()
            )

        try:
            pg.init()

            show_report(
                pg,
                "STARFALL DIAGNOSTIC - SCREENSHOT THIS",
                lines,
                real_flip
            )

        except BaseException:
            pass

    # --------------------------------------------------
    # استيراد ملف اللعبة الأصلي
    # --------------------------------------------------

    game_dir = (
        os.path.dirname(os.path.abspath(__file__))
        if "__file__" in globals()
        else os.getcwd()
    )

    sys.path.insert(0, game_dir)

    stage("import game module")

    try:

        G = __import__(GAME_MODULE)

    except BaseException:

        tb = traceback.format_exc()

        write_state(
            ok=False,
            err=tb[-2500:],
            stage="game import FAILED"
        )

        try:
            pg.init()

            show_report(
                pg,
                "ERROR WHILE LOADING GAME - SCREENSHOT THIS",
                tb.splitlines(),
                real_flip
            )

        except BaseException:
            pass

        sys.exit(1)

    # --------------------------------------------------
    # إعدادات الوضع الآمن
    # --------------------------------------------------

    if mode in ("safe", "minimal"):

        try:
            G.save["bloom"] = False
            G.save["scan"] = False

        except Exception:
            pass

    if mode == "minimal":

        try:
            G.SOUND_ENABLED = False

        except Exception:
            pass

    # --------------------------------------------------
    # مراقبة مراحل تحميل اللعبة
    # --------------------------------------------------

    orig_loading = getattr(
        G,
        "show_loading",
        None
    )

    if orig_loading:

        def loading(*a, **k):

            stage(
                "loading: "
                + (str(a[0]) if a else "")
            )

            return orig_loading(*a, **k)

        G.show_loading = loading

    # --------------------------------------------------
    # مراقبة أول إطار من اللعبة
    # --------------------------------------------------

    orig_fx = getattr(
        G,
        "post_fx",
        None
    )

    banner = {
        "n": 420 if (
            crashed or mode != "normal"
        ) else 0
    }

    ready = {"v": False}

    if orig_fx:

        def post_fx(surf):

            if not ready["v"]:

                ready["v"] = True

                write_state(
                    ok=True,
                    stage="running (first frame OK)"
                )

            orig_fx(surf)

            if banner["n"] > 0:

                banner["n"] -= 1

                draw_text(
                    surf,
                    6,
                    6,
                    "MODE: " + mode.upper()
                    + (
                        " (AFTER CRASH)"
                        if crashed else ""
                    ),
                    (255, 220, 90),
                    2
                )

        G.post_fx = post_fx

    # --------------------------------------------------
    # تشغيل اللعبة
    # --------------------------------------------------

    stage("game main()")

    try:

        G.main()

        write_state(
            ok=True,
            stage="clean exit"
        )

    except SystemExit:

        write_state(
            ok=True,
            stage="clean exit"
        )

        raise

    except BaseException:

        tb = traceback.format_exc()

        write_state(
            ok=False,
            err=tb[-2500:],
            stage=_state.get("stage", "")
            + " | EXCEPTION"
        )

        try:

            pg.init()

            show_report(
                pg,
                "GAME CRASHED - SCREENSHOT THIS",
                tb.splitlines(),
                real_flip
            )

        except BaseException:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
