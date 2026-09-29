#!/usr/bin/env bash
#
# Снимает дашборды в PNG для README. Запускать НА СЕРВЕРЕ.
#
# ---------------------------------------------------------------------------
# ПОЧЕМУ ЭТО СКРИПТ, А НЕ ПОСТОЯННАЯ СЛУЖБА
# ---------------------------------------------------------------------------
# Grafana не умеет рендерить картинки сама: для этого нужен отдельный сервис
# с браузером внутри (grafana-image-renderer, ~450 МБ и полноценный Chromium).
# Держать его поднятым круглосуточно ради двух кадров в README — плата
# памятью и поверхностью атаки за то, чем пользуются раз в месяц. Поэтому
# рендерер поднимается на время съёмки и убирается сразу после.
#
# ---------------------------------------------------------------------------
# ОКНО ВРЕМЕНИ
# ---------------------------------------------------------------------------
# По умолчанию берётся последний час. Если в окно попадает момент, когда у
# рядов сменились метки (переезд, переименование instance), Grafana честно
# покажет и старый ряд, и новый: в легенде задвоятся имена, а панель состояний
# развалится на два блока. Это не поломка данных, но кадр испорчен — возьмите
# окно целиком после такого события через FROM.
#
# Использование:
#   ./render-dashboards.sh [FROM]      FROM — как в Grafana, например now-6h
#
set -euo pipefail

FROM="${1:-now-1h}"
# Стек катится через deploy-kit, поэтому compose-файл лежит в текущем релизе,
# а .env — рядом с каталогом релизов и переживает выкатки.
ROOT=/opt/samoylove-metrics
STACK="$ROOT/current"
ENV_FILE="$ROOT/.env"
OUT=/tmp
TAG=3.12.9
NET=samoylove-metrics_default
RENDERER=samoylove-renderer-tmp
OVERRIDE="$STACK/docker-compose.override.yml"

cleanup() {
  echo "Убираю рендерер..."
  sudo docker rm -f "$RENDERER" >/dev/null 2>&1 || true
  sudo rm -f "$OVERRIDE"
  (cd "$STACK" && sudo docker compose up -d grafana >/dev/null)
}
trap cleanup EXIT

# Токен одноразовый и живёт только в памяти этого запуска: Grafana отказывается
# стартовать со значением по умолчанию, и это правильно — рендерер отдаёт
# картинку любому, кто знает адрес и токен.
TOKEN=$(openssl rand -hex 24)

echo "Поднимаю рендерер..."
sudo docker rm -f "$RENDERER" >/dev/null 2>&1 || true
sudo docker run -d --name "$RENDERER" --network "$NET" \
  -e ENABLE_METRICS=false -e AUTH_TOKEN="$TOKEN" \
  -e RENDERING_VIEWPORT_MAX_HEIGHT=8000 \
  "grafana/grafana-image-renderer:$TAG" >/dev/null

sudo tee "$OVERRIDE" >/dev/null <<YML
# Временный файл, создаётся docs/render-dashboards.sh и удаляется им же.
services:
  grafana:
    environment:
      GF_RENDERING_SERVER_URL: http://$RENDERER:8081/render
      GF_RENDERING_CALLBACK_URL: http://samoylove-grafana:3000/
      GF_RENDERING_RENDERER_TOKEN: $TOKEN
YML

(cd "$STACK" && sudo docker compose up -d grafana >/dev/null)
sleep 15

# Пароль администратора читается из .env стека во временную копию с правами
# 600 и стирается shred'ом: в /tmp мира и пса он не должен полежать даже
# минуту.
ENVC=$(mktemp)
chmod 600 "$ENVC"
sudo cat "$ENV_FILE" > "$ENVC"
set -a; . "$ENVC"; set +a
shred -u "$ENVC"

# Высота задаётся вручную: рендерер снимает ровно тот кусок страницы, который
# помещается в окно, а не «сколько получится». Число — из максимальной
# координаты панелей в JSON: строк сетки * 38 + запас на шапку.
shot() {
  local uid=$1 out=$2 height=$3
  printf '%-22s ' "$uid"
  curl -sS -u "$GF_SECURITY_ADMIN_USER:$GF_SECURITY_ADMIN_PASSWORD" \
    -o "$OUT/$out" -w 'HTTP %{http_code}, %{size_download} байт\n' --max-time 240 \
    "http://127.0.0.1:3002/render/d/$uid/x?orgId=1&from=$FROM&to=now&width=1400&height=$height&scale=2&kiosk&theme=dark"
}

# Высоты пересчитываются при добавлении панелей — иначе кадр молча обрежется
# по нижнему краю, и раздела на нём просто не окажется. Считается так:
#   for f in grafana/dashboards/*.json; do python -c "import json,sys;d=json.load(
#     open(sys.argv[1],encoding='utf-8'));print(d['uid'], max(p['gridPos']['y']+
#     p['gridPos']['h'] for p in d['panels'])*38+90)" "$f"; done
shot samoylove-ops        dashboard-ops.png 1230
shot samoylove-overview   dashboard-overview.png 1876
shot samoylove-chillhub   dashboard-chillhub.png 3054
shot samoylove-snakes     dashboard-snakes.png 2256
shot samoylove-die        dashboard-die.png 926
shot samoylove-metro      dashboard-metro.png 774
shot samoylove-site       dashboard-samoylove.png 1116
shot samoylove-status     dashboard-status.png 2294

echo
echo "Готово. Забрать к себе и положить в docs/ репозитория:"
echo "  scp oracle:$OUT/dashboard-ops.png oracle:$OUT/dashboard-overview.png oracle:$OUT/dashboard-chillhub.png oracle:$OUT/dashboard-snakes.png oracle:$OUT/dashboard-die.png oracle:$OUT/dashboard-metro.png oracle:$OUT/dashboard-samoylove.png oracle:$OUT/dashboard-status.png docs/"
