# Тревоги: что значат и что делать

Русский · собирается из [`grafana/provisioning/alerting/rules.yml`](../grafana/provisioning/alerting/rules.yml)
командой `python3 ci/alerts.py --write-runbook`. Руками не править: CI сверяет файл с правилами.

Каждая тревога в Telegram ведёт сюда ссылкой «что делать» и на свою панель — ссылкой «график».
Уровни: **авария** — чинить сейчас, напоминание раз в 4 часа; **предупреждение** — раз в сутки;
**для сведения** — не требует действий.

- [CI](#ci-area) — 11
- [Сервер](#server-area) — 39
- [Пристрелка](#cs2-area) — 66
- [Сайты и проекты](#sites-area) — 39
- [Мониторинг](#monitoring-area) — 11

<a id="ci-area"></a>

## CI

<a id="ci-queue-stuck-linux"></a>

### CI: задание ждёт Linux-раннер дольше 10 минут

**предупреждение** · порог: дольше 10 мин, держится 5 мин · панель: [CI — раннеры, очередь, задания → Самое старое задание в очереди](https://metrics.samoy.love/d/samoylove-ci?viewPanel=17)

**Что случилось.** Задание в очереди на большие Linux-раннеры ждёт дольше 10 минут

**Что это значит и что делать.** Очередь на собственные Linux-раннеры копится: самое старое задание ждёт больше 10 минут. Число раннеров меняет ci-autoscaler: если на панели «Почему не поднимает новых» упор в память — очередь стоит из-за бюджета или хоста (см. «CI: раннерам не хватает памяти хоста»). Если упора нет, а раннеры есть, — они не берут работу: на хосте ci-autoscaler status и journalctl -u 'ci-runner-cycle@*'.

<details><summary>Условие</summary>

```promql
max(ci_job_queue_oldest_seconds{pool=~"home-linux|set-heavy"}) > 600
```

Держится: 5m · группа `infra-ci` · uid `ci-queue-stuck-linux`

</details>

<a id="ci-queue-stuck-windows"></a>

### CI: задание ждёт win-builder дольше 15 минут

**предупреждение** · порог: дольше 15 мин, держится 5 мин · панель: [CI — раннеры, очередь, задания → Самое старое задание в очереди](https://metrics.samoy.love/d/samoylove-ci?viewPanel=17)

**Что случилось.** Задание в очереди на win-builder ждёт дольше 15 минут

**Что это значит и что делать.** Задание на Windows-раннер ждёт больше 15 минут, а машине на загрузку хватает минуты. Значит, win-builder не поднялась или раннер на ней офлайн: journalctl -u win-builder-ondemand на хосте, состояние службы раннера в VM (Home Server CLAUDE.md, раздел про win-builder).

<details><summary>Условие</summary>

```promql
max(ci_job_queue_oldest_seconds{pool="home-windows"}) > 900
```

Держится: 5m · группа `infra-ci` · uid `ci-queue-stuck-windows`

</details>

<a id="ci-queue-stuck-light"></a>

### CI: задание ждёт лёгкий раннер дольше 5 минут

**предупреждение** · порог: дольше 5 мин, держится 5 мин · панель: [CI — раннеры, очередь, задания → Самое старое задание в очереди](https://metrics.samoy.love/d/samoylove-ci?viewPanel=17)

**Что случилось.** Задание в очереди на лёгкие раннеры ждёт дольше 5 минут

**Что это значит и что делать.** Очередь на лёгкие раннеры (метка light; сколько их, решает ci-autoscaler): линтеры, тесты на Node, снимки страниц и покрытие. Работы в таком задании секунды, поэтому пять минут ожидания значат, что лёгких не хватает или они не берут работу. Порог ниже, чем у больших, по той же причине.

<details><summary>Условие</summary>

```promql
max(ci_job_queue_oldest_seconds{pool=~"home-light|set-light"}) > 300
```

Держится: 5m · группа `infra-ci` · uid `ci-queue-stuck-light`

</details>

<a id="ci-autoscaler-actions-failing"></a>

### CI: контроллер не может поднять или погасить раннер

**предупреждение** · порог: не меньше 3 · панель: [CI — раннеры, очередь, задания → Действия контроллера](https://metrics.samoy.love/d/samoylove-ci?viewPanel=56)

**Что случилось.** Три и больше неудачных действий контроллера за 15 минут

**Что это значит и что делать.** За 15 минут три и больше действий ci-autoscaler не удались: не создаётся слот, не снимается регистрация через API GitHub, не стартует служба слота или адрес слота не входит в изоляцию (такой слот контроллер не запускает намеренно). Причина — в журнале: journalctl -u ci-autoscaler | grep '!'.

<details><summary>Условие</summary>

```promql
sum(increase(ci_autoscaler_actions_total{result="fail"}[15m])) >= 3
```

Держится: 0m · группа `infra-ci` · uid `ci-autoscaler-actions-failing`

</details>

<a id="ci-autoscaler-down"></a>

### CI: контроллер раннеров молчит

**предупреждение** · порог: держится 3 мин · панель: [CI — раннеры, очередь, задания → Контроллер раннеров](https://metrics.samoy.love/d/samoylove-ci?viewPanel=45)

**Что случилось.** Контроллер раннеров не отмечался больше двух минут

**Что это значит и что делать.** ci-autoscaler не закончил такт больше двух минут. Раннеры это переживут: цикл, не видящий свежего пульса контроллера, работает по-старому, класс по имени. Но под очередь новые не поднимутся, лишние не погаснут, а запаркованные слоты так и останутся стоять. На хосте: systemctl status ci-autoscaler, journalctl -u ci-autoscaler.

<details><summary>Условие</summary>

```promql
((time() - max(ci_autoscaler_timestamp_seconds)) > 120) or (absent(ci_autoscaler_timestamp_seconds) * 1e6)
```

Держится: 3m · группа `infra-ci` · uid `ci-autoscaler-down`

</details>

<a id="ci-linux-runners-missing"></a>

### CI: поднятые раннеры не видны в GitHub

**предупреждение** · порог: не меньше 2, держится 15 мин · панель: [CI — раннеры, очередь, задания → Идут и ждут — большие](https://metrics.samoy.love/d/samoylove-ci?viewPanel=19)

**Что случилось.** Контроллер поднял раннеры, а GitHub видит онлайн на два меньше

**Что это значит и что делать.** Контроллер ci-autoscaler считает минимум двух раннеров поднятыми (процесс раннера жив), а GitHub не видит их в онлайне уже 15 минут. Значит, раннеры не могут до него достучаться или регистрация не проходит, и задания стоят. На хосте: ci-autoscaler status, journalctl -u 'ci-runner-cycle@*'.

<details><summary>Условие</summary>

```promql
min_over_time(((sum(ci_autoscaler_slots{state=~"idle|busy"}) or vector(0)) - (sum(ci_runners{os!="windows",status="online"}) or vector(0)))[5m:30s]) >= 2
```

Держится: 15m · группа `infra-ci` · uid `ci-linux-runners-missing`

</details>

<a id="ci-autoscaler-memory-bound"></a>

### CI: раннерам не хватает памяти хоста

**предупреждение** · порог: держится 10 мин · панель: [CI — раннеры, очередь, задания → Почему не поднимает новых](https://metrics.samoy.love/d/samoylove-ci?viewPanel=54)

**Что случилось.** Контроллер упёрся в память, а задания ждут дольше 15 минут

**Что это значит и что делать.** Задание ждёт раннер больше 15 минут, и контроллер не поднимает новых из-за памяти. Причина budget — сумма потолков раннеров дошла до ci_mem_max в /etc/ci-autoscaler.toml на хосте: поднять бюджет, если хосту хватает. Причина host — память занята не CI (рендер, Windows-машины, прод): смотреть панель «Память инстансов» на панели железа.

<details><summary>Условие</summary>

```promql
(max(ci_autoscaler_blocked{reason=~"budget|host"}) == 1) and on() (max(ci_job_queue_oldest_seconds{pool=~"home-linux|home-light|set-heavy|set-light"}) > 900)
```

Держится: 10m · группа `infra-ci` · uid `ci-autoscaler-memory-bound`

</details>

<a id="ci-autoscaler-cpu-bound"></a>

### CI: раннерам не хватает ядер

**предупреждение** · порог: держится 10 мин · панель: [CI — раннеры, очередь, задания → Почему не поднимает новых](https://metrics.samoy.love/d/samoylove-ci?viewPanel=54)

**Что случилось.** Контроллер упёрся в набор ядер, а задания ждут дольше 15 минут

**Что это значит и что делать.** Задание ждёт раннер больше 15 минут, и контроллер не поднимает новый: общий набор ядер раннеров (cpu_pool) с учётом ожидаемого расхода уже занят. Если ядра набора на деле простаивают, ожидаемый расход завышен: смотреть ci_autoscaler_cpu_pool_cores (used, reserved, max) и cpu_pool_max в /etc/ci-autoscaler.toml на хосте. Если заняты, CI упирается в процессор, и новый раннер только растянул бы все задания.

<details><summary>Условие</summary>

```promql
(max(ci_autoscaler_blocked{reason="cpu_pool"}) == 1) and on() (max(ci_job_queue_oldest_seconds{pool=~"home-linux|home-light|set-heavy|set-light"}) > 900)
```

Держится: 10m · группа `infra-ci` · uid `ci-autoscaler-cpu-bound`

</details>

<a id="ci-queue-collector-stale"></a>

### CI: сборщик очереди GitHub молчит

**предупреждение** · порог: держится 10 мин · панель: [CI — раннеры, очередь, задания → Сборщик очереди](https://metrics.samoy.love/d/samoylove-ci?viewPanel=13)

**Что случилось.** Сборщик очереди заданий не обновлялся больше 10 минут

**Что это значит и что делать.** Сборщик очереди раннеров (ci-queue-collect на хосте) не пишет данные или не может опросить GitHub. Пока это так, тревоги об очереди молчат. На хосте: systemctl status ci-queue-collect.timer, journalctl -u ci-queue-collect.

<details><summary>Условие</summary>

```promql
(time() - max(ci_queue_collect_timestamp_seconds)) > 600 or max(ci_queue_collect_ok) == 0
```

Держится: 10m · группа `infra-ci` · uid `ci-queue-collector-stale`

</details>

<a id="ci-orphan-docker"></a>

### CI: сирота docker в раннере без задания

**предупреждение** · порог: больше 1,5 ГиБ, держится 20 мин · панель: [CI — раннеры, очередь, задания → Память раннеров без задания (сироты docker)](https://metrics.samoy.love/d/samoylove-ci?viewPanel=70)

**Что случилось.** Раннер ‹name› без задания держит больше 1,5 ГиБ памяти

**Что это значит и что делать.** Docker-сборка упавшего прогона осталась жить после того, как GitHub закрыл задание (26.09.2026 так восемь часов крутился devkita64). Раннер держит память хоста, контроллер не поднимает новых, хост уходит в давление памяти. Найти: ps внутри раннера; убить через cgroup.kill docker-*.scope, затем перезапустить раннер.

<details><summary>Условие</summary>

```promql
(max by (name) (incus_memory_MemTotal_bytes{name=~"ci-(runner|light).*"} - incus_memory_MemAvailable_bytes{name=~"ci-(runner|light).*"})) * on(name) group_left() (max by (name) (label_replace(ci_autoscaler_slot{state="idle"}, "name", "$1", "slot", "(.*)")) == 1) > 1.5 * 1024^3
```

Держится: 20m · группа `infra-ci` · uid `ci-orphan-docker`

</details>

<a id="ci-scaleset-listener-down"></a>

### CI: слушатель Runner Scale Set отключён

**предупреждение** · порог: держится 5 мин · панель: [CI — раннеры, очередь, задания → Слушатель наборов](https://metrics.samoy.love/d/samoylove-ci?viewPanel=58)

**Что случилось.** Слушатель наборов раннеров не на связи с GitHub

**Что это значит и что делать.** Слушатель ci-scaleset не держит сессию набора Runner Scale Set или давно не получал ответа. Задания с runs-on home-heavy или home-light при этом назначаются набору только после переподключения, а контроллер берёт спрос у сборщика очереди (раз в 30 с). После падения сессия занята до минуты — это штатно; дольше — journalctl -u ci-scaleset на хосте.

<details><summary>Условие</summary>

```promql
(min(ci_scaleset_session_up) == 0) or ((time() - min(ci_scaleset_last_update_timestamp_seconds)) > 180) or (absent(ci_scaleset_session_up) * 1e6)
```

Держится: 5m · группа `infra-ci` · uid `ci-scaleset-listener-down`

</details>

<a id="server-area"></a>

## Сервер

<a id="hw-zpool-errors"></a>

### Сервер: ZFS видит ошибки дисков

**авария** · порог: больше 0, держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Ошибки ZFS](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=22)

**Что случилось.** ZFS сообщает об ошибках чтения, записи или контрольных сумм

**Что это значит и что делать.** ECC на этой машине нет, контрольные суммы ZFS — единственный сигнал о порче данных. zpool status -v, затем zpool scrub и SMART обоих дисков.

<details><summary>Условие</summary>

```promql
zpool_device_errors_total > 0
```

Держится: 5m · группа `infra-hardware` · uid `hw-zpool-errors`

</details>

<a id="infra-disk-space-low"></a>

### Сервер: в контейнере web кончается диск

**авария** · порог: меньше 10%, держится 15 мин · панель: [Сайты samoy.love — сводка → Свободно на дисках](https://metrics.samoy.love/d/samoylove-overview?viewPanel=23)

**Что случилось.** На корне контейнера web свободно меньше 10%

**Что это значит и что делать.** В web живут nginx, Prometheus, Grafana и статика всех сайтов. Кончится место — перестанут писаться журналы и метрики, выкатка не распакуется. Смотреть, кто вырос: du -xh / в web, чаще всего журналы docker или TSDB.

<details><summary>Условие</summary>

```promql
node_filesystem_avail_bytes{mountpoint="/",job!="node-containers"} / node_filesystem_size_bytes{mountpoint="/",job!="node-containers"} < 0.10
```

Держится: 15m · группа `infra-host` · uid `infra-disk-space-low`

</details>

<a id="hw-smart-unhealthy"></a>

### Сервер: диск сообщает о поломке

**авария** · панель: [Сервер — хост, диски, контейнеры, машины рендера → SMART самооценка](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=47)

**Что случилось.** SMART самооценка диска — FAILED

**Что это значит и что делать.** SMART диска (метка device, model) сообщил, что он неисправен. Пул — зеркало из двух NVMe, второй держит данные, но замену надо планировать сразу: корень хоста лежит только на Kingston без зеркала.

<details><summary>Условие</summary>

```promql
smart_device_healthy{job="node-host"} == 0
```

Держится: 0m · группа `infra-hardware` · uid `hw-smart-unhealthy`

</details>

<a id="hw-incus-autostart-not-running"></a>

### Сервер: инстанс с автозапуском лежит

**авария** · порог: держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Инстансов не запущено](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=82)

**Что случилось.** Инстанс ‹name› должен работать, но не RUNNING

**Что это значит и что делать.** Всё, что живёт в этом инстансе, недоступно целиком (cs2 — сайт Пристрелки, web — все сайты, cs2-render — рендер). incus info и incus start на хосте, затем журнал инстанса.

<details><summary>Условие</summary>

```promql
(incus_instance_running{autostart="true"} == 0) or (incus_instance_list_ok == 0)
```

Держится: 5m · группа `infra-hardware` · uid `hw-incus-autostart-not-running`

</details>

<a id="hw-cpu-fan-stopped"></a>

### Сервер: кулер процессора стоит

**авария** · порог: держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Обороты вентиляторов](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=12)

**Что случилось.** Кулер процессора показывает 0 об/мин

**Что это значит и что делать.** Без кулера процессор перегреется за минуты и хост выключится. Проверить разъём и сам вентилятор; если датчик пропал после перезагрузки — модуль nct6775 не загрузился.

<details><summary>Условие</summary>

```promql
node_hwmon_fan_rpm{sensor="fan2"} == 0
```

Держится: 5m · группа `infra-hardware` · uid `hw-cpu-fan-stopped`

</details>

<a id="hw-cpu-temp-high"></a>

### Сервер: процессор перегрет

**авария** · порог: больше 97 °C, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Процессор, iGPU и плата](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=9)

**Что случилось.** Процессор держит 94 °C и сбрасывает частоту ниже базовой, или выше 97 °C

**Что это значит и что делать.** Процессор 15 минут у предела 95 °C и при этом ниже базовой частоты 4,2 ГГц — охлаждение не справляется и отнимает производительность; или температура выше 97 °C — защита не удерживает предел. Штатный упор в 95 °C при нагрузке на полной частоте тревогой не считается. Проверить обороты кулера и пыль, график частоты — «Железо».

<details><summary>Условие</summary>

```promql
(min_over_time((node_hwmon_temp_celsius * on(chip) group_left(chip_name) node_hwmon_chip_names{chip_name="k10temp"})[15m:1m]) >= 94 and on() avg(avg_over_time(node_cpu_scaling_frequency_hertz{job="node-host"}[15m])) < 4.2e9) or max_over_time((node_hwmon_temp_celsius * on(chip) group_left(chip_name) node_hwmon_chip_names{chip_name="k10temp"})[5m:1m]) > 97
```

Держится: 10m · группа `infra-hardware` · uid `hw-cpu-temp-high`

</details>

<a id="hw-zpool-unhealthy"></a>

### Сервер: пул ZFS не в порядке

**авария** · порог: держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Пул tank](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=6)

**Что случилось.** Пул ZFS не ONLINE: зеркало деградировало

**Что это значит и что делать.** Данные живут на одном диске из двух: следующая поломка — потеря всего пула (демки, базы, контейнеры). zpool status -v на хосте, заменить диск.

<details><summary>Условие</summary>

```promql
zpool_health_state != 0
```

Держится: 5m · группа `infra-hardware` · uid `hw-zpool-unhealthy`

</details>

<a id="hw-zpool-capacity-critical"></a>

### Сервер: пул ZFS почти полон

**авария** · порог: больше 90%, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Кто занимает пул tank](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=52)

**Что случилось.** Пул ZFS заполнен больше чем на 90%

**Что это значит и что делать.** Пул заполнен больше чем на 90 %: до остановки записи на всех контейнерах недалеко. Освобождать место сейчас: старые снимки, кэш CI (/srv/ci-cache), тома игр.

<details><summary>Условие</summary>

```promql
zpool_capacity_ratio{job="node-host"} > 0.9
```

Держится: 10m · группа `infra-hardware` · uid `hw-zpool-capacity-critical`

</details>

<a id="hw-host-unit-down"></a>

### Сервер: служба инфраструктуры хоста не работает

**авария** · порог: держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Состояние юнитов](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=37)

**Что случилось.** Служба хоста ‹name› не active

**Что это значит и что делать.** Это службы изоляции сетей, шейпер, incus, fail2ban или автоскейлер CI: без них либо контейнеры видят лишнее, либо CI не поднимает раннеров. systemctl status и journalctl -u на хосте.

<details><summary>Условие</summary>

```promql
node_systemd_unit_state{instance="srv-host",state="active",name=~"(incus|web-isolation|ci-isolation|win-isolation|wan-shaper|fail2ban|ci-autoscaler|ci-scaleset)\\.service"} == 0
```

Держится: 10m · группа `infra-hardware` · uid `hw-host-unit-down`

</details>

<a id="hw-nvme-media-errors"></a>

### Сервер: у NVMe неисправимые ошибки носителя

**авария** · порог: больше 0, держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Ошибки носителя](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=21)

**Что случилось.** SMART сообщает о неисправимых ошибках носителя

**Что это значит и что делать.** Диск начал терять данные. Пока зеркало ZFS цело, данные спасает второй диск; пора планировать замену.

<details><summary>Условие</summary>

```promql
smart_nvme_media_errors_total > 0
```

Держится: 5m · группа `infra-hardware` · uid `hw-nvme-media-errors`

</details>

<a id="hw-host-global-oom"></a>

### Сервер: ядро убивало процессы от нехватки памяти

**авария** · порог: больше 0 · панель: [Сервер — хост, диски, контейнеры, машины рендера → Убито за нехваткой памяти](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=58)

**Что случилось.** Память кончилась на всём хосте, ядро убило процесс

**Что это значит и что делать.** Ядро убило процесс из-за нехватки памяти на всём хосте, а не внутри потолка инстанса: жертвой мог стать Postgres или ClickHouse прода. «Сервер: в контейнере убит процесс по памяти» такое не видит — он считает только счётчики инстансов. Считается по строкам ядра oom-kill с global_oom (node-textfile-collect): node_vmstat_oom_kill растёт и от потолка контейнера, и 22.09.2026 так ложно сработал на рендерере Grafana. 21.09.2026 так было дважды (steamwebhelper, процессы раннеров). Кто съел — «Сервер: хост задыхается без памяти» и панель «Память инстансов»; журнал — journalctl -k | grep global_oom.

<details><summary>Условие</summary>

```promql
increase(host_global_oom_kills_total{job="node-host"}[15m]) > 0
```

Держится: 0m · группа `infra-hardware` · uid `hw-host-global-oom`

</details>

<a id="hw-gpu-temp-high"></a>

### Сервер: GTX 1080 Ti перегрета

**предупреждение** · порог: больше 84 °C, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → GPU: температура, питание, вентилятор](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=71)

**Что случилось.** GPU cs2-win горячее 84 °C 10 минут

**Что это значит и что делать.** У GTX 1080 Ti с 84 °C начинается сброс частот, около 91 °C — аварийный. Десять минут выше 84 — карте не хватает продува в корпусе сервера: рендер замедлится раньше, чем что-то сломается.

<details><summary>Условие</summary>

```promql
nvidia_gpu_temperature_celsius{job="cs2-win"} > 84
```

Держится: 10m · группа `infra-hardware` · uid `hw-gpu-temp-high`

</details>

<a id="hw-nvme-wear-high"></a>

### Сервер: NVMe изношен на 80%

**предупреждение** · порог: больше 80%, держится 1 ч · панель: [Сервер — хост, диски, контейнеры, машины рендера → Износ Kingston](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=19)

**Что случилось.** Износ NVMe больше 80% заявленного ресурса

**Что это значит и что делать.** Диск ещё работает, но ресурс записи кончается. Смотреть «Записано за сутки»: кто пишет больше всех (рендер, CI) и планировать замену.

<details><summary>Условие</summary>

```promql
smart_nvme_percentage_used_ratio > 0.8
```

Держится: 1h · группа `infra-hardware` · uid `hw-nvme-wear-high`

</details>

<a id="hw-nvme-temp-high"></a>

### Сервер: NVMe перегрет

**предупреждение** · порог: больше 70 °C, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Память и диски](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=10)

**Что случилось.** NVMe горячее 70 °C: контроллер начинает сбрасывать скорость

**Что это значит и что делать.** Диск троттлит — медленнее запись демок, клипов и баз. Обычно следствие долгой записи (рендер, CI) без обдува.

<details><summary>Условие</summary>

```promql
node_hwmon_temp_celsius{sensor="temp1"} * on(chip) group_left(chip_name) node_hwmon_chip_names{chip_name="nvme"} > 70
```

Держится: 10m · группа `infra-hardware` · uid `hw-nvme-temp-high`

</details>

<a id="hw-win-commit-over-physical"></a>

### Сервер: cs2-win живёт в файле подкачки

**предупреждение** · порог: выделено больше физической и больше 1000 опер/с, держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Windows: память](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=74)

**Что случилось.** Windows на cs2-win выделила больше памяти, чем есть, и гоняет подкачку

**Что это значит и что делать.** Выделенная память Windows больше физической, и подкачка идёт быстрее 1000 операций в секунду полчаса подряд. Каждая такая операция — запись на NVMe хоста: 30.09.2026 подкачка cs2-win давала около 290 ГБ записи в сутки. На панели видно, какой процесс раздулся: чаще всего клиент Steam (с cs2#866 он перезапускается сам) или зависшая игра. На машине: ssh render@cs2-win, Get-Process | Sort-Object WS -Descending.

<details><summary>Условие</summary>

```promql
((windows_memory_committed_bytes{job="cs2-win"} / windows_memory_physical_total_bytes{job="cs2-win"}) > 1) and on(instance) (rate(windows_memory_swap_page_operations_total{job="cs2-win"}[30m]) > 1000)
```

Держится: 30m · группа `infra-hardware` · uid `hw-win-commit-over-physical`

</details>

<a id="hw-win-exporter-down"></a>

### Сервер: cs2-win не отдаёт метрики

**предупреждение** · порог: держится 5 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Экспортёр](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=64)

**Что случилось.** windows_exporter на cs2-win не отвечает

**Что это значит и что делать.** Prometheus не достучался до windows_exporter на Windows-машине рендера пять минут: машина выключена, зависла или служба экспортёра встала. Рендер движком HLAE при этом тоже, скорее всего, стоит. Экран — vmview на хосте, службы — ssh render@cs2-win.

<details><summary>Условие</summary>

```promql
up{job="cs2-win"} == 0 or absent(up{job="cs2-win"})
```

Держится: 5m · группа `infra-hardware` · uid `hw-win-exporter-down`

</details>

<a id="hw-gpu-collect-failing"></a>

### Сервер: nvidia-smi на cs2-win не отвечает

**предупреждение** · порог: держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → nvidia-smi](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=65)

**Что случилось.** nvidia-smi на cs2-win отказывает 10 минут

**Что это значит и что делать.** Опрос GTX 1080 Ti через nvidia-smi не удаётся десять минут: драйвер отвалился или карта пропала из виртуалки после перезагрузки хоста. Рендер на GPU в таком состоянии не пойдёт.

<details><summary>Условие</summary>

```promql
nvidia_smi_collect_ok{job="cs2-win"} == 0
```

Держится: 10m · группа `infra-hardware` · uid `hw-gpu-collect-failing`

</details>

<a id="hw-instance-oom-kills"></a>

### Сервер: в контейнере убит процесс по памяти

**предупреждение** · порог: больше 0 · панель: [Сервер — хост, диски, контейнеры, машины рендера → Убито за нехваткой памяти](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=58)

**Что случилось.** В ‹name› OOM-killer убил процесс

**Что это значит и что делать.** Процесс убит за нехватку памяти в инстансе (метка name): он умер молча, и то, что он делал, не доехало. Разбор 19.09.2026: все 17 убийств в web — это Chromium рендерера скриншотов с лимитом 512 МБ, шесть в cs2-render — старый потолок игры, поднятый с тех пор. Считается increase, а не changes: у одноразовых раннеров счётчик обнуляется на каждом задании, поэтому они исключены по имени — и большие ci-runner, и лёгкие ci-light. Нарочные потолки внутри cs2 (работник, разбор демки под limitmem) метрика Incus отличить не умеет — для этого нужен сбор по cgroup. С 29.09.2026 cs2-render здесь не считается: 55 убийств за неделю давали сообщение на каждое, у рендера теперь своя тревога с порогом — «Пристрелка: рендер убивают по памяти».

<details><summary>Условие</summary>

```promql
increase(incus_memory_OOM_kills_total{name!~"ci-(runner|light).*|cs2-render"}[15m]) > 0
```

Держится: 0m · группа `infra-hardware` · uid `hw-instance-oom-kills`

</details>

<a id="hw-io-pressure"></a>

### Сервер: задачи ждут диск

**предупреждение** · порог: больше 15%, держится 15 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Давление на ресурсы (PSI)](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=40)

**Что случилось.** Задачи хоста ждут ввод-вывод больше 15% времени

**Что это значит и что делать.** Все задачи хоста больше 15% времени ждут диск (PSI): упор в NVMe. За неделю до 19.09.2026 максимум был 6%. Смотреть занятость NVMe и запись по инстансам.

<details><summary>Условие</summary>

```promql
rate(node_pressure_io_stalled_seconds_total{job="node-host"}[5m]) > 0.15
```

Держится: 15m · группа `infra-hardware` · uid `hw-io-pressure`

</details>

<a id="hw-laptop-backup-old"></a>

### Сервер: копия на ноутбук старше 36 часов

**предупреждение** · порог: старше 36 ч, держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Копия на ноутбук](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=86)

**Что случилось.** Последняя удачная копия на ноутбук старше 36 часов

**Что это значит и что делать.** Копия незаменимого уезжает с сервера на ноутбук владельца каждую ночь, и удачный прогон пишет отметку в backup_laptop.prom на хосте. Отметка старая: ноутбук был выключен или скрипт упал. Смотреть last-run.log копии на ноутбуке и запустить scripts/backup-irreplaceable.sh руками. Значение около 30 лет значит, что отметки нет совсем: скрипт ни разу не дошёл до конца или файл на хосте удалён.

<details><summary>Условие</summary>

```promql
((time() - max(backup_laptop_last_success_timestamp_seconds)) > 36*3600) or ((absent(backup_laptop_last_success_timestamp_seconds) * 1e9) and on() (vector(time()) > 1790942400))
```

Держится: 30m · группа `infra-hardware` · uid `hw-laptop-backup-old`

</details>

<a id="hw-hw-metrics-missing"></a>

### Сервер: метрики железа не собираются

**предупреждение** · порог: держится 15 мин · панель: [Сайты samoy.love — сводка → Сбор метрик](https://metrics.samoy.love/d/samoylove-overview?viewPanel=26)

**Что случилось.** node_exporter хоста не отвечает: температуры, ZFS и SMART не видны

**Что это значит и что делать.** Сам хост может быть в порядке, но о перегреве или поломке диска мы не узнаем. systemctl status prometheus-node-exporter на хосте и правило web_isolation.

<details><summary>Условие</summary>

```promql
up{job="node-host"} == 0
```

Держится: 15m · группа `infra-hardware` · uid `hw-hw-metrics-missing`

</details>

<a id="hw-incus-metrics-missing"></a>

### Сервер: метрики контейнеров не собираются

**предупреждение** · порог: держится 15 мин · панель: [Сайты samoy.love — сводка → Сбор метрик](https://metrics.samoy.love/d/samoylove-overview?viewPanel=26)

**Что случилось.** Экспортёр Incus не отвечает: нет метрик по контейнерам и виртуалкам

**Что это значит и что делать.** Не видно памяти, процессора и убийств по памяти в контейнерах, в том числе cs2 и сборщиков CI. Проверить incus и клиентский сертификат метрик.

<details><summary>Условие</summary>

```promql
up{job="incus"} == 0
```

Держится: 15m · группа `infra-hardware` · uid `hw-incus-metrics-missing`

</details>

<a id="hw-dimm-temp-high"></a>

### Сервер: модуль памяти перегрет

**предупреждение** · порог: больше 65 °C, держится 15 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Память и диски](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=10)

**Что случилось.** Модуль DDR5 горячее 65 °C

**Что это значит и что делать.** На этой машине нет ECC: перегретая память — это тихие ошибки данных. Ослабить tRFC с 600 до 700–800 в BIOS или улучшить обдув.

<details><summary>Условие</summary>

```promql
node_hwmon_temp_celsius * on(chip) group_left(chip_name) node_hwmon_chip_names{chip_name="spd5118"} > 65
```

Держится: 15m · группа `infra-hardware` · uid `hw-dimm-temp-high`

</details>

<a id="hw-nvme-write-rate-high"></a>

### Сервер: на NVMe пишут больше 1,1 ТБ в сутки

**предупреждение** · порог: больше 1,1 ТБ, держится 1 ч · панель: [Сервер — хост, диски, контейнеры, машины рендера → Записано на диски](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=25)

**Что случилось.** Запись на NVMe больше 1,1 ТБ за сутки

**Что это значит и что делать.** При такой записи ресурс Kingston (1000 ТБ) уйдёт меньше чем за 2,5 года. 19.09.2026 было около 437 ГБ в сутки на диск. Искать, кто пишет: запись по инстансам и датасетам.

<details><summary>Условие</summary>

```promql
increase(smart_nvme_written_bytes_total[1d]) > 1.1e12
```

Держится: 1h · группа `infra-hardware` · uid `hw-nvme-write-rate-high`

</details>

<a id="hw-security-updates-pending"></a>

### Сервер: обновления безопасности не ставятся

**предупреждение** · порог: больше 0 все двое суток, держится 1 ч · панель: [Сервер — хост, диски, контейнеры, машины рендера → Обновления безопасности ждут](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=87)

**Что случилось.** На хосте двое суток ждут обновления безопасности

**Что это значит и что делать.** unattended-upgrades ставит обновления безопасности каждый день, а эти ждут уже двое суток: установка падает или стоит. На хосте: apt list --upgradable, journalctl -u apt-daily-upgrade, /var/log/unattended-upgrades/unattended-upgrades.log. Отложенные пакеты (held) сюда не входят, их видно на панели отдельно.

<details><summary>Условие</summary>

```promql
min_over_time(((sum(apt_upgrades_pending{job="node-host",origin=~".*-security.*"}) or vector(0)) - (sum(apt_upgrades_held{job="node-host",origin=~".*-security.*"}) or vector(0)))[2d:15m]) > 0
```

Держится: 1h · группа `infra-hardware` · uid `hw-security-updates-pending`

</details>

<a id="hw-zpool-scrub-overdue"></a>

### Сервер: проверка ZFS не проходила 40 дней

**предупреждение** · порог: дольше 40 дн, держится 1 ч · панель: [Сервер — хост, диски, контейнеры, машины рендера → Последний scrub](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=44)

**Что случилось.** Ежемесячный scrub пула ZFS не завершался 40 дней

**Что это значит и что делать.** Ежемесячный scrub пула пропущен (таймер zfs-scrub-monthly@tank). Без него тихая порча данных на диске не обнаруживается.

<details><summary>Условие</summary>

```promql
zpool_scrub_age_seconds > 40*86400
```

Держится: 1h · группа `infra-hardware` · uid `hw-zpool-scrub-overdue`

</details>

<a id="hw-link-flap"></a>

### Сервер: проводной линк моргнул

**предупреждение** · порог: больше 3600 · панель: [Сервер — хост, диски, контейнеры, машины рендера → Ошибки и обрывы линка](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=53)

**Что случилось.** Проводной интерфейс eno1 терял несущую

**Что это значит и что делать.** Проводной линк сервера пропадал за последний час. За неделю до 19.09.2026 было 4 перепада — кабель или порт роутера.

<details><summary>Условие</summary>

```promql
increase(node_network_carrier_changes_total{job="node-host",device="eno1"}[1h]) > 0 and on() (time() - node_boot_time_seconds{job="node-host"}) > 3600
```

Держится: 0m · группа `infra-hardware` · uid `hw-link-flap`

</details>

<a id="hw-prod-memory-pressure"></a>

### Сервер: прод ждёт память

**предупреждение** · порог: больше 5%, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Давление на память по контейнерам (PSI full)](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=80)

**Что случилось.** ‹name› стоит в ожидании памяти больше 5% времени

**Что это значит и что делать.** Все задачи ‹name› больше 5% времени ждут память: страдают сайт, базы или службы хоста. Упор раннеров CI в свой потолок сюда не входит. Кто занял память — панели «Давление на память по контейнерам» и «Память по инстансам».

<details><summary>Условие</summary>

```promql
rate(incus_cgroup_memory_stall_seconds_total{kind="full",name=~"cs2|web|host:system.slice"}[5m]) > 0.05
```

Держится: 10m · группа `infra-hardware` · uid `hw-prod-memory-pressure`

</details>

<a id="infra-cpu-saturated"></a>

### Сервер: процессор хоста занят полностью

**предупреждение** · порог: больше 90%, держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Загрузка CPU по режимам](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=15)

**Что случилось.** Процессор хоста занят больше чем на 90% полчаса подряд

**Что это значит и что делать.** Все контейнеры делят одни ядра: при полной загрузке тормозят сайты и растут очереди CI и рендера. Смотреть «Процессор по инстансам» — кто съел; обычно это CI-сборки или рендер.

<details><summary>Условие</summary>

```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{job="node-host",mode="idle"}[5m])) * 100) > 90
```

Держится: 30m · группа `infra-host` · uid `infra-cpu-saturated`

</details>

<a id="hw-zpool-capacity-high"></a>

### Сервер: пул ZFS заполнен на 80%

**предупреждение** · порог: больше 80%, держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Кто занимает пул tank](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=52)

**Что случилось.** Пул ZFS заполнен больше чем на 80%

**Что это значит и что делать.** Пул заполнен больше чем на 80 %: у ZFS после этого падает скорость записи и растёт фрагментация. «Сервер: в контейнере web кончается диск» смотрит только корень хоста (ext4), пул он не видит. Смотреть zfs list -o space: снимки sanoid, квоты демок и клипов, диск cs2-win.

<details><summary>Условие</summary>

```promql
zpool_capacity_ratio{job="node-host"} > 0.8
```

Держится: 30m · группа `infra-hardware` · uid `hw-zpool-capacity-high`

</details>

<a id="hw-smart-collect-failing"></a>

### Сервер: сбор SMART и ZFS сломан

**предупреждение** · порог: держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Возраст SMART и ZFS](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=49)

