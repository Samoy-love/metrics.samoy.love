#!/usr/bin/env python3
"""Сверка тревог с дашбордами и сборка docs/runbook.md.

    python3 ci/alerts.py                 проверить (так зовёт CI)
    python3 ci/alerts.py --write-runbook пересобрать docs/runbook.md из rules.yml

ЗАЧЕМ. Тревога в Telegram ведёт ссылкой на панель (__dashboardUid__ и
__panelId__) и на раздел runbook. Обе ссылки ломаются молча: панель
переименовали или убрали при перестройке дашборда — сообщение ведёт на пустую
страницу; правило добавили, а раздел runbook нет — «что делать» ведёт в
никуда. Grafana об этом не скажет ни при старте, ни при срабатывании. Поэтому
здесь проверяется ровно это, плюс то, без чего правило не попадёт на светофор
«Обзора»: область (area) и уровень (severity).

Для дашбордов — то, что делает их читаемыми оператором: у каждой панели есть
описание, номера панелей не повторяются, строки не шире сетки.
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "grafana", "provisioning", "alerting", "rules.yml")
DASHBOARDS = os.path.join(ROOT, "grafana", "dashboards")
RUNBOOK = os.path.join(ROOT, "docs", "runbook.md")
RUNBOOK_URL = "https://github.com/samoy-love/metrics.samoy.love/blob/main/docs/runbook.md#"
PUBLIC = "https://metrics.samoy.love"

AREAS = {"ci": "CI", "server": "Сервер", "cs2": "Пристрелка", "sites": "Сайты и проекты", "monitoring": "Мониторинг"}
SEVERITIES = {"critical": "авария", "warning": "предупреждение", "info": "для сведения"}


def load_dashboards():
    """uid -> (заголовок, {id панели: панель})."""
    out = {}
    for path in sorted(glob.glob(os.path.join(DASHBOARDS, "*.json"))):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        panels = {}

        def walk(ps):
            for p in ps:
                if p.get("id") is not None:
                    panels.setdefault(str(p["id"]), []).append(p)
                if p.get("type") == "row":
                    walk(p.get("panels", []))
        walk(d.get("panels", []))
        out[d["uid"]] = (d.get("title", ""), panels, os.path.basename(path))
    return out


def load_rules():
    with open(RULES, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    for g in d["groups"]:
        for r in g["rules"]:
            yield g["name"], r


def expr_of(rule):
    for q in rule["data"]:
        if q.get("datasourceUid") != "__expr__":
            return " ".join(str(q["model"].get("expr", "")).split())
    return ""


def check():
    errors = []
    dashboards = load_dashboards()

    uids = {}
    for uid, (title, panels, name) in dashboards.items():
        uids.setdefault(uid, []).append(name)
        for pid, ps in panels.items():
            if len(ps) > 1:
                errors.append(f"{name}: панель {pid} встречается {len(ps)} раза — ссылка тревоги станет неоднозначной")
            p = ps[0]
            if p.get("type") in ("row",):
                continue
            if not str(p.get("description", "")).strip():
                errors.append(f"{name}: у панели {pid} «{p.get('title')}» нет описания — оператор не узнает, что на ней")
            g = p.get("gridPos") or {}
            if g and g.get("x", 0) + g.get("w", 0) > 24:
                errors.append(f"{name}: панель {pid} выходит за сетку в 24 колонки")
    for uid, names in uids.items():
        if len(names) > 1:
            errors.append(f"uid {uid} у нескольких дашбордов: {names}")

    seen = set()
    for group, r in load_rules():
        where = f"{group}/{r['uid']} «{r['title']}»"
        if r["uid"] in seen:
            errors.append(f"{where}: uid повторяется")
        seen.add(r["uid"])
        labels = r.get("labels") or {}
        ann = r.get("annotations") or {}
        if labels.get("severity") not in SEVERITIES:
            errors.append(f"{where}: severity {labels.get('severity')!r} — маршрутизация идёт по нему, без него правило не будит")
        if labels.get("area") not in AREAS:
            errors.append(f"{where}: area {labels.get('area')!r} — без области правило не попадёт ни на один светофор")
        if not str(ann.get("summary", "")).strip():
            errors.append(f"{where}: нет summary — в чате будет только имя")
        if ann.get("runbook_url") != RUNBOOK_URL + r["uid"]:
            errors.append(f"{where}: runbook_url должен быть {RUNBOOK_URL + r['uid']}")
        d_uid, pid = ann.get("__dashboardUid__"), ann.get("__panelId__")
        if not d_uid or not pid:
            errors.append(f"{where}: нет __dashboardUid__/__panelId__ — ссылка «график» в сообщении не появится")
        elif d_uid not in dashboards:
            errors.append(f"{where}: нет дашборда {d_uid}")
        elif str(pid) not in dashboards[d_uid][1]:
            errors.append(f"{where}: на дашборде {d_uid} нет панели {pid}")

    if os.path.exists(RUNBOOK):
        with open(RUNBOOK, encoding="utf-8") as f:
            current = f.read()
        if current != runbook(dashboards):
            errors.append("docs/runbook.md разошёлся с rules.yml: python3 ci/alerts.py --write-runbook")
    else:
        errors.append("нет docs/runbook.md: python3 ci/alerts.py --write-runbook")
    return errors


def plain(text):
    """Шаблоны меток — словами: «{{ $labels.device }}» читается как ‹device›."""
    return re.sub(r"\{\{\s*\$labels\.(\w+)\s*\}\}", r"‹\1›", str(text or ""))


def runbook(dashboards):
    rules = list(load_rules())
    lines = [
        "# Тревоги: что значат и что делать",
        "",
        "Русский · собирается из [`grafana/provisioning/alerting/rules.yml`](../grafana/provisioning/alerting/rules.yml)",
        "командой `python3 ci/alerts.py --write-runbook`. Руками не править: CI сверяет файл с правилами.",
        "",
        "Каждая тревога в Telegram ведёт сюда ссылкой «что делать» и на свою панель — ссылкой «график».",
        "Уровни: **авария** — чинить сейчас, напоминание раз в 4 часа; **предупреждение** — раз в сутки;",
        "**для сведения** — не требует действий.",
        "",
    ]
    for area, name in AREAS.items():
        rs = [(g, r) for g, r in rules if r["labels"].get("area") == area]
        lines.append(f"- [{name}](#{area}-area) — {len(rs)}")
    lines.append("")
    for area, name in AREAS.items():
        rs = [(g, r) for g, r in rules if r["labels"].get("area") == area]
        if not rs:
            continue
        lines += [f'<a id="{area}-area"></a>', "", f"## {name}", ""]
        order = {"critical": 0, "warning": 1, "info": 2}
        for g, r in sorted(rs, key=lambda x: (order.get(x[1]["labels"]["severity"], 9), x[1]["title"])):
            a = r["annotations"]
            d_uid, pid = a.get("__dashboardUid__"), str(a.get("__panelId__"))
            dash = dashboards.get(d_uid)
            panel = dash[1].get(pid, [{}])[0].get("title", "?") if dash else "?"
            link = f"[{dash[0] if dash else d_uid} → {panel}]({PUBLIC}/d/{d_uid}?viewPanel={pid})"
            meta = [f"**{SEVERITIES[r['labels']['severity']]}**"]
            if a.get("threshold"):
                meta.append(f"порог: {a['threshold']}")
            meta.append(f"панель: {link}")
            lines += [f'<a id="{r["uid"]}"></a>', "", f"### {r['title']}", "", " · ".join(meta), "",
                      f"**Что случилось.** {plain(a.get('summary'))}", ""]
            if a.get("description"):
                lines += [f"**Что это значит и что делать.** {plain(a['description'])}", ""]
            lines += ["<details><summary>Условие</summary>", "", "```promql", expr_of(r), "```", "",
                      f"Держится: {r.get('for', '0m')} · группа `{g}` · uid `{r['uid']}`", "", "</details>", ""]
    return "\n".join(lines)


def main():
    if "--write-runbook" in sys.argv:
        os.makedirs(os.path.dirname(RUNBOOK), exist_ok=True)
        with open(RUNBOOK, "w", encoding="utf-8", newline="\n") as f:
            f.write(runbook(load_dashboards()))
        print("docs/runbook.md собран")
        return
    errors = check()
    for e in errors:
        print("::error::" + e)
    if errors:
        sys.exit(1)
    print("тревоги, панели и runbook сходятся")


main()