**Что случилось.** Сборщик SMART, ZFS или OOM на хосте отказывает

**Что это значит и что делать.** Здоровье дисков и убийства по памяти на хосте сейчас неизвестны: тревоги по ним молчат не потому, что всё хорошо. journalctl -u node-textfile-collect на хосте.

<details><summary>Условие</summary>

```promql
smart_collect_ok == 0 or zpool_collect_ok == 0 or host_oom_collect_ok == 0
```

Держится: 30m · группа `infra-hardware` · uid `hw-smart-collect-failing`

</details>

<a id="infra-network-errors-high"></a>

### Сервер: сетевой интерфейс теряет пакеты с ошибками

**предупреждение** · порог: больше 0, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Ошибки и обрывы линка](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=53)

**Что случилось.** Интерфейс ‹device› получает или отправляет пакеты с ошибками

**Что это значит и что делать.** Ошибки на физическом интерфейсе — кабель, порт роутера или драйвер. Сайты в это время могут открываться рывками. Смотреть «Ошибки и обрывы линка» и ethtool -S на хосте.

<details><summary>Условие</summary>

```promql
rate(node_network_receive_errs_total{device!~"lo|veth.*|docker.*|br-.*"}[5m]) + rate(node_network_transmit_errs_total{device!~"lo|veth.*|docker.*|br-.*"}[5m]) > 0
```

Держится: 10m · группа `infra-host` · uid `infra-network-errors-high`

</details>

<a id="hw-snapshots-stale"></a>

### Сервер: снимки ZFS не делались больше суток

**предупреждение** · порог: старше 28 ч, держится 30 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Возраст последнего снимка sanoid](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=85)

**Что случилось.** Самому свежему снимку sanoid датасета ‹dataset› больше 28 часов

**Что это значит и что делать.** Снимки делаются раз в сутки, значит, последний прогон sanoid этот датасет не снял, и точки отката за сегодня нет. На хосте: systemctl status sanoid.timer sanoid.service, journalctl -u sanoid, zfs list -t snapshot -o name,creation -s creation <датасет>. Если метки dataset нет, сборщик не смог прочитать sanoid.conf или список снимков: journalctl -u node-textfile-collect.

<details><summary>Условие</summary>

```promql
((time() - zfs_snapshot_newest_timestamp_seconds{job="node-host"}) > 28*3600) or (zfs_snapshot_collect_ok{job="node-host"} == 0)
```

Держится: 30m · группа `infra-hardware` · uid `hw-snapshots-stale`

</details>

<a id="hw-nvme-spare-low"></a>

### Сервер: у NVMe кончается резерв блоков

**предупреждение** · порог: меньше 20%, держится 1 ч · панель: [Сервер — хост, диски, контейнеры, машины рендера → Резерв блоков NVMe](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=46)

**Что случилось.** Резерв запасных блоков NVMe меньше 20%

**Что это значит и что делать.** Резерв запасных блоков NVMe кончается — диск начал активно заменять изношенные ячейки. Готовить замену диска.

<details><summary>Условие</summary>

```promql
smart_nvme_available_spare_ratio < 0.2
```

Держится: 1h · группа `infra-hardware` · uid `hw-nvme-spare-low`

</details>

<a id="hw-swap-thrashing"></a>

### Сервер: хост гоняет swap туда-обратно

**предупреждение** · порог: больше 1000, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Обмен со swap](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=41)

**Что случилось.** Хост непрерывно выгружает и подгружает страницы swap

**Что это значит и что делать.** Страницы одновременно и вытесняются в swap, и читаются обратно — памяти не хватает прямо сейчас, всё тормозит. Swap за неделю до 19.09.2026 бывал занят до 7 из 8 ГиБ.

<details><summary>Условие</summary>

```promql
rate(node_vmstat_pswpin{job="node-host"}[5m]) > 1000 and rate(node_vmstat_pswpout{job="node-host"}[5m]) > 1000
```

Держится: 10m · группа `infra-hardware` · uid `hw-swap-thrashing`

</details>

<a id="hw-memory-pressure"></a>

### Сервер: хост задыхается без памяти

**предупреждение** · порог: больше 20%, держится 10 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Давление на ресурсы (PSI)](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=40)

**Что случилось.** Все задачи хоста стоят в ожидании памяти больше 20% времени

**Что это значит и что делать.** Все задачи хоста больше 20% времени ждут память (PSI full, без самоторможения раннеров CI на их собственном потолке): это трэш, как 22.09 (75%) и 26.09 (97%). Кто ждёт — панель «Давление на память по контейнерам»; прод отдельно тревожит «Сервер: прод ждёт память». Кто съел — панель «Память инстансов» на дашборде железа; частый виновник — cs2-render с открытой игрой.

<details><summary>Условие</summary>

```promql
(rate(node_pressure_memory_stalled_seconds_total{job="node-host"}[5m]) - on() group_left() (max(rate(incus_cgroup_memory_stall_seconds_total{kind="full",name=~"ci-(runner|light).*"}[5m])) or vector(0))) > 0.2 or (rate(node_pressure_memory_stalled_seconds_total{job="node-host"}[5m]) > 0.2 and on() (node_memory_MemAvailable_bytes{job="node-host"} / node_memory_MemTotal_bytes{job="node-host"}) < 0.1)
```

Держится: 10m · группа `infra-hardware` · uid `hw-memory-pressure`

</details>

<a id="hw-reboot-required"></a>

### Сервер: хосту неделю нужна перезагрузка

**предупреждение** · порог: держится 7 сут · панель: [Сервер — хост, диски, контейнеры, машины рендера → Нужна перезагрузка](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=88)

**Что случилось.** Установленные обновления неделю ждут перезагрузки хоста

**Что это значит и что делать.** После обновления ядра или системных библиотек хост неделю не перезагружался, и исправления не действуют. Что именно ждёт: cat /var/run/reboot-required.pkgs на хосте. Перезагрузка гасит прод, CI и игры, время выбирает владелец; после неё проверить, что поднялись все инстансы с автозапуском.

<details><summary>Условие</summary>

```promql
min_over_time((max(node_reboot_required{job="node-host"}) or vector(0))[7d:1h]) > 0
```

Держится: 1h · группа `infra-hardware` · uid `hw-reboot-required`

</details>

<a id="hw-time-not-synced"></a>

### Сервер: часы хоста не синхронизированы

**предупреждение** · порог: держится 15 мин · панель: [Сервер — хост, диски, контейнеры, машины рендера → Часы синхронизированы](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=61)

**Что случилось.** Часы хоста не синхронизированы

**Что это значит и что делать.** Часы хоста не синхронизированы (NTP). Уехавшие часы ломают TLS, сроки токенов и сопоставление журналов.

<details><summary>Условие</summary>

```promql
node_timex_sync_status{job="node-host"} == 0
```

Держится: 15m · группа `infra-hardware` · uid `hw-time-not-synced`

</details>

<a id="infra-node-rebooted"></a>

### Сервер: хост перезагрузился

**для сведения** · панель: [Сервер — хост, диски, контейнеры, машины рендера → Аптайм хоста](https://metrics.samoy.love/d/samoylove-hardware?viewPanel=62)

**Что случилось.** Хост перезагрузился меньше пяти минут назад

**Что это значит и что делать.** Для сведения: если перезагрузку не делали руками — смотреть journalctl -b -1 на хосте (паника, питание, сторожевой таймер). После перезагрузки проверить, что поднялись все инстансы с автозапуском.

<details><summary>Условие</summary>

```promql
time() - node_boot_time_seconds{job="node-host"} < 300
```

Держится: 0s · группа `infra-host` · uid `infra-node-rebooted`

</details>

<a id="cs2-area"></a>

## Пристрелка

<a id="cs2-parse-postponed"></a>

### Пристрелка: ClickHouse не принимает разбор

**авария** · порог: больше 0, держится 1 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: отложенные разборы](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1502)

**Что случилось.** Разборы откладываются больше часа: ClickHouse не принимает запись

**Что это значит и что делать.** Свежие матчи не появляются ни на сайте, ни в боте. Задания при этом не пропадают: каждое ждёт и пробует снова. Смотреть ClickHouse в контейнере cs2: жив ли, есть ли место, нет ли TOO_MANY_PARTS в журнале cs2-chain.

<details><summary>Условие</summary>

```promql
cs2_parse_postponed > 0
```

Держится: 1h · группа `product-cs2` · uid `cs2-parse-postponed`

</details>

<a id="cs2-steam-key-rejected"></a>

### Пристрелка: Steam отклонил наш ключ

**авария** · порог: больше 3, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Чем отвечает Steam](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=502)

**Что случилось.** Steam Web API отвечает «ключ недействителен»

**Что это значит и что делать.** Условия Valve разрешают отозвать ключ без предупреждения и без объяснения — это не поломка, а сторона договора. Для игроков это значит: история матчей не пополняется, ники и аватары застыли. Сервис обязан пережить это как временную недоступность, страницы отдают то, что уже собрано.

<details><summary>Условие</summary>

```promql
sum(increase(cs2_steam_requests_total{result="ключ_отклонён"}[1h])) > 3
```

Держится: 10m · группа `product-cs2` · uid `cs2-steam-key-rejected`

</details>

<a id="cs2-demos-expiring"></a>

### Пристрелка: демки вот-вот исчезнут у Valve

**авария** · порог: больше 0, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Исчезнут у Valve](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=203)

**Что случилось.** Есть матчи, у которых осталось меньше трёх дней окна хранения

**Что это значит и что делать.** ЕДИНСТВЕННАЯ ТРЕВОГА ПРО БЕЗВОЗВРАТНУЮ ПОТЕРЮ. Valve держит демку около тридцати дней; не забранный сейчас матч не разобрать уже никогда — ни по просьбе игрока, ни за деньги. Проверить скачиватель: место на диске, связь с CDN, не выключен ли работник.

<details><summary>Условие</summary>

```promql
cs2_chain_demos_expiring_soon > 0
```

Держится: 10m · группа `product-cs2` · uid `cs2-demos-expiring`

</details>

<a id="cs2-render-lab-at-public"></a>

### Пристрелка: лабораторная машина рендера при публичном сервисе

**авария** · порог: держится 5 мин · панель: [Пристрелка — cs.samoy.love → Машины рендера: режим](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1602)

**Что случилось.** Машина рендера ‹engine› в лабораторном режиме, а сервис публичный

**Что это значит и что делать.** Ролики с этой машины кладут музыку, картинки и голоса без лицензии и уходят людям в публичный сервис. Сразу: остановить работника на этой машине (задания без камер уйдут другой), затем поставить CS2_MODE=public в её настройках и запустить снова. Уже снятые ролики с лабораторными ассетами найти по render_jobs этой машины после смены режима сервиса.

<details><summary>Условие</summary>

```promql
cs2_render_mode_mismatch == 1 and on() cs2_service_mode{mode="public"} == 1
```

Держится: 5m · группа `product-cs2` · uid `cs2-render-lab-at-public`

</details>

<a id="cs2-gc-down"></a>

### Пристрелка: нет связи с сервером Valve

**авария** · порог: держится 30 мин · панель: [Пристрелка — cs.samoy.love → Связь с Valve](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=200)

**Что случилось.** Прослойка Game Coordinator не отвечает или потеряла сессию Steam

**Что это значит и что делать.** Новые матчи перестают приходить сами: у игрока в истории остаётся «найден» и ничего дальше, при этом сайт выглядит здоровым. Причины по частоте: обновление CS2, отозванный токен, бан серверного аккаунта. Загрузка демки руками продолжает работать.

<details><summary>Условие</summary>

```promql
cs2_gc_ready == 0
```

Держится: 30m · группа `product-cs2` · uid `cs2-gc-down`

</details>

<a id="cs2-gc-unparsed"></a>

### Пристрелка: ответы сервера Valve перестали разбираться

**авария** · порог: больше 0, держится 5 мин · панель: [Пристрелка — cs.samoy.love → Что отвечает сервер Valve](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=207)

**Что случилось.** Game Coordinator отвечает, но разобрать ответ мы не можем

**Что это значит и что делать.** Так выглядит очередной апдейт CS2 — тот самый постоянный налог. Пока не починим имена полей, у всех игроков матчи стоят на стадии «найден»: счёт не приходит, демка не скачивается, разбора нет. Сырой ответ пишется в журнал целиком — по нему и правится.

<details><summary>Условие</summary>

```promql
sum(increase(cs2_gc_requests_total{result="не_разобран"}[1h])) > 0
```

Держится: 5m · группа `product-cs2` · uid `cs2-gc-unparsed`

</details>

<a id="cs2-queue-stuck"></a>

### Пристрелка: разбор матчей встал

**авария** · порог: держится 15 мин · панель: [Пристрелка — cs.samoy.love → В очереди](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=300)

**Что случилось.** Очередь разбора не убывает, а разборов не происходит вовсе

**Что это значит и что делать.** Демки лежат, разбора нет ни у кого: у игрока страница матча вечно показывает «разбирается». Обычная причина — обновление игры сломало парсер; вторая — воркеры не поднялись после выкатки. Отказ выглядит как тишина, а не как ошибка.

<details><summary>Условие</summary>

```promql
min_over_time(cs2_parse_queue_depth[15m]) > 0 and on(instance) sum by (instance) (rate(cs2_parse_total[15m])) == 0
```

Держится: 15m · группа `product-cs2` · uid `cs2-queue-stuck`

</details>

<a id="cs2-api-down"></a>

### Пристрелка: сайт не отвечает

**авария** · порог: держится 5 мин · панель: [Пристрелка — cs.samoy.love → Сайт отвечает](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=100)

**Что случилось.** Служба cs2-api не отвечает на сбор метрик

**Что это значит и что делать.** Для игрока это полностью недоступный сайт: ни разбора, ни истории, ни входа. Смотреть journalctl -u cs2-api в контейнере cs2; выкатка откатывается сама, если не поднялся healthz.

<details><summary>Условие</summary>

```promql
up{job="cs2-api"} == 0
```

Держится: 5m · группа `product-cs2` · uid `cs2-api-down`

</details>

<a id="cs2-not-ready"></a>

### Пристрелка: сервис не подключился к базам

**авария** · порог: держится 10 мин · панель: [Пристрелка — cs.samoy.love → Базы готовы](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=402)

**Что случилось.** Сайт поднят, но Postgres или ClickHouse недоступны

**Что это значит и что делать.** Человек видит страницу «сервис поднимается» и 503 везде, где нужны данные: разбор, профиль, поиск. Само чинится, когда база встанет; дольше десяти минут — значит база не поднимется без нас. Причина названа словами в /readyz.

<details><summary>Условие</summary>

```promql
cs2_ready == 0
```

Держится: 10m · группа `product-cs2` · uid `cs2-not-ready`

</details>

<a id="cs2-http-errors"></a>

### Пристрелка: страницы отвечают ошибками

**авария** · порог: больше 5%, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Ошибки по разделам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=109)

**Что случилось.** Больше 5% ответов сайта — пятисотки

**Что это значит и что делать.** Каждый такой ответ — страница, которая у человека не открылась. Какой именно раздел ломается, видно на панели «Ошибки по разделам»: журнал nginx этого не покажет, он видит домен целиком.

<details><summary>Условие</summary>

```promql
sum(rate(cs2_http_requests_total{code=~"5.."}[15m])) / clamp_min(sum(rate(cs2_http_requests_total[15m])), 0.0001) > 0.05
```

Держится: 10m · группа `product-cs2` · uid `cs2-http-errors`

</details>

<a id="cs2-storage-crit"></a>

### Пристрелка: хранилище демок почти полное

**авария** · порог: больше 85%, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Заполнение квоты](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=701)

**Что случилось.** Занято больше 85% квоты хранилища демок

**Что это значит и что делать.** Скачиватель уже останавливает круги, когда остаётся меньше десяти гигабайт: новые матчи перестают забираться, а окно у Valve — тридцать дней. Загрузка руками тоже начнёт отказывать. Место кончается тихо и сразу у всех, включая временные файлы разбора.

<details><summary>Условие</summary>

```promql
cs2_demo_storage_used_bytes / cs2_demo_storage_total_bytes > 0.85
```

Держится: 15m · группа `product-cs2` · uid `cs2-storage-crit`

</details>

<a id="cs2-chain-no-leader"></a>

### Пристрелка: цепочку никто не ведёт

**авария** · порог: держится 10 мин · панель: [Пристрелка — cs.samoy.love → Цепочка одна](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=406)

**Что случилось.** Ни один процесс не держит замок цепочки матчей

**Что это значит и что делать.** Матчи перестают приходить сами, а сайт при этом выглядит здоровым. Проверить cs2-chain в контейнере cs2: запущен ли, не завис ли на замке в Postgres.

<details><summary>Условие</summary>

```promql
max(cs2_chain_leader{state="leading"}) == 0 and on() max(cs2_chain_scrape_up) == 1
```

Держится: 10m · группа `product-cs2` · uid `cs2-chain-no-leader`

</details>

<a id="cs2-telegram-rejected"></a>

### Пристрелка: Telegram не принимает сообщения бота

**предупреждение** · порог: не меньше 3, держится 5 мин · панель: [Пристрелка — cs.samoy.love → Доставка: не дошло по причинам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1801)

**Что случилось.** Telegram отказал в отправке разбора три и больше раз за час

**Что это значит и что делать.** Разборы после матча не доходят до людей. «токен_отвергнут» — ключ бота отозван, не дойдёт ничего: поставить новый CS2_TELEGRAM_BOT_TOKEN. «отказ» — ответ Telegram, причина в журнале cs2-chain. Люди, закрывшие бота, сюда не входят.

<details><summary>Условие</summary>

```promql
sum(increase(cs2_deliveries_total{result=~"отказ|токен_отвергнут"}[1h])) >= 3
```

Держится: 5m · группа `product-cs2` · uid `cs2-telegram-rejected`

</details>

<a id="cs2-avatars-failing"></a>

### Пристрелка: аватары не отдаются

**предупреждение** · порог: не меньше 500%, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Аватары со своего домена](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1803)

**Что случилось.** Больше пятой части аватаров не отдаётся

**Что это значит и что делать.** Вместо лиц на страницах серые кружки; сама страница при этом целая, и без этой тревоги мы бы не узнали вовсе. «нет_аватара» сюда не входит: это не отказ, а человек без картинки в Steam.

<details><summary>Условие</summary>

```promql
sum(rate(cs2_avatar_requests_total{result="отказ"}[1h])) / clamp_min(sum(rate(cs2_avatar_requests_total[1h])), 0.0001) > 0.2 and sum(increase(cs2_avatar_requests_total[1h])) >= 5
```

Держится: 30m · группа `product-cs2` · uid `cs2-avatars-failing`

</details>

<a id="cs2-outdated"></a>

### Пристрелка: архив разобран старым составом данных

**предупреждение** · порог: больше 0, держится 6 ч · панель: [Пристрелка — cs.samoy.love → Старым составом данных](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=303)

**Что случилось.** Есть матчи, разобранные устаревшей версией состава данных

**Что это значит и что делать.** Метрики считаются по всему архиву сразу, поэтому половина матчей по-старому — это числа, которые между собой несопоставимы, при совершенно целом на вид сайте. Работник пересчёта должен разгребать это сам; не убывает — значит он не идёт.

<details><summary>Условие</summary>

```promql
cs2_chain_matches_outdated > 0
```

Держится: 6h · группа `product-cs2` · uid `cs2-outdated`

</details>

<a id="cs2-reconcile-mismatch"></a>

### Пристрелка: базы и диск разошлись

**предупреждение** · порог: больше 0, держится 1 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: сверка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1505)

**Что случилось.** Ночная сверка нашла расхождение баз и диска (вид — метка kind)

**Что это значит и что делать.** Сверка только считает, удалять данные без человека ей нельзя. clickhouse_orphan — строки матча без задания, file_orphan — файл демки без записи, row_no_file — запись без файла, то есть демку уже не перечитать. Разбирать руками, начиная с row_no_file.

<details><summary>Условие</summary>

```promql
cs2_reconcile_mismatches{kind=~"clickhouse_orphan|file_orphan|row_no_file"} > 0
```

Держится: 1h · группа `product-cs2` · uid `cs2-reconcile-mismatch`

</details>

<a id="cs2-telegram-down"></a>

### Пристрелка: бот Telegram не отвечает

**предупреждение** · порог: держится 15 мин · панель: [Пристрелка — cs.samoy.love → Бот: опросы Telegram](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1802)

**Что случилось.** Пятнадцать минут ни одного удачного опроса Telegram

**Что это значит и что делать.** Третий шаг первого захода не проходится: код привязки из ссылки некому погасить, и человек застревает на странице «привяжи бота». Одиночные обрывы опроса (unexpected EOF, сброс соединения — обход блокировок на роутере, чаще в начале часа) бот переживает сам за секунды, поэтому тревога — на долгое молчание, а не на число обрывов: до 11.09.2026 она горела от пяти обрывов в час при живом боте.

<details><summary>Условие</summary>

```promql
(sum(increase(cs2_telegram_polls_total{result="ok"}[15m])) or vector(0)) == 0 and on() cs2_worker_enabled{worker="бот"} == 1
```

Держится: 15m · группа `product-cs2` · uid `cs2-telegram-down`

</details>

<a id="cs2-container-unit-failed"></a>

### Пристрелка: в контейнере упала служба

**предупреждение** · порог: держится 5 мин · панель: [Пристрелка — cs.samoy.love → Службы в контейнерах cs2: упавшие](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1004)

**Что случилось.** В контейнере ‹container› упала служба ‹unit›

**Что это значит и что делать.** Что именно перестало работать, зависит от службы: таймер дампа — нет резервной копии, пересчёт — старые числа на страницах, работник рендера — клипы не пишутся. Смотреть journalctl -u ‹unit› в контейнере ‹container›; после починки systemctl reset-failed.

<details><summary>Условие</summary>

```promql
incus_container_unit_failed == 1
```

Держится: 5m · группа `product-cs2` · uid `cs2-container-unit-failed`

</details>

<a id="cs2-pg-dump-old"></a>

### Пристрелка: дамп Postgres давно не снимался

**предупреждение** · порог: дольше 26 ч, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Резервные копии](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1501)

**Что случилось.** Последний удачный дамп Postgres старше 26 часов

**Что это значит и что делать.** Дамп снимается каждый день, значит, вчерашний не удался. Если сейчас потерять базу, пропадут учётные записи, коды и очередь с последнего дампа. Смотреть cs2-pgdump в контейнере cs2: таймер, журнал, место под дампы.

<details><summary>Условие</summary>

```promql
cs2_pg_dump_age_seconds > 93600
```

Держится: 30m · группа `product-cs2` · uid `cs2-pg-dump-old`

</details>

<a id="cs2-render-engine-broken"></a>

### Пристрелка: движок съёмки сломан

**предупреждение** · порог: держится 2 ч · панель: [Пристрелка — cs.samoy.love → Движок съёмки](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=911)

**Что случилось.** Проба движка съёмки не проходит дольше двух часов (движок — метка engine)

**Что это значит и что делать.** У hlae это значит, что камеры повтора не работают: обычные заказы уходят на Linux, а ролики с камерами ждут. Почти всегда причина — обновление CS2, под которое HLAE ещё не вышла или не поставлена. Если одновременно горит «вышла новая версия HLAE» — ставить её на cs2-win и гонять стенд. Журнал — C:\cs2\logs\render.log на cs2-win.

<details><summary>Условие</summary>

```promql
cs2_render_engine_ok == 0
```

Держится: 2h · группа `product-cs2` · uid `cs2-render-engine-broken`

</details>

<a id="cs2-downloads-failing"></a>

### Пристрелка: демки не скачиваются с CDN Valve

**предупреждение** · порог: больше 30% попыток и не меньше 3 отказов за час, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Походы за демками на CDN Valve](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=208)

**Что случилось.** Больше трети походов за файлом кончаются обрывом связи

**Что это значит и что делать.** Матчи копятся нескачанными, а окно хранения у Valve — тридцать дней: затянувшийся отказ превращается в потерю навсегда. Считается ПО ПОПЫТКАМ, а не по состоянию в базе: состояние помнит и то, что случилось месяц назад и починке не подлежит.

<details><summary>Условие</summary>

```promql
sum(rate(cs2_demo_download_total{result=~"нет_связи|обрыв"}[1h])) / clamp_min(sum(rate(cs2_demo_download_total[1h])), 0.0001) > 0.3 and sum(increase(cs2_demo_download_total{result=~"нет_связи|обрыв"}[1h])) >= 3
```

Держится: 15m · группа `product-cs2` · uid `cs2-downloads-failing`

</details>

<a id="cs2-reports-behind"></a>

### Пристрелка: документы отчёта не догоняют

**предупреждение** · порог: не меньше 0, держится 6 ч · панель: [Пристрелка — cs.samoy.love → Документы отчёта отстают](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=309)

**Что случилось.** Пересчёт документов отчёта встал

**Что это значит и что делать.** Страницы матчей считаются на лету и медленнее, пока документы устаревшие. Проверить работника пересчёта.

<details><summary>Условие</summary>

```promql
cs2_reports_outdated > 0 and deriv(cs2_reports_outdated[1h]) >= 0
```

Держится: 6h · группа `product-cs2` · uid `cs2-reports-behind`

</details>

<a id="cs2-upload-broken"></a>

### Пристрелка: загрузка демок отказывает по нашей вине

**предупреждение** · порог: больше 0, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Загрузка демок руками](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=602)

**Что случилось.** Приём демки упал не из-за файла, а из-за нас: диск или база

**Что это значит и что делать.** Это единственное место, где отказ человек видит СРАЗУ — и обычно уходит. Для матчей старше тридцати дней и демок с площадок загрузка руками не запасной путь, а единственный.

<details><summary>Условие</summary>

```promql
increase(cs2_upload_total{result="наша_сторона"}[1h]) > 0
```

Держится: 10m · группа `product-cs2` · uid `cs2-upload-broken`

</details>

<a id="cs2-render-stalled"></a>

### Пристрелка: заказ клипа ждёт больше получаса

**предупреждение** · порог: дольше 30 мин, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Ожидание по классам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1603)

**Что случилось.** Заказ клипа человека ждёт машину ‹engine› дольше получаса

**Что это значит и что делать.** Человек заказал клип и ждёт. Считаются только заказы, которые можно взять прямо сейчас: без ждущих повтора и заданий сломанного движка, без промо. Смотреть «Машины рендера: отметка» — жива ли машина, и «Рендер: очередь по машинам».

<details><summary>Условие</summary>

```promql
max by (engine) (cs2_render_waiting_seconds{class=~"order|paid"}) > 1800
```

Держится: 15m · группа `product-cs2` · uid `cs2-render-stalled`

</details>

<a id="cs2-worker-mark-absent"></a>

### Пристрелка: запущенный работник ни разу не отметился

**предупреждение** · порог: держится 6 ч · панель: [Пристрелка — cs.samoy.love → Сколько молчит работник](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=401)

**Что случилось.** Работник ‹worker› запущен, а удачного круга не отметил ни разу

**Что это значит и что делать.** Либо работник падает на каждом круге с самого запуска, либо отметка в service_marks не пишется (нет прав, другая база). Для человека это то же, что молчащий работник: данные не свежеют. Смотреть журнал cs2-chain по имени работника и строку worker:‹worker› в service_marks.

<details><summary>Условие</summary>

```promql
max by (worker) (cs2_worker_enabled{worker=~"профили|faceit|друзья|пересчёт"}) == 1 unless on(worker) max by (worker) (cs2_worker_last_success_timestamp_seconds)
```

Держится: 6h · группа `product-cs2` · uid `cs2-worker-mark-absent`

</details>

<a id="cs2-codes-rebind"></a>

### Пристрелка: игроку нужно перевыпустить код Steam

**предупреждение** · порог: больше 0, держится 6 ч · панель: [Пристрелка — cs.samoy.love → Нужен новый код](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=205)

**Что случилось.** Steam отверг код аутентификации у одного из игроков

**Что это значит и что делать.** У этого человека история матчей остановилась совсем: новые матчи не находятся, разбора не будет. Починить может ТОЛЬКО он сам — взять новый код на странице помощи Steam, — и, значит, сказать ему об этом должны мы.

<details><summary>Условие</summary>

```promql
cs2_chain_codes_needing_rebind > 0
```

Держится: 6h · группа `product-cs2` · uid `cs2-codes-rebind`

</details>

<a id="cs2-render-failed"></a>

### Пристрелка: клипы проваливаются

**предупреждение** · порог: не меньше 3, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Рендер: провалы за сутки по классам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1702)

**Что случилось.** За час провалилось три и больше заданий рендера

**Что это значит и что делать.** Завершённые отказы пользовательских и автоматических заказов за час из render_history, отдельно по машине. Удаление или повтор render_jobs не вычитает уже случившиеся ошибки. Диагностические прогоны видны отдельно на дашборде и не входят в эту тревогу. Проверить классы ошибок и очередь машины; историю не удалять.

<details><summary>Условие</summary>

```promql
(sum by (engine) (cs2_render_failed_window{requester=~"user|system",window="1h"}) >= 3) and on() (cs2_chain_scrape_up == 1)
```

Держится: 10m · группа `product-cs2` · uid `cs2-render-failed`

</details>

<a id="cs2-steam-rate"></a>

### Пристрелка: ключ Steam упирается в темп

**предупреждение** · порог: больше 90%, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Ключ Steam: доля потолка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=510)

**Что случилось.** Вызовы Steam идут на пределе частоты

**Что это значит и что делать.** Страницы ждут Steam: фоновый сбор занял почти весь темп ключа. Смотреть расход по работникам на дашборде cs2.

<details><summary>Условие</summary>

```promql
max(cs2_budget_used{resource="steam_key",window="10с"}) / (10 * max(cs2_external_limit{limit="steam_вызовов_в_секунду"})) > 0.9
```

Держится: 30m · группа `product-cs2` · uid `cs2-steam-rate`

</details>

<a id="cs2-summaries-failed"></a>

### Пристрелка: коды матчей закрыты с ошибкой

**предупреждение** · порог: больше 5, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Не получили счёт](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=801)

**Что случилось.** Больше пяти кодов закрыто с непустой причиной отказа

**Что это значит и что делать.** Эти матчи в историю игрока уже не попадут: попытки исчерпаны. Разово так бывает у матчей, которых у Valve нет; растущее число означает нашу поломку — чаще всего разбор ответа GC после апдейта игры.

<details><summary>Условие</summary>

```promql
cs2_chain_codes_summary_failed > 5
```

Держится: 30m · группа `product-cs2` · uid `cs2-summaries-failed`

</details>

<a id="cs2-admin-login-bruteforce"></a>

### Пристрелка: кто-то подбирает пароль админки

**предупреждение** · панель: [Пристрелка — cs.samoy.love → Вход в админку по исходам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1202)

**Что случилось.** Кто-то подбирает пароль админки cs2

**Что это значит и что делать.** За 15 минут пять и больше неверных паролей к /admin или попытка при уже закрытом входе. Если это не ты — кто-то перебирает пароль владельца: вход сам закрыт на 15 минут, но стоит посмотреть журнал cs2-api и журнал nginx и сменить пароль.

<details><summary>Условие</summary>

```promql
(sum(increase(cs2_admin_login_total{result="blocked"}[15m])) > 0) or (sum(increase(cs2_admin_login_total{result="wrong"}[15m])) >= 5)
```

Держится: 0m · группа `product-cs2` · uid `cs2-admin-login-bruteforce`

</details>

<a id="cs2-clickhouse-parts"></a>

### Пристрелка: куски ClickHouse копятся

**предупреждение** · порог: больше 200, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Базы: куски ClickHouse](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=2001)

**Что случилось.** В одной партиции ClickHouse больше 200 кусков

**Что это значит и что делать.** На трёхсотом куске ClickHouse отказывает в любой вставке, и разбор встаёт. Обычно это значит, что слияния не успевают за мелкими вставками. Смотреть system.parts и system.merges.

<details><summary>Условие</summary>

```promql
cs2_clickhouse_parts{scope="max_partition"} > 200
```

Держится: 15m · группа `product-cs2` · uid `cs2-clickhouse-parts`

</details>

<a id="cs2-chain-waiting"></a>

### Пристрелка: матч ждёт разбора больше двух часов

**предупреждение** · порог: дольше 2 ч, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Сколько ждёт игрок на каждом шаге](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=106)

**Что случилось.** Самое старое дело в цепочке висит дольше двух часов

**Что это значит и что делать.** Игрок доиграл, обновляет страницу и не видит разбора. Панель «Сколько ждёт игрок» показывает, на каком шаге затор: ждёт счёта — работник Game Coordinator, ждёт файла — скачиватель, ждёт разбора — воркер. Обещано «сам и сразу», а не «к утру».

<details><summary>Условие</summary>

```promql
max(cs2_chain_waiting_seconds) > 7200
```

Держится: 30m · группа `product-cs2` · uid `cs2-chain-waiting`

</details>

<a id="cs2-render-disk-unknown"></a>

### Пристрелка: машина не измеряет свободное место

**предупреждение** · порог: нет замера у живой машины 5 минут · панель: [Пристрелка — cs.samoy.love → Место на машинах рендера](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=912)

**Что случилось.** Живая машина ‹engine› не измеряет свободное место

**Что это значит и что делать.** Неизвестное место не означает достаточный запас. Проверить доступность каталогов клипов, работы и кэша под учётной записью работника. Windows должна использовать GetDiskFreeSpaceExW. Задания остаются в очереди до успешного замера.

<details><summary>Условие</summary>

```promql
(cs2_render_heartbeat_age_seconds < 180) unless on(engine) cs2_render_clips_free_bytes
```

Держится: 5m · группа `product-cs2` · uid `cs2-render-disk-unknown`

</details>

<a id="cs2-render-heartbeat"></a>

### Пристрелка: машина рендера молчит

**предупреждение** · порог: дольше 10 мин, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Машины рендера: отметка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1601)

**Что случилось.** Машина рендера ‹engine› молчит больше 10 минут

**Что это значит и что делать.** Её задания без камер уже уходят другим машинам, а ролики с камерами повтора ждут. Смотреть, жив ли работник: на cs2-render это служба в контейнере, на cs2-win — задача планировщика cs2-render и C:\cs2\logs\render.log.

<details><summary>Условие</summary>

```promql
cs2_render_heartbeat_age_seconds > 600
```

Держится: 10m · группа `product-cs2` · uid `cs2-render-heartbeat`

</details>

<a id="cs2-demo-storage-low"></a>

### Пристрелка: место под демки кончается

**предупреждение** · порог: меньше 15, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Рост хранилища](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=702)

**Что случилось.** Под демки осталось меньше 15 ГБ: скачиватель встанет на десяти

**Что это значит и что делать.** Демки хранятся целиком и без срока — это решение, а не недосмотр, и защита пула здесь квота, а не удаление. Ниже десяти гигабайт скачиватель перестаёт начинать круги: матчи продолжат находиться, но файлы за ними приходить перестанут, а окно Valve — тридцать дней. Решать владельцу: расширить квоту ZFS или разобраться, что занимает место.

<details><summary>Условие</summary>

```promql
(cs2_demo_storage_total_bytes - cs2_demo_storage_used_bytes) / 1024^3 < 15
```

Держится: 15m · группа `product-cs2` · uid `cs2-demo-storage-low`

</details>

<a id="cs2-clip-storage-low"></a>

### Пристрелка: место под клипы кончается

**предупреждение** · порог: больше 0, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Заполнение квоты клипов](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=908)

**Что случилось.** Под клипы осталось меньше 4 ГБ: работник рендера встанет на двух

**Что это значит и что делать.** Клипы стираются сами через месяц без обращений, так что это либо всплеск заказов, либо сироты — каталоги без записи в реестре (панель «Клипы: занято» покажет расхождение). Ниже двух гигабайт заказы перестают браться, и у людей клип «готовится» бесконечно. Решать владельцу: расширить квоту ZFS датасета tank/cs2-clips или укоротить срок жизни CS2_RENDER_CLIP_TTL.

<details><summary>Условие</summary>

```promql
(cs2_clip_storage_total_bytes - cs2_clip_storage_used_bytes) / 1024^3 < 4 and cs2_clip_storage_total_bytes > 0
```

Держится: 15m · группа `product-cs2` · uid `cs2-clip-storage-low`

</details>

<a id="cs2-reconcile-parse-missing"></a>

### Пристрелка: много матчей без строк в ClickHouse

**предупреждение** · порог: больше 10, держится 1 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: сверка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1505)

**Что случилось.** Больше десяти матчей помечены разобранными, а строк у них нет

**Что это значит и что делать.** Сверка сама ставит их на разбор заново, но пока разбор не пройдёт, у людей пустые страницы матчей. Один-два — случайность, десяток — ClickHouse терял запись. Проверить, что повторные разборы проходят, и искать, куда делись строки.

<details><summary>Условие</summary>

```promql
cs2_reconcile_mismatches{kind="parse_missing"} > 10
```

Держится: 1h · группа `product-cs2` · uid `cs2-reconcile-parse-missing`

</details>

<a id="cs2-render-machine-space-low"></a>

### Пристрелка: на машине рендера кончается место

**предупреждение** · порог: меньше 10 ГиБ, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Место на машинах рендера](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=912)

**Что случилось.** На машине рендера меньше 10 ГиБ свободного места (машина — метка engine)

**Что это значит и что делать.** Ниже 8 ГиБ в каталоге клипов сборщик начнёт стирать клипы раньше срока, ниже 2 ГиБ где угодно машина перестанет брать задания, и клипов не получит никто. На cs2-win смотреть оба диска: Z: (клипы) и C: (дорожки, кэш демок). Это не квота датасета tank/cs2-clips — про неё отдельная тревога «место под клипы кончается».

<details><summary>Условие</summary>

```promql
cs2_render_clips_free_bytes < 10 * 1024^3
```

Держится: 15m · группа `product-cs2` · uid `cs2-render-machine-space-low`

</details>

<a id="cs2-render-disk-low"></a>

### Пристрелка: на машине рендера мало места

**предупреждение** · порог: меньше 10 ГиБ 10 минут · панель: [Пристрелка — cs.samoy.love → Место на машинах рендера](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=912)

**Что случилось.** На машине ‹engine› осталось меньше 10 ГиБ

**Что это значит и что делать.** Метрика берёт минимум по каталогам клипов, работы и кэша. Проверить конкретный диск, рабочие файлы и сроки хранения. Ниже 2 ГиБ новые задания не берутся; память машины не увеличивать.

<details><summary>Условие</summary>

```promql
cs2_render_clips_free_bytes < 10 * 1024^3
```

Держится: 10m · группа `product-cs2` · uid `cs2-render-disk-low`

</details>

<a id="cs2-container-units-unknown"></a>

### Пристрелка: не видно служб контейнера

**предупреждение** · порог: держится 15 мин · панель: [Пристрелка — cs.samoy.love → Службы в контейнерах cs2: упавшие](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1004)

**Что случилось.** Список служб контейнера не снимается дольше 15 минут

**Что это значит и что делать.** Пока так, тревога про упавшие службы молчит, даже если они упали. Либо контейнер остановлен или завис (метка container), либо встал сам сборщик: systemctl status incus-units-collect.timer на хосте.

<details><summary>Условие</summary>

```promql
(time() - incus_container_units_collect_timestamp_seconds > 300) or (incus_container_units_collect_ok == 0)
```

Держится: 15m · группа `product-cs2` · uid `cs2-container-units-unknown`

</details>

<a id="cs2-render-game-update-stuck"></a>

### Пристрелка: обновление игры на машине рендера не встало

**предупреждение** · порог: дольше 3 ч, держится 5 мин · панель: [Пристрелка — cs.samoy.love → Движок съёмки](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=911)

**Что случилось.** Steam ждёт поставить обновление CS2 на машине рендера (машина — метка engine)

**Что это значит и что делать.** Пока оно не встало, новые демки не читаются старой игрой, а новая HLAE, собранная под новую игру, её не поднимает. На cs2-win: мягко остановить работника (C:\cs2\stop-render.ps1), запустить CS2 через Steam разовой задачей в сеансе render (steam://run/730), дождаться, когда buildid в appmanifest_730.acf сравняется с TargetBuildID, погасить игру и запустить задачу cs2-render — проба при старте проверит движок. Если HLAE под новую игру ещё нет, проба упадёт, и заказы уйдут на Linux. На Linux — смотреть клиент Steam в cs2-render. Карточка машины в админке cs2 пишет, какая сборка ждёт.

<details><summary>Условие</summary>

```promql
cs2_render_game_update_seconds{engine="hlae"} > 1800 or cs2_render_game_update_seconds{engine="linux"} > 10800
```

Держится: 5m · группа `product-cs2` · uid `cs2-render-game-update-stuck`

</details>

<a id="cs2-pg-dump-absent"></a>

### Пристрелка: отметки дампа Postgres нет

**предупреждение** · порог: держится 2 сут · панель: [Пристрелка — cs.samoy.love → Резервные копии](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1501)

**Что случилось.** Сервис не видит ни одного удачного дампа Postgres

**Что это значит и что делать.** Похоже, резервной копии базы нет вовсе. Проверить, что таймер cs2-pgdump включён в контейнере cs2 и что скрипт пишет отметку в service_marks. Если лежит сам сайт, рядом горит «сайт не отвечает» — начинать с него.

<details><summary>Условие</summary>

```promql
absent(cs2_pg_dump_age_seconds)
```

Держится: 48h · группа `product-cs2` · uid `cs2-pg-dump-absent`

</details>

<a id="cs2-music-provider-down"></a>

### Пристрелка: провайдер музыки не отвечает

**предупреждение** · порог: не меньше 500%, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Музыка: доля отказов по провайдерам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1902)

**Что случилось.** Провайдер музыки ‹provider› отказывает больше чем в половине обращений

**Что это значит и что делать.** Вкладка этого провайдера в конструкторе роликов пуста, ролики с его треками не соберутся. У Яндекса обычно истёк вход или сменился API; у Jamendo — client_id. Причина словами провайдера — в журнале cs2-api.

<details><summary>Условие</summary>

```promql
sum by (provider) (increase(cs2_music_requests_total{result="отказ"}[1h])) / clamp_min(sum by (provider) (increase(cs2_music_requests_total{result!="кэш"}[1h])), 1) > 0.5 and sum by (provider) (increase(cs2_music_requests_total{result!="кэш"}[1h])) >= 5
```

Держится: 15m · группа `product-cs2` · uid `cs2-music-provider-down`

</details>

<a id="cs2-render-promo-late"></a>

### Пристрелка: промо не успевает к сводке неделю подряд

**предупреждение** · порог: не меньше 12000%, держится 1 ч · панель: [Пристрелка — cs.samoy.love → Промо успевает к сводке](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1604)

**Что случилось.** Неделю подряд больше 5% промо снимаются уже после сводки сессии

**Что это значит и что делать.** Опоздавшее промо в Telegram не уходит: человек получает сводку без ролика. Две машины не справляются с вечерним пиком — пора третья (КОНСТРУКТОР-РОЛИКОВ, «Мощность рендера»). Сначала глянуть «Ожидание по классам» и «Машины рендера: отметка»: если одна машина всю неделю молчала, дело не в мощности.

<details><summary>Условие</summary>

```promql
max_over_time((max(cs2_render_promo_day{state="in_time"}) / (sum(max by (state) (cs2_render_promo_day)) > 0))[7d:1h]) < 0.95 and count_over_time((sum(max by (state) (cs2_render_promo_day)) > 0)[7d:1h]) >= 120
```

Держится: 1h · группа `product-cs2` · uid `cs2-render-promo-late`

</details>

<a id="cs2-profiles-stale"></a>

### Пристрелка: профили Steam перестали обновляться

**предупреждение** · порог: больше 50, держится 6 ч · панель: [Пристрелка — cs.samoy.love → Профили устарели](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=504)

**Что случилось.** Больше полусотни профилей опоздали с обновлением больше чем на сутки

**Что это значит и что делать.** На страницах остаются старые ники и аватары — сервис показывает человека таким, каким он был вчера. Обычные причины две: ключ отозван или суточный потолок выеден другим сбором.

<details><summary>Условие</summary>

```promql
cs2_steam_profiles_stale > 50
```

Держится: 6h · группа `product-cs2` · uid `cs2-profiles-stale`

</details>

<a id="cs2-worker-panics"></a>

### Пристрелка: работник падает с паникой

**предупреждение** · порог: не меньше 2 · панель: [Пристрелка — cs.samoy.love → Падения работников](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=408)

**Что случилось.** Работник цепочки паникует

**Что это значит и что делать.** Работник ловит панику и перезапускается — задание, на котором он падает, не пройдёт никогда. Порог 2, а не 1: сумма счётчиков сайта и цепочки даёт ложный прирост при выкатке. Журнал cs2-chain, строка с паникой.

<details><summary>Условие</summary>

```promql
sum by (worker) (increase(cs2_worker_panics_total[30m])) >= 2
```

Держится: 0m · группа `product-cs2` · uid `cs2-worker-panics`

</details>

<a id="cs2-worker-disabled"></a>

### Пристрелка: работник цепочки выключен

**предупреждение** · порог: держится 30 мин · панель: [Пристрелка — cs.samoy.love → Кто из работников запущен](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=400)

**Что случилось.** Работник ‹worker› не запущен: нет настройки или ключа

**Что это значит и что делать.** Матчи перестают приходить сами, а страницы объясняют пустоту ОЖИДАНИЕМ — то есть врут: ждать нечего. 09.09.2026 живой игрок так ждал разбора, которого не случилось бы никогда. Проверить CS2_GC_URL, ключ Steam и список хостов скачивателя в /etc/cs2/api.env.

<details><summary>Условие</summary>

```promql
cs2_worker_enabled{worker=~"коды|сводки|скачивание"} == 0
```

Держится: 30m · группа `product-cs2` · uid `cs2-worker-disabled`

</details>

<a id="cs2-worker-silent"></a>

### Пристрелка: работник цепочки молчит

**предупреждение** · порог: держится 30 мин · панель: [Пристрелка — cs.samoy.love → Сколько молчит работник](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=401)

**Что случилось.** Работник ‹worker› шесть часов не сделал ни одного дела, хотя его ждут дела

**Что это значит и что делать.** Работник запущен, очередь у него непустая (cs2_worker_backlog), а следов работы в базе шесть часов нет: круг падает молча. Для игрока это затор в цепочке без единой ошибки в журнале. Тишина при пустой очереди — норма (никто не играл) и тревогой не считается: до 11.09.2026 правило этого не различало и горело весь вечер. Очередь при этом должна быть непустой все шесть часов: дела, появившиеся после тихой ночи, работник ещё не обязан был сделать (с 27.09.2026).

<details><summary>Условие</summary>

```promql
(time() - cs2_worker_last_success_timestamp_seconds > 21600) and on(worker) min_over_time(cs2_worker_backlog[6h]) > 0 unless on(worker) cs2_worker_enabled == 0
```

Держится: 30m · группа `product-cs2` · uid `cs2-worker-silent`

</details>

<a id="cs2-parse-slow"></a>

### Пристрелка: разбор идёт дольше двух минут

**предупреждение** · порог: не короче 5 с, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Время разбора по парсерам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=306)

**Что случилось.** p95 времени разбора перевалил за две минуты

**Что это значит и что делать.** Сервис обещает разбор «под минуту»: человек, приславший демку, за две минуты обычно уходит со страницы. Смотреть, кто из двух парсеров стал узким местом, и не мешает ли разбору пересчёт архива.

<details><summary>Условие</summary>

```promql
histogram_quantile(0.95, sum by (le) (rate(cs2_parse_duration_seconds_bucket[1h]))) > 120 and on() sum(increase(cs2_parse_duration_seconds_count[1h])) >= 5
```

Держится: 15m · группа `product-cs2` · uid `cs2-parse-slow`

</details>

<a id="cs2-parse-failures"></a>

### Пристрелка: разбор падает у каждого пятого матча

**предупреждение** · порог: не меньше 500%, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Разборы по исходу](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=307)

**Что случилось.** Больше 20% разборов кончаются ошибкой

**Что это значит и что делать.** Каждый пятый игрок вместо отчёта видит «разбор не удался». Отдельная и худшая причина — потеря синхронизации парсера с битовым потоком: такой матч не падает, а отдаёт правдоподобные, но неверные числа, поэтому расхождение считается отказом намеренно.

<details><summary>Условие</summary>

```promql
sum(increase(cs2_parse_total{result="failed"}[30m])) / clamp_min(sum(increase(cs2_parse_total[30m])), 0.0001) > 0.20 and sum(increase(cs2_parse_total[30m])) >= 5
```

Держится: 15m · группа `product-cs2` · uid `cs2-parse-failures`

</details>

<a id="cs2-reconcile-summary"></a>

### Пристрелка: разбор разошёлся со сводкой Valve

**предупреждение** · порог: больше 0, держится 1 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: сверка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1505)

**Что случилось.** Ночная сверка нашла матчи, где разбор не совпал со сводкой Valve

**Что это значит и что делать.** У людей на страницах матча не те убийства, смерти или счёт, что показывает сама игра. Обычная причина — обновление CS2 или свежая выкатка разбора. Первые двадцать расхождений (матч, номер GC, SteamID, два числа) — в журнале cs2-chain у recheck; сверить с демкой и чинить разбор, данные сами не правятся.

<details><summary>Условие</summary>

```promql
max(cs2_reconcile_mismatches{kind="summary"}) > 0
```

Держится: 1h · группа `product-cs2` · uid `cs2-reconcile-summary`

</details>

<a id="cs2-render-mode-mismatch"></a>

### Пристрелка: режим машины рендера не совпадает с сервисом

**предупреждение** · порог: держится 15 мин · панель: [Пристрелка — cs.samoy.love → Машины рендера: режим](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1602)

**Что случилось.** Режим машины рендера ‹engine› не совпадает с режимом сервиса

**Что это значит и что делать.** Сервис лабораторный, а машина — нет: ролики с неё выходят без лабораторных ассетов. Вреда людям нет, но решено было иначе. Поправить CS2_MODE в настройках машины и перезапустить работника.

<details><summary>Условие</summary>

```promql
cs2_render_mode_mismatch == 1 unless on() cs2_service_mode{mode="public"} == 1
```

Держится: 15m · группа `product-cs2` · uid `cs2-render-mode-mismatch`

</details>

<a id="cs2-render-oom"></a>

### Пристрелка: рендер убивают по памяти

**предупреждение** · порог: не меньше 3, держится 5 мин · панель: [Пристрелка — cs.samoy.love → cs2-render: убито по памяти](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1709)

**Что случилось.** В cs2-render за час убито по памяти три и больше процессов

**Что это значит и что делать.** Игру или ffmpeg рендера убивает OOM-killer: задания повторяются по кругу, клипы опаздывают. Одиночное убийство при тяжёлой демке — не повод будить. Смотреть память cs2-render и не идёт ли рядом стенд или повтор.

<details><summary>Условие</summary>

```promql
increase(incus_memory_OOM_kills_total{name="cs2-render"}[1h]) >= 3
```

Держится: 5m · группа `product-cs2` · uid `cs2-render-oom`

</details>

<a id="cs2-render-first-try-low"></a>

### Пристрелка: рендер часто не получается с первого раза

**предупреждение** · порог: меньше 90%, держится 1 сут · панель: [Пристрелка — cs.samoy.love → Рендер с первого раза](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=910)

**Что случилось.** Меньше 90% заданий рендера за неделю прошли с первой попытки (машина — метка engine)

**Что это значит и что делать.** Клипы в итоге доходят, но каждый повтор — лишние минуты, пока игрок ждёт. Какая причина выросла, видно в cs2_render_retries_by_requester_week по той же машине и классу заказов (панель «Рендер с первого раза: причины повторов»): перемотка, камера, падение игры, HLAE, диск, потолок времени (timeout). Частый повод — обновление CS2 или выкатка посреди задания.

<details><summary>Условие</summary>

```promql
cs2_render_first_try_by_requester_ratio{engine=~"linux|hlae",requester=~"user|system"} < 0.9
```

Держится: 24h · группа `product-cs2` · uid `cs2-render-first-try-low`

</details>

<a id="cs2-pg-connections"></a>

### Пристрелка: соединения Postgres на исходе

**предупреждение** · порог: больше 80%, держится 10 мин · панель: [Пристрелка — cs.samoy.love → Базы: соединения Postgres](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=2000)

**Что случилось.** Занято больше 80% соединений Postgres

**Что это значит и что делать.** Когда кончатся все, запросы сайта и цепочки начнут падать с ошибкой: страницы не откроются, разбор встанет. Смотреть pg_stat_activity: кто держит соединения и не утекают ли они.

<details><summary>Условие</summary>

```promql
cs2_postgres_connections{state="used"} / ignoring(state) cs2_postgres_connections{state="max"} > 0.8
```

Держится: 10m · группа `product-cs2` · uid `cs2-pg-connections`

</details>

<a id="cs2-page-slow"></a>

### Пристрелка: страница матча стала медленной

**предупреждение** · порог: дольше 3 с, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Время ответа, p95 по разделам](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=108)

**Что случилось.** p95 страницы матча перевалил за три секунды

**Что это значит и что делать.** Разбор считается по ClickHouse на лету, поэтому медленно здесь — это медленно у человека, открывшего свой матч. Смотреть запросы отчёта и объём архива, а не «сайт тормозит»: остальные разделы могут быть быстрыми.

<details><summary>Условие</summary>

```promql
histogram_quantile(0.95, sum by (le) (rate(cs2_http_request_duration_seconds_bucket{route="страница_матча"}[15m]))) > 3
```

Держится: 15m · группа `product-cs2` · uid `cs2-page-slow`

</details>

<a id="cs2-pages-slow"></a>

### Пристрелка: страницы сайта отвечают медленно

**предупреждение** · порог: дольше 0,05 с, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Время ответа страниц: p50, p95, p99](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=111)

**Что случилось.** 95-й перцентиль ответа страниц дольше двух секунд

**Что это значит и что делать.** Сайт открывается медленно у всех. Отдача роликов и звука (раздел «медиа»), статика и служебные ручки не в счёте — это время просмотра, а не сервера. Какой раздел — «Время ответа, p95 по разделам»; чаще всего ClickHouse под нагрузкой разбора.

<details><summary>Условие</summary>

```promql
histogram_quantile(0.95, sum by (le) (rate(cs2_http_request_duration_seconds_bucket{route!~"статика|служебные|медиа"}[15m]))) > 2 and on() sum(rate(cs2_http_requests_total{route!~"статика|служебные|медиа"}[15m])) > 0.05
```

Держится: 15m · группа `product-cs2` · uid `cs2-pages-slow`

</details>

<a id="cs2-steam-quota"></a>

### Пристрелка: суточный потолок Steam почти выеден

**предупреждение** · порог: больше 80%, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Ключ Steam: доля потолка](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=510)

**Что случилось.** За сутки израсходовано больше 80% из 100 000 вызовов ключа

**Что это значит и что делать.** Упереться в потолок значит остановить У ВСЕХ и историю матчей, и профили, а выглядеть это будет как отказ Steam. Пятиминутный обход историй стоит 288 вызовов в сутки на игрока: примерно на трёхстах сорока игроках ключ выедается целиком, и обход обязан стать разным для активных и спящих.

<details><summary>Условие</summary>

```promql
max(cs2_budget_used{resource="steam_key",window="сутки"}) / clamp_min(max(cs2_external_limit{limit="steam_вызовов_в_сутки"}), 1) > 0.8
```

Держится: 15m · группа `product-cs2` · uid `cs2-steam-quota`

</details>

<a id="cs2-parse-deleting-stuck"></a>

### Пристрелка: удаление матча застряло

**предупреждение** · порог: больше 0, держится 2 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: удаления](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1504)

**Что случилось.** Удаление матча оборвалось и не доделано

**Что это значит и что делать.** Данные, которые человек просил стереть, всё ещё лежат. Подметальщик не справился за час: смотреть журнал cs2-chain (recheck) и доделывать руками.

<details><summary>Условие</summary>

```promql
cs2_parse_deleting_stuck > 0
```

Держится: 2h · группа `product-cs2` · uid `cs2-parse-deleting-stuck`

</details>

<a id="cs2-parse-failed-seen"></a>

### Пристрелка: упавшие разборы спрятали матчи

**предупреждение** · порог: больше 0, держится 6 ч · панель: [Пристрелка — cs.samoy.love → Сохранность: спрятанные матчи](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=1503)

**Что случилось.** Есть упавшие разборы уже виденных матчей

**Что это значит и что делать.** Человек этот матч уже видел, а теперь он пропал со страниц: перезапись стёрла старые строки и не записала новые. Сам матч не вернётся, пока разбор не пройдёт. Причину искать в parse_jobs.error у упавших заданий.

<details><summary>Условие</summary>

```promql
cs2_parse_failed_seen > 0
```

Держится: 6h · группа `product-cs2` · uid `cs2-parse-failed-seen`

</details>

<a id="cs2-worker-mark-silent"></a>

### Пристрелка: фоновый работник молчит

**предупреждение** · порог: держится 15 мин · панель: [Пристрелка — cs.samoy.love → Сколько молчит работник](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=401)

**Что случилось.** Работник ‹worker› давно не отметил ни одного удачного круга

**Что это значит и что делать.** Сайт отвечает, но данные этого работника перестали свежеть: блокировки, уровни и профили — наблюдения о встреченных и профили игроков; faceit — ELO на профилях; друзья — матчи через бота в друзьях приходят только кругом кодов, с опозданием; пересчёт — старые числа на страницах после смены разбора; аватары — кэш аватаров растёт без уборки. Смотреть журнал cs2-chain (у аватаров — cs2-api) по имени работника: круг падает молча или обрывается отказом чужой стороны.

<details><summary>Условие</summary>

```promql
( (time() - max by (worker) (cs2_worker_last_success_timestamp_seconds{worker=~"блокировки|уровни|профили"}) > 10800) and on() (max(cs2_worker_enabled{worker="профили"}) == 1) ) or ( (time() - max by (worker) (cs2_worker_last_success_timestamp_seconds{worker="faceit"}) > 7200) and on(worker) (max by (worker) (cs2_worker_enabled{worker="faceit"}) == 1) ) or ( (time() - max by (worker) (cs2_worker_last_success_timestamp_seconds{worker="друзья"}) > 900) and on(worker) (max by (worker) (cs2_worker_enabled{worker="друзья"}) == 1) ) or ( (time() - max by (worker) (cs2_worker_last_success_timestamp_seconds{worker="пересчёт"}) > 3600) unless on(worker) (max by (worker) (cs2_worker_enabled{worker="пересчёт"}) == 0) ) or (time() - max by (worker) (cs2_worker_last_success_timestamp_seconds{worker="аватары"}) > 180000)
```

Держится: 15m · группа `product-cs2` · uid `cs2-worker-mark-silent`

</details>

<a id="cs2-storage-warn"></a>

### Пристрелка: хранилище демок заполняется

**предупреждение** · порог: больше 70%, держится 30 мин · панель: [Пристрелка — cs.samoy.love → Заполнение квоты](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=701)

**Что случилось.** Занято больше 70% квоты хранилища демок

**Что это значит и что делать.** Ретеншна нет намеренно: демки хранятся целиком, и место когда-нибудь кончится. Знать об этом надо заранее — расширить квоту или заняться оптимизацией хранения, — а не в тот день, когда приём встанет.

<details><summary>Условие</summary>

```promql
cs2_demo_storage_used_bytes / cs2_demo_storage_total_bytes > 0.70
```

Держится: 30m · группа `product-cs2` · uid `cs2-storage-warn`

</details>

<a id="cs2-chain-stalled"></a>

### Пристрелка: цепочка встала

**предупреждение** · порог: держится 10 мин · панель: [Пристрелка — cs.samoy.love → Очереди цепочки](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=206)

**Что случилось.** Коды матчей ждут счёта, а новых сводок за час не прибавилось

**Что это значит и что делать.** Работа приходит и не уходит: у игроков матчи стоят на первой стадии. Ничего при этом не падает — сайт отвечает двухсотыми, ошибок в журнале нет. Ровно так поломку цепочки однажды нашёл живой игрок, а не проверка.

<details><summary>Условие</summary>

```promql
min_over_time(cs2_chain_codes_awaiting_summary[1h]) > 0 and increase(cs2_chain_summaries[1h]) == 0
```

Держится: 10m · группа `product-cs2` · uid `cs2-chain-stalled`

</details>

<a id="cs2-chain-scrape-down"></a>

### Пристрелка: цепочка не отвечает на сбор

**предупреждение** · порог: меньше 50%, держится 15 мин · панель: [Пристрелка — cs.samoy.love → Цепочка отвечает на сбор](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=407)

**Что случилось.** Сайт не может снять метрики процесса цепочки

**Что это значит и что делать.** Числа работников на дашборде становятся нулями сайта, и часть тревог про цепочку врёт. Проверить, жив ли cs2-chain и отвечает ли его порт метрик.

<details><summary>Условие</summary>

```promql
avg_over_time(cs2_chain_scrape_up[15m]) < 0.5
```

Держится: 15m · группа `product-cs2` · uid `cs2-chain-scrape-down`

</details>

<a id="cs2-render-hlae-update"></a>

### Пристрелка: вышла новая версия HLAE

**для сведения** · порог: держится 1 ч · панель: [Пристрелка — cs.samoy.love → Движок съёмки](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=911)

**Что случилось.** Вышла HLAE новее той, что стоит на машине рендера

**Что это значит и что делать.** Само по себе это не поломка: пока движок исправен, обновление можно отложить. Срочно — только вместе с тревогой «движок съёмки сломан»: тогда новая версия, скорее всего, и есть починка после обновления CS2. Ставить на cs2-win и прогонять стенд.

<details><summary>Условие</summary>

```promql
cs2_render_engine_update == 1
```

Держится: 1h · группа `product-cs2` · uid `cs2-render-hlae-update`

</details>

<a id="cs2-demo-storage-forecast"></a>

### Пристрелка: места под демки хватит меньше чем на две недели

**для сведения** · порог: держится 1 ч · панель: [Пристрелка — cs.samoy.love → Квоты демок хватит на](https://metrics.samoy.love/d/samoylove-cs2?viewPanel=705)

**Что случилось.** При нынешнем темпе места под демки хватит меньше чем на две недели

**Что это значит и что делать.** Наклон взят по последним трём дням (без всплесков короче двух часов) и продолжен на две недели — это повод посмотреть, а не тревога: неделя активной игры задирает темп, а неделя без игры его обнуляет. Настоящий остаток — в правиле «место под демки кончается».

<details><summary>Условие</summary>

```promql
predict_linear(min_over_time(cs2_demo_storage_used_bytes[2h])[3d:10m], 14*24*3600) > cs2_demo_storage_total_bytes - 10 * 1024^3
```

Держится: 1h · группа `product-cs2` · uid `cs2-demo-storage-forecast`

</details>

<a id="sites-area"></a>

## Сайты и проекты

<a id="product-snakes-profiles-read-only"></a>

### Змейки: профили только на чтение

**авария** · порог: держится 5 мин · панель: [Snakes — игра → Профили только на чтение](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=27)

**Что случилось.** Хранилище профилей только на чтение — прогресс игроков не переживёт перезапуск

<details><summary>Условие</summary>

```promql
snakes_profiles_read_only == 1
```

Держится: 5m · группа `product-snakes` · uid `product-snakes-profiles-read-only`

</details>

<a id="product-install-failure-rate-high"></a>

### Лаунчер: больше 40% установок не завершились

**авария** · порог: не меньше 500%, держится 30 мин · панель: [ChillHub — лаунчер → Доля неуспешных установок](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=39)

**Что случилось.** Больше 40% установок за час не завершились

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_game_installs_total{result!="ok"}[1h])) / clamp_min(sum(increase(chillhub_game_installs_total[1h])), 1) > 0.4 and sum(increase(chillhub_game_installs_total[1h])) >= 5
```

Держится: 30m · группа `product-chillhub` · uid `product-install-failure-rate-high`

</details>

<a id="product-launcher-error-rate-high"></a>

### Лаунчер: больше 5% ответов — пятисотки

**авария** · порог: больше 5%, держится 10 мин · панель: [ChillHub — лаунчер → Доля 5xx лаунчера (API и админка)](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=41)

**Что случилось.** Больше 5% ответов лаунчера с кодом 5xx

<details><summary>Условие</summary>

```promql
sum(rate(chillhub_http_requests_total{code=~"5.."}[15m])) / clamp_min(sum(rate(chillhub_http_requests_total[15m])), 0.001) > 0.05
```

Держится: 10m · группа `product-chillhub` · uid `product-launcher-error-rate-high`

</details>

<a id="product-site-error-rate-high"></a>

### Сайты: больше 5% ответов — пятисотки

**авария** · порог: больше 2000%, держится 10 мин · панель: [Сайты samoy.love — сводка → Доля 5xx по сайтам](https://metrics.samoy.love/d/samoylove-overview?viewPanel=10)

**Что случилось.** ‹host›: больше 5% ответов с кодом 5xx

**Что это значит и что делать.** Страницы у людей не открываются. Какой раздел — «Запросы по разделам» на дашборде сайта; у cs.samoy.love — «Ошибки по разделам» Пристрелки.

<details><summary>Условие</summary>

```promql
sum by (host) (rate(samoylove_site_http_response_count_total{status=~"5.."}[15m])) / sum by (host) (rate(samoylove_site_http_response_count_total[15m])) > 0.05 and sum by (host) (increase(samoylove_site_http_response_count_total[15m])) > 20
```

Держится: 10m · группа `product-sites` · uid `product-site-error-rate-high`

</details>

<a id="infra-status-check-down"></a>

### Сайты: проверка статус-страницы красная

**авария** · порог: держится 5 мин · панель: [Статус — страница, агент и бот → Проверки по проектам](https://metrics.samoy.love/d/samoylove-status?viewPanel=12)

**Что случилось.** ‹project› / ‹name›: проверка не проходит

**Что это значит и что делать.** Это то же, что видят люди на status.samoy.love. Подробности — на дашборде «Статус».

<details><summary>Условие</summary>

```promql
status_check_up == 0
```

Держится: 5m · группа `infra-sites` · uid `infra-status-check-down`

</details>

<a id="infra-site-down"></a>

### Сайты: сайт не открывается

**авария** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Доступность сайтов (проба)](https://metrics.samoy.love/d/samoylove-overview?viewPanel=28)

**Что случилось.** ‹instance› не отвечает на внешнюю пробу

**Что это значит и что делать.** Людям сайт недоступен. Если лежат все сайты разом — nginx, сеть или DNS; если один — его служба.

<details><summary>Условие</summary>

```promql
probe_success == 0
```

Держится: 5m · группа `infra-sites` · uid `infra-site-down`

</details>

<a id="infra-service-down"></a>

### Сайты: служба в контейнере web не работает

**авария** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Службы (systemd)](https://metrics.samoy.love/d/samoylove-overview?viewPanel=25)

**Что случилось.** Служба ‹name› не active

**Что это значит и что делать.** nginx и docker держат все сайты; snakes и chillhub — свои проекты. systemctl status внутри web.

<details><summary>Условие</summary>

```promql
node_systemd_unit_state{job!="node-containers",name=~"(snakes|chillhub-api|chillhub-admin|nginx|docker)\\.service",state="active"} == 0
```

Держится: 5m · группа `infra-services` · uid `infra-service-down`

</details>

<a id="infra-deploy-event-delivery-stuck"></a>

### Сайты: события выкатки не доходят до Telegram

**авария** · порог: дольше 5 мин, держится 1 мин · панель: [Статус — страница, агент и бот → События выкатки](https://metrics.samoy.love/d/samoylove-status?viewPanel=43)

**Что случилось.** Событие выкатки ждёт в очереди больше 5 минут

**Что это значит и что делать.** Сообщения о релизах не уходят в чат. Смотреть статус-бота на дашборде «Статус».

<details><summary>Условие</summary>

```promql
statusbot_deploy_events_pending_age_seconds > 300
```

Держится: 1m · группа `infra-deploy-events` · uid `infra-deploy-event-delivery-stuck`

</details>

<a id="infra-unit-failed"></a>

### Сайты: юнит в контейнере web упал

**авария** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Службы (systemd)](https://metrics.samoy.love/d/samoylove-overview?viewPanel=25)

**Что случилось.** Юнит ‹name› в состоянии failed

**Что это значит и что делать.** Разовая задача (резервная копия, агент) закончилась ошибкой. journalctl -u внутри web.

<details><summary>Условие</summary>

```promql
node_systemd_unit_state{job!="node-containers",state="failed"} == 1
```

Держится: 5m · группа `infra-services` · uid `infra-unit-failed`

</details>

<a id="product-status-agent-stale"></a>

### Статус: агент проверок молчит

**авария** · порог: дольше 10 мин, держится 5 мин · панель: [Статус — страница, агент и бот → Последний прогон](https://metrics.samoy.love/d/samoylove-status?viewPanel=8)

**Что случилось.** Агент статус-страницы не проверял сервисы больше 10 минут

<details><summary>Условие</summary>

```promql
time() - status_agent_run_timestamp_seconds > 600
```

Держится: 5m · группа `product-status` · uid `product-status-agent-stale`

</details>

<a id="product-status-bot-stale"></a>

### Статус: бот Telegram молчит

**авария** · порог: дольше 10 мин, держится 5 мин · панель: [Статус — страница, агент и бот → Сердцебиение](https://metrics.samoy.love/d/samoylove-status?viewPanel=17)

**Что случилось.** Бот статус-страницы не обновлял метрики больше 10 минут

<details><summary>Условие</summary>

```promql
time() - statusbot_heartbeat_timestamp_seconds > 600
```

Держится: 5m · группа `product-status` · uid `product-status-bot-stale`

</details>

<a id="product-telegram-delivery-failing"></a>

### Статус: бот не может отправлять сообщения

**авария** · порог: больше 3, держится 15 мин · панель: [Статус — страница, агент и бот → Ошибок отправки за сутки](https://metrics.samoy.love/d/samoylove-status?viewPanel=18)

**Что случилось.** Бот статуса не отправляет сообщения: уведомления об инцидентах не придут

<details><summary>Условие</summary>

```promql
increase(statusbot_send_failures_total[1h]) > 3
```

Держится: 15m · группа `product-status` · uid `product-telegram-delivery-failing`

</details>

<a id="product-snakes-tick-slow"></a>

### Змейки: игровой тик медленный

**предупреждение** · порог: дольше 0,1 с, держится 10 мин · панель: [Snakes — игра → Тик, p95](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=25)

**Что случилось.** Игровой тик медленнее нормы — игра дёргается

<details><summary>Условие</summary>

```promql
histogram_quantile(0.95, sum(rate(snakes_tick_duration_seconds_bucket[10m])) by (le)) > 0.1
```

Держится: 10m · группа `product-snakes` · uid `product-snakes-tick-slow`

</details>

<a id="product-snakes-matches-stalled"></a>

### Змейки: матчи идут, но не заканчиваются

**предупреждение** · панель: [Snakes — игра → Матчи](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=8)

**Что случилось.** Матчи идут, но ни один не закончился за 15 минут — комната зависла

**Что это значит и что делать.** Матч идёт по таймеру 5 минут; если матч «идёт» 15 минут и ни один не закончился — комната зависла.

<details><summary>Условие</summary>

```promql
sum(snakes_matches_running) > 0 and on() sum(increase(snakes_matches_total[15m])) == 0
```

Держится: 0m · группа `product-snakes` · uid `product-snakes-matches-stalled`

</details>

<a id="product-snakes-ws-errors-high"></a>

### Змейки: много ошибок WebSocket

**предупреждение** · порог: больше 10, держится 10 мин · панель: [Snakes — игра → Потери и отказы](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=23)

**Что случилось.** Много ошибок WebSocket у игроков

<details><summary>Условие</summary>

```promql
60 * ( sum(rate(snakes_ws_dropped_messages_total[10m])) + sum(rate(snakes_ws_write_errors_total[10m])) + sum(rate(snakes_ws_handshake_rejected_total[10m])) ) > 10
```

Держится: 10m · группа `product-snakes` · uid `product-snakes-ws-errors-high`

</details>

<a id="product-snakes-ws-panic"></a>

### Змейки: паника в обработчике WebSocket

**предупреждение** · порог: больше 0 · панель: [Snakes — игра → Потери и отказы](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=23)

**Что случилось.** Обработчик WebSocket падал с паникой

**Что это значит и что делать.** Паника в обработчике соединения — ошибка в коде, а не нагрузка. Журнал snakes.service.

<details><summary>Условие</summary>

```promql
sum(increase(snakes_ws_closed_total{reason="panic"}[10m])) > 0
```

Держится: 0m · группа `product-snakes` · uid `product-snakes-ws-panic`

</details>

<a id="product-snakes-profile-saves-failing"></a>

### Змейки: профили не сохраняются

**предупреждение** · порог: больше 0, держится 15 мин · панель: [Snakes — игра → Ошибки сохранения за сутки](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=28)

**Что случилось.** Змейки не могут записать profiles.json — прогресс теряется

<details><summary>Условие</summary>

```promql
increase(snakes_profiles_save_errors_total[30m]) > 0
```

Держится: 15m · группа `product-snakes` · uid `product-snakes-profile-saves-failing`

</details>

<a id="product-snakes-ws-abnormal-closes"></a>

### Змейки: соединения рвутся

**предупреждение** · порог: больше 1, держится 10 мин · панель: [Snakes — игра → Подключения и разрывы](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=22)

**Что случилось.** Соединения WebSocket закрываются аварийно

**Что это значит и что делать.** Соединения игроков рвутся по нашей вине (паника, ошибка записи, переполнение очереди отправки) чаще раза в минуту.

<details><summary>Условие</summary>

```promql
sum(rate(snakes_ws_closed_total{reason=~"panic|write_error|send_backpressure"}[10m])) * 60 > 1
```

Держится: 10m · группа `product-snakes` · uid `product-snakes-ws-abnormal-closes`

</details>

<a id="product-snakes-tick-rate-low"></a>

### Змейки: тиков в секунду мало

**предупреждение** · порог: больше 0, держится 10 мин · панель: [Snakes — игра → Тиков в секунду на комнату](https://metrics.samoy.love/d/samoylove-snakes?viewPanel=38)

**Что случилось.** Комнаты тикают реже нормы

**Что это значит и что делать.** Сервер пропускает тики: игра идёт медленнее реального времени. «Змейки: игровой тик медленный» смотрит только на длительность тика и может молчать.

<details><summary>Условие</summary>

```promql
sum(rate(snakes_tick_duration_seconds_count[5m])) / sum(avg_over_time(snakes_rooms[5m])) < 9 and on() sum(avg_over_time(snakes_rooms[5m])) > 0
```

Держится: 10m · группа `product-snakes` · uid `product-snakes-tick-rate-low`

</details>

<a id="product-chillhub-admin-error-rate-high"></a>

### Лаунчер: админка отвечает ошибками

**предупреждение** · порог: больше 20%, держится 15 мин · панель: [ChillHub — лаунчер → Доля ошибок админки](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=42)

**Что случилось.** Больше 20% ответов админки с кодом 5xx

<details><summary>Условие</summary>

```promql
100 * sum(rate(chillhub_http_requests_total{service="admin",code=~"5.."}[15m])) / clamp_min(sum(rate(chillhub_http_requests_total{service="admin"}[15m])), 0.001) > 20
```

Держится: 15m · группа `product-chillhub` · uid `product-chillhub-admin-error-rate-high`

</details>

<a id="product-diff-updates-not-working"></a>

### Лаунчер: обновления качаются целиком

**предупреждение** · порог: не меньше 500%, держится 1 ч · панель: [ChillHub — лаунчер → Доля обновлений целиком (без диффа)](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=40)

**Что случилось.** Больше 80% обновлений скачали сборку целиком — дифф не работает

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_game_updates_total{result="ok",mode="full"}[6h])) / clamp_min(sum(increase(chillhub_game_updates_total{result="ok"}[6h])), 1) > 0.8 and sum(increase(chillhub_game_updates_total{result="ok"}[6h])) >= 5
```

Держится: 1h · группа `product-chillhub` · uid `product-diff-updates-not-working`

</details>

<a id="product-chillhub-admin-login-failures"></a>

### Лаунчер: подбирают пароль админки

**предупреждение** · порог: больше 10 · панель: [ChillHub — лаунчер → Входы в админку за сутки](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=22)

**Что случилось.** Больше 10 неудачных входов в админку за час

**Что это значит и что делать.** Похоже на подбор пароля к админке лаунчера.

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_admin_logins_total{result="fail"}[1h])) > 10
```

Держится: 0m · группа `product-chillhub` · uid `product-chillhub-admin-login-failures`

</details>

<a id="product-telemetry-junk-flood"></a>

### Лаунчер: поток мусорной телеметрии

**предупреждение** · порог: больше 500, держится 30 мин · панель: [ChillHub — лаунчер → Отвергнуто по причине за час](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=999)

**Что случилось.** Больше 500 отчётов с неизвестной игрой за час

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_telemetry_rejected_total{reason="unknown_game"}[1h])) > 500
```

Держится: 30m · группа `product-chillhub` · uid `product-telemetry-junk-flood`

</details>

<a id="product-chillhub-integrity-check-failed"></a>

### Лаунчер: проверка целостности не прошла

**предупреждение** · порог: больше 0 · панель: [ChillHub — лаунчер → Неудачных проверок целостности за сутки](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=18)

**Что случилось.** Проверка целостности лаунчера не прошла

**Что это значит и что делать.** У игрока файлы игры разошлись с манифестом.

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_integrity_checks_total{result!="ok"}[1h])) > 0
```

Держится: 0m · группа `product-chillhub` · uid `product-chillhub-integrity-check-failed`

</details>

<a id="product-maintenance-mode-stuck"></a>

### Лаунчер: режим обслуживания включён дольше получаса

**предупреждение** · порог: держится 30 мин · панель: [ChillHub — лаунчер → Режим обслуживания](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=6)

**Что случилось.** Публичный API полчаса отдаёт заглушку техработ

<details><summary>Условие</summary>

```promql
max(chillhub_maintenance_enabled) == 1
```

Держится: 30m · группа `product-chillhub` · uid `product-maintenance-mode-stuck`

</details>

<a id="product-chillhub-telemetry-rate-limited"></a>

### Лаунчер: телеметрию режет ограничитель

**предупреждение** · порог: больше 20, держится 30 мин · панель: [ChillHub — лаунчер → Ответы приёма телеметрии по кодам за час](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=56)

**Что случилось.** Приём телеметрии отвечает 429

**Что это значит и что делать.** Ограничитель частоты отбрасывает телеметрию лаунчеров (429). «Лаунчер: телеметрия отвергается» этого не видит: 429 не попадает в chillhub_telemetry_rejected_total.

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_http_requests_total{route="/metrics/report",code="429"}[1h])) > 20
```

Держится: 30m · группа `product-chillhub` · uid `product-chillhub-telemetry-rate-limited`

</details>

<a id="product-telemetry-rejected"></a>

### Лаунчер: телеметрия отвергается

**предупреждение** · порог: больше 20, держится 30 мин · панель: [ChillHub — лаунчер → Отвергнуто по причине за час](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=999)

**Что случилось.** Больше 20 отвергнутых отчётов телеметрии за час

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_telemetry_rejected_total{reason!="unknown_game"}[1h])) > 20
```

Держится: 30m · группа `product-chillhub` · uid `product-telemetry-rejected`

</details>

<a id="product-chillhub-client-errors-high"></a>

### Лаунчер: у клиентов много ошибок

**предупреждение** · порог: больше 20, держится 15 мин · панель: [ChillHub — лаунчер → Отказы у клиентов за час](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=36)

**Что случилось.** Больше 20 ошибок у клиентов лаунчера за час

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_client_errors_total[1h])) > 20
```

Держится: 15m · группа `product-chillhub` · uid `product-chillhub-client-errors-high`

</details>

<a id="product-hash-mismatches-high"></a>

### Лаунчер: файлы не сходятся с манифестом

**предупреждение** · порог: больше 10, держится 15 мин · панель: [ChillHub — лаунчер → Отказы у клиентов за час](https://metrics.samoy.love/d/samoylove-chillhub?viewPanel=36)

**Что случилось.** Больше десяти файлов за час не совпали с манифестом

<details><summary>Условие</summary>

```promql
sum(increase(chillhub_hash_mismatches_total[1h])) > 10
```

Держится: 15m · группа `product-chillhub` · uid `product-hash-mismatches-high`

</details>

<a id="product-site-latency-high"></a>

### Сайты: nginx отвечает медленно

**предупреждение** · порог: дольше 1 с, держится 15 мин · панель: [Сайты samoy.love — сводка → Время ответа сайтов, p95](https://metrics.samoy.love/d/samoylove-overview?viewPanel=33)

**Что случилось.** ‹host›: 95-й перцентиль ответа nginx дольше секунды

**Что это значит и что делать.** Страницы открываются медленно. У cs.samoy.love своя, точнее, тревога по разделам сайта — здесь его нет: отдача роликов и звука делала ему p95 секундами (38 ложных срабатываний за две недели сентября).

<details><summary>Условие</summary>

```promql
histogram_quantile(0.95, sum by (le, host) (rate(samoylove_site_http_response_time_seconds_hist_bucket{host!="cs.samoy.love",path!~"/downloads/|/content/|/clips/video/|/admin/vnc/"}[15m]))) > 1
```

Держится: 15m · группа `product-sites` · uid `product-site-latency-high`

</details>

<a id="product-access-log-parse-failing"></a>

### Сайты: журнал nginx не разбирается

**предупреждение** · порог: больше 0, держится 30 мин · панель: [Сайты samoy.love — сводка → Ошибки разбора журнала nginx](https://metrics.samoy.love/d/samoylove-overview?viewPanel=34)

**Что случилось.** Строки журнала nginx не разбираются экспортёром

**Что это значит и что делать.** log_format nginx и формат экспортёра разошлись: посещаемость и пятисотки по сайтам перестали считаться.

<details><summary>Условие</summary>

```promql
increase(samoylove_site_parse_errors_total[30m]) > 0
```

Держится: 30m · группа `product-sites` · uid `product-access-log-parse-failing`

</details>

<a id="product-traffic-collapse"></a>

### Сайты: посещаемость упала впятеро

**предупреждение** · порог: держится 2 ч · панель: [Сайты samoy.love — сводка → Посещаемость: сейчас против недели назад](https://metrics.samoy.love/d/samoylove-overview?viewPanel=32)

**Что случилось.** ‹host›: заходов на главную впятеро меньше, чем неделю назад

**Что это значит и что делать.** Сравнение идёт с тем же окном неделю назад. С 20.09.2026 журнал посещаемости не считает наши собственные проверки — проба blackbox и агент статус-страницы давали у тихих сайтов почти весь трафик главной. Неделю после этой правки сравнивать не с чем: прошлая неделя ещё с пробами, и любое окно выглядит падением в тридцать раз. Отсюда условие на время в выражении: правило молчит до 29.09.2026, когда в сравнение попадёт неделя чистых данных. После этой даты условие убрать.

<details><summary>Условие</summary>

```promql
sum by (host) (increase(samoylove_site_http_response_count_total{path="/"}[6h])) < 0.2 * sum by (host) (increase(samoylove_site_http_response_count_total{path="/"}[6h] offset 1w)) and sum by (host) (increase(samoylove_site_http_response_count_total{path="/"}[6h] offset 1w)) > 50 and on() (vector(time()) > 1790640000)
```

Держится: 2h · группа `product-sites` · uid `product-traffic-collapse`

</details>

<a id="product-event-receiver-errors"></a>

### Сайты: приёмник событий отвечает не 204

**предупреждение** · порог: больше 0 · панель: [Визитка — samoy.love → Ответы приёмника](https://metrics.samoy.love/d/samoylove-site?viewPanel=24)

**Что случилось.** Приёмник событий интерфейса ответил не 204

**Что это значит и что делать.** Приёмник событий сайтов обязан отвечать только 204; любой другой код — потерянные события.

<details><summary>Условие</summary>

```promql
sum(increase(samoylove_event_http_response_count_total{status!="204"}[1h])) > 0
```

Держится: 0m · группа `product-sites` · uid `product-event-receiver-errors`

</details>

<a id="product-probe-disagrees-with-agent"></a>

### Сайты: проба и агент статуса расходятся

**предупреждение** · порог: держится 30 мин · панель: [Сайты samoy.love — сводка → Доступность сайтов (проба)](https://metrics.samoy.love/d/samoylove-overview?viewPanel=28)

**Что случилось.** Внешняя проба падает, а агент статуса видит сайт живым

**Что это значит и что делать.** Сломан маршрут самой пробы, а не сайт: так 12–19.09.2026 «Сайты: сайт не открывается» неделю горел critical при живых сайтах (DNS пробы). Смотреть blackbox-exporter и резолв внутри стека мониторинга.

<details><summary>Условие</summary>

```promql
(probe_success{instance="https://samoy.love/"} == 0 and on() max(status_check_up{check="samoylove"}) == 1) or (probe_success{instance="https://metro.samoy.love/"} == 0 and on() max(status_check_up{check="metro"}) == 1) or (probe_success{instance="https://launcher.samoy.love/"} == 0 and on() max(status_check_up{check="launcher"}) == 1) or (probe_success{instance="https://snakes.samoy.love/"} == 0 and on() max(status_check_up{check="snakes"}) == 1) or (probe_success{instance="https://status.samoy.love/"} == 0 and on() max(status_check_up{check="status-page"}) == 1) or (probe_success{instance="https://die.samoy.love/"} == 0 and on() max(status_check_up{check="die"}) == 1) or (probe_success{instance="https://cs.samoy.love/"} == 0 and on() max(status_check_up{check="cs2-health"}) == 1)
```

Держится: 30m · группа `product-sites` · uid `product-probe-disagrees-with-agent`

</details>

<a id="infra-probe-latency-high"></a>

### Сайты: сайт отвечает медленно

**предупреждение** · порог: держится 15 мин · панель: [Сайты samoy.love — сводка → Время внешней пробы](https://metrics.samoy.love/d/samoylove-overview?viewPanel=30)

**Что случилось.** ‹instance› отвечает на внешнюю пробу дольше 3 секунд

**Что это значит и что делать.** Сайт открывается, но медленно. Лежащий сайт сюда не попадает: для него есть «Сайты: сайт не открывается».

<details><summary>Условие</summary>

```promql
probe_duration_seconds > 3 and on(instance) probe_success == 1
```

Держится: 15m · группа `infra-sites` · uid `infra-probe-latency-high`

</details>

<a id="infra-certificate-expiring-soon"></a>

### Сайты: сертификат истекает

**предупреждение** · порог: меньше 14, держится 1 ч · панель: [Сайты samoy.love — сводка → Сертификаты: дней до истечения (проба)](https://metrics.samoy.love/d/samoylove-overview?viewPanel=29)

**Что случилось.** Сертификат ‹instance› истекает меньше чем через 14 дней

**Что это значит и что делать.** certbot не продлил сертификат. sudo certbot renew --dry-run в web.

<details><summary>Условие</summary>

```promql
(probe_ssl_earliest_cert_expiry - time()) / 86400 < 14
```

Держится: 1h · группа `infra-sites` · uid `infra-certificate-expiring-soon`

</details>

<a id="infra-deploy-event-metrics-missing"></a>

### Сайты: у бота нет счётчиков выкатки

**предупреждение** · порог: держится 15 мин · панель: [Статус — страница, агент и бот → События выкатки](https://metrics.samoy.love/d/samoylove-status?viewPanel=43)

**Что случилось.** Метрики бота не содержат счётчиков выкатки

**Что это значит и что делать.** Путь событий выкатки не наблюдается: доставку релизов проверить нечем.

<details><summary>Условие</summary>

```promql
absent(statusbot_deploy_events_pending_age_seconds)
```

Держится: 15m · группа `infra-deploy-events` · uid `infra-deploy-event-metrics-missing`

</details>

<a id="product-status-bot-restart-loop"></a>

### Статус: бот перезапускается по кругу

**предупреждение** · порог: больше 3 · панель: [Статус — страница, агент и бот → Без перезапуска](https://metrics.samoy.love/d/samoylove-status?viewPanel=40)

**Что случилось.** Бот статуса перезапускался больше трёх раз за час

**Что это значит и что делать.** Процесс бота перезапускается по кругу: systemd поднимает его, он падает. Журнал samoylove-bot.

<details><summary>Условие</summary>

```promql
changes(statusbot_start_timestamp_seconds[1h]) > 3
```

Держится: 0m · группа `product-status` · uid `product-status-bot-restart-loop`

</details>

<a id="product-status-cert-renewal-missed"></a>

### Статус: сертификат не продлён вовремя

**предупреждение** · порог: меньше 25, держится 6 ч · панель: [Статус — страница, агент и бот → Дни до истечения сертификатов](https://metrics.samoy.love/d/samoylove-status?viewPanel=14)

**Что случилось.** Сертификат не продлился на 30 днях остатка

**Что это значит и что делать.** Certbot продлевает за 30 дней до конца; меньше 25 — продление сломано. Так 19.09.2026 нашёлся launcher: certbot.service падал молча месяц. Смотреть journalctl -u certbot в контейнере web.

<details><summary>Условие</summary>

```promql
min by (project) (status_cert_days_left) < 25
```

Держится: 6h · группа `product-status` · uid `product-status-cert-renewal-missed`

</details>

<a id="monitoring-area"></a>

## Мониторинг

<a id="mon-prometheus-ingestion-stopped"></a>

### Мониторинг: Prometheus не пишет точки

**авария** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Точек в секунду](https://metrics.samoy.love/d/samoylove-overview?viewPanel=46)

**Что случилось.** Prometheus перестал записывать точки

**Что это значит и что делать.** Сбор встал целиком: все панели замерли, а тревоги смотрят на устаревшие данные. Журнал контейнера samoylove-prometheus.

<details><summary>Условие</summary>

```promql
sum(rate(prometheus_tsdb_head_samples_appended_total[5m])) == 0
```

Держится: 5m · группа `infra-monitoring` · uid `mon-prometheus-ingestion-stopped`

</details>

<a id="mon-grafana-scheduler-behind"></a>

### Мониторинг: Grafana не успевает вычислять тревоги

**предупреждение** · порог: дольше 30 с, держится 10 мин · панель: [Сайты samoy.love — сводка → Отставание тревог](https://metrics.samoy.love/d/samoylove-overview?viewPanel=50)

**Что случилось.** Планировщик тревог Grafana отстаёт больше чем на 30 секунд

**Что это значит и что делать.** Тревоги вычисляются с опозданием на столько же, насколько отстаёт планировщик.

<details><summary>Условие</summary>

```promql
grafana_alerting_scheduler_behind_seconds > 30
```

Держится: 10m · группа `infra-monitoring` · uid `mon-grafana-scheduler-behind`

</details>

<a id="mon-prometheus-reload-failed"></a>

### Мониторинг: Prometheus не принял конфиг

**предупреждение** · порог: держится 10 мин · панель: [Сайты samoy.love — сводка → Конфиг Prometheus](https://metrics.samoy.love/d/samoylove-overview?viewPanel=49)

**Что случилось.** Последняя перезагрузка конфига Prometheus не удалась

**Что это значит и что делать.** Prometheus работает на старом конфиге: изменения целей из последней выкатки не применились. Смотреть журнал контейнера samoylove-prometheus.

<details><summary>Условие</summary>

```promql
prometheus_config_last_reload_successful == 0
```

Держится: 10m · группа `infra-monitoring` · uid `mon-prometheus-reload-failed`

</details>

<a id="mon-grafana-rule-eval-failing"></a>

### Мониторинг: правила тревог не вычисляются

**предупреждение** · порог: больше 0, держится 15 мин · панель: [Сайты samoy.love — сводка → Сбоев правил за час](https://metrics.samoy.love/d/samoylove-overview?viewPanel=51)

**Что случилось.** Grafana не может вычислить правила тревог

**Что это значит и что делать.** Правило, которое не вычисляется, не видит того, что должно сторожить. Какое именно — страница /alerting/list, состояние Error.

<details><summary>Условие</summary>

```promql
sum(increase(grafana_alerting_rule_evaluation_failures_total[30m])) > 0
```

Держится: 15m · группа `infra-monitoring` · uid `mon-grafana-rule-eval-failing`

</details>

<a id="mon-scrape-near-timeout"></a>

### Мониторинг: сбор цели почти упирается в таймаут

**предупреждение** · порог: дольше 8 с, держится 15 мин · панель: [Сайты samoy.love — сводка → Время опроса целей](https://metrics.samoy.love/d/samoylove-overview?viewPanel=53)

**Что случилось.** Сбор ‹job› идёт дольше 8 секунд из 10

**Что это значит и что делать.** Таймаут опроса 10 с; цель, которая к нему подходит, скоро начнёт выпадать из сбора.

<details><summary>Условие</summary>

```promql
max by (job) (scrape_duration_seconds) > 8
```

Держится: 15m · группа `infra-monitoring` · uid `mon-scrape-near-timeout`

</details>

<a id="mon-host-textfile-stale"></a>

### Мониторинг: файл метрик на хосте устарел

**предупреждение** · порог: дольше 30 мин, держится 5 мин · панель: [Сайты samoy.love — сводка → Конфиг Prometheus](https://metrics.samoy.love/d/samoylove-overview?viewPanel=49)

**Что случилось.** Файл ‹file› не обновлялся больше 30 минут

**Что это значит и что делать.** Сборщик на хосте завис или его таймер встал (файл — метка file: smart.prom и zfs.prom пишет node-textfile-collect раз в 5 минут, ci.prom — ci-queue-collect раз в 30 секунд). Старые значения при этом выглядят живыми, и «Сервер: сбор SMART и ZFS сломан» молчит.

<details><summary>Условие</summary>

```promql
time() - node_textfile_mtime_seconds{job="node-host",file!~".*/backup_laptop.prom"} > 1800
```

Держится: 5m · группа `infra-monitoring` · uid `mon-host-textfile-stale`

</details>

<a id="mon-prometheus-tsdb-near-limit"></a>

### Мониторинг: хранилище Prometheus почти у лимита

**предупреждение** · порог: больше 85%, держится 1 ч · панель: [Сайты samoy.love — сводка → TSDB от лимита размера](https://metrics.samoy.love/d/samoylove-overview?viewPanel=48)

**Что случилось.** TSDB занимает больше 85% лимита размера

**Что это значит и что делать.** Упёршись в лимит размера, Prometheus молча удаляет историю раньше 90 дней. 19.09.2026 было занято 8%.

<details><summary>Условие</summary>

```promql
prometheus_tsdb_storage_blocks_bytes / prometheus_tsdb_retention_limit_bytes > 0.85
```

Держится: 1h · группа `infra-monitoring` · uid `mon-prometheus-tsdb-near-limit`

</details>

<a id="mon-prometheus-tsdb-failures"></a>

### Мониторинг: хранилище Prometheus сбоит

**предупреждение** · порог: больше 0 · панель: [Сайты samoy.love — сводка → Сбои хранилища Prometheus](https://metrics.samoy.love/d/samoylove-overview?viewPanel=54)

**Что случилось.** Сбои уплотнения или журнала TSDB Prometheus

**Что это значит и что делать.** Хранилище Prometheus портится: сбой уплотнения или журнала WAL. История может пропасть — смотреть журнал контейнера и место на томе.

<details><summary>Условие</summary>

```promql
(increase(prometheus_tsdb_compactions_failed_total[1h]) + increase(prometheus_tsdb_wal_corruptions_total[1h]) + increase(prometheus_tsdb_wal_writes_failed_total[1h])) > 0
```

Держится: 0m · группа `infra-monitoring` · uid `mon-prometheus-tsdb-failures`

</details>

<a id="mon-scrape-target-down"></a>

### Мониторинг: цель сбора не отвечает

**предупреждение** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Сбор метрик](https://metrics.samoy.love/d/samoylove-overview?viewPanel=26)

**Что случилось.** Prometheus не может собрать ‹job›

**Что это значит и что делать.** Prometheus не может снять метрики с цели (метка job). Панели этой цели замерли на последних значениях, а тревоги по её метрикам молчат. Для snakes и chillhub частая причина — ограничение сети в юните сервиса (README, «Как добавить цель сбора»).

<details><summary>Условие</summary>

```promql
up{job!~"node-host|incus|blackbox-http|nginxlog|cs2-api|cs2-win"} == 0
```

Держится: 5m · группа `infra-monitoring` · uid `mon-scrape-target-down`

</details>

<a id="mon-scrape-target-missing"></a>

### Мониторинг: цель сбора пропала из конфига

**предупреждение** · порог: держится 15 мин · панель: [Сайты samoy.love — сводка → Сбор метрик](https://metrics.samoy.love/d/samoylove-overview?viewPanel=26)

**Что случилось.** Цели сбора хоста, Incus или Пристрелки нет в Prometheus

**Что это значит и что делать.** Цель из file_sd пропала целиком: файл /etc/prometheus/targets/*.yml опустел или удалён. up == 0 при этом не бывает, поэтому остальные тревоги молчат.

<details><summary>Условие</summary>

```promql
absent(up{job="node-host"}) or absent(up{job="incus"}) or absent(up{job="cs2-api"})
```

Держится: 15m · группа `infra-monitoring` · uid `mon-scrape-target-missing`

</details>

<a id="infra-monitoring-exporter-down"></a>

### Мониторинг: экспортёр проб или журналов не отвечает

**предупреждение** · порог: держится 5 мин · панель: [Сайты samoy.love — сводка → Сбор метрик](https://metrics.samoy.love/d/samoylove-overview?viewPanel=26)

**Что случилось.** Prometheus не может собрать ‹job›: данные за ним устарели

**Что это значит и что делать.** Пока экспортёр молчит, тревоги доступности и посещаемости сайтов слепы. docker ps в web — жив ли контейнер samoylove-blackbox или samoylove-nginxlog.

<details><summary>Условие</summary>

```promql
up{job="nginxlog"} == 0 or (count(up{job="blackbox-http"} == 0) == count(up{job="blackbox-http"}))
```

Держится: 5m · группа `infra-services` · uid `infra-monitoring-exporter-down`

</details>
