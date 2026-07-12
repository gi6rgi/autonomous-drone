# Follow-me дрон: 5" deadcat на SpeedyBee F405 V3 + Raspberry Pi 5

Дрон, следующий за объектом: ArduPilot держит машину в воздухе, Raspberry Pi 5
видит цель через камеру и шлёт полётному контроллеру команды скорости по MAVLink
(режим GUIDED).

```
frame/frame.py        параметрическая рама (build123d -> STL/STEP)
frame/export/         готовые файлы: STL на печать, STEP для FreeCAD
software/follow/      код follow-me для Pi
software/tools/       утилиты: маркер, тест камеры, тест связи
```

---

## 1. Железо

### Что уже есть
SpeedyBee F405 V3 BLS 50A (FC+ESC), 6S 4000 mAh, моторы RETEK LN2207
(**используйте версию 1960 KV**, на первые полёты `MOT_SPIN_MAX` ~0.85),
винты 5.1x3.7x3, GPS Neo-M8M, Pi 5 + Arducam IMX219 175°, XT60, smoke stopper.

### Докупить обязательно
| Что | Зачем |
|---|---|
| Приёмник + пульт (ELRS 2.4G) | ручное управление и аварийный перехват. **Без RC не летать.** |
| BEC 5V/5A с входом 2–8S (до 35 В) | питание Pi 5. **MINI560 обычно до 20 В — на 6S сгорит, проверьте маркировку** |
| Крепёж: M3x12 (8 шт, армы) + гайки с нейлоном, стойки M3x30 (4) + M3x8 (8), M2.5x8 + стойки (Pi), M2x6 (камера), M3x8 (кронштейн/мачта) | сборка |
| Ремешок АКБ 20 мм, пенка под АКБ, стяжки | |
| Если на плате GPS нет компаса (чип QMC5883) | модуль GPS+компас — Loiter будет заметно стабильнее |

### Схема соединений
```
6S XT60 ─┬─ ESC (пады +/- , конденсатор Low-ESR прямо на пады!)
         └─ BEC 5V/5A ── Pi 5 (пины 5V: GPIO-пин 2/4 и GND 6)

FC UART (свободный, напр. T4/R4) ── Pi 5 UART: GPIO14 TXD -> RX FC,
                                    GPIO15 RXD <- TX FC, GND общий
GPS: TX/RX -> UART GPS-пады FC, SDA/SCL (компас) -> I2C пады FC
Камера IMX219 -> CSI-шлейф Pi 5 (нужен шлейф 22pin mini -> 15pin, если не в комплекте)
Приёмник ELRS -> UART2 FC (обычно пады T2/R2 + 4.5V)
```
Логика UART у FC и Pi — 3.3 В, соединяются напрямую. TX всегда крест-накрест с RX.

---

## 2. Рама

### Генерация
```bash
.venv/bin/python frame/frame.py     # -> frame/export/*.stl, *.step, assembly.step
```
Все размеры — параметры в начале `frame/frame.py` (база, толщина арма, наклон
камеры и т.д.). Поменяли — перезапустили — получили новые файлы. STEP открывается
во FreeCAD для доработки, `assembly.step` — вся рама в сборе для проверки.

### Детали и печать
| Деталь | Кол-во | Ориентация | Настройки |
|---|---|---|---|
| `arm.stl` | 4 | плашмя | PETG/ABS, **6+ периметров, заполнение 50% gyroid**, 100% для первых 2 мм |
| `bottom_plate.stl` | 1 | плашмя | 5 периметров, 40% |
| `top_plate.stl` | 1 | плашмя | 4 периметра, 30% |
| `camera_bracket.stl`, `gps_mast.stl` | 1+1 | базой вниз | обычные |

PLA не использовать (плывёт от нагрева моторов). Армы — расходник: печатайте
сразу 6 штук. Если MVP полетит стабильно — плиты и армы стоит перевести на
карбон, печатными оставить кронштейны.

### Сборка
1. Хвостовики армов вставляются в карманы снизу нижней плиты, M3x12 сверху,
   гайки с нейлоном снизу.
2. Моторы — на площадки армов (M3 из комплекта моторов), провода вдоль арма
   стяжками.
3. Стек на нижнюю плиту (30.5x30.5, люверсы), стрелка FC — вперёд (в нос).
4. Стойки M3x30 -> верхняя плита -> Pi 5 на стойках M2.5, камера в кронштейн
   на носу (наклон 10° вниз уже в детали), GPS на мачту на корме.
5. АКБ снизу на ремешке через прорези, пенка между АКБ и гайками армов.
   Двигайте АКБ вперёд/назад до баланса: центр тяжести — на оси стека.

---

## 3. Прошивка FC (ArduPilot)

1. Скачайте ArduCopter для таргета **SpeedyBeeF405v3** с firmware.ardupilot.org.
2. Первая прошивка — через DFU (зажать boot-кнопку, USB): STM32CubeProgrammer
   или Mission Planner -> Load custom firmware (`*_with_bl.hex`).
3. В Mission Planner: FRAME_CLASS=1 (Quad), FRAME_TYPE=1 (X). Deadcat-геометрию
   ArduPilot считает обычным X — для наших углов это ок.
4. Калибровки: акселерометр, компас, радио, ESC (BLHeli_S — протокол DShot300:
   `MOT_PWM_TYPE=4`).
5. Ключевые параметры:
```
SERIALx_PROTOCOL = 2      # MAVLink2 на UART, куда подключён Pi
SERIALx_BAUD     = 921    # 921600
MOT_PWM_TYPE     = 4      # DShot300
MOT_SPIN_MAX     = 0.85   # бережём моторы/ESC на 6S первое время
BATT_MONITOR     = 4      # ток+напряжение со стека
FS_THR_ENABLE    = 1      # потеря RC -> RTL
BATT_FS_LOW_ACT  = 2      # низкая батарея -> RTL
BATT_LOW_VOLT    = 21.6   # 3.6 В/банка
GUID_TIMEOUT     = 3      # нет команд от Pi 3 с в GUIDED -> зависание
```
6. Режимы на тумблеры: `Stabilize | AltHold | Loiter` + отдельный тумблер
   `RTL` и **GUIDED** (появится после настройки; GUIDED = «управляет Pi»).
7. Motor Test (без винтов!): порядок и направление по схеме ArduPilot X.

---

## 4. Raspberry Pi 5

```bash
# Raspberry Pi OS Bookworm 64-bit
sudo apt update && sudo apt install -y python3-picamera2 python3-opencv python3-pip
cd software && pip install -r requirements.txt --break-system-packages

# UART для FC: в /boot/firmware/config.txt добавить
#   enable_uart=1
#   dtparam=uart0=on
# и отключить консоль на serial: sudo raspi-config -> Interface -> Serial Port
#   (login shell: No, hardware: Yes). Порт: /dev/ttyAMA0 (GPIO14/15).
```

Камеру проверить: `rpicam-hello -t 5000` (для IMX219 обычно работает из коробки).

---

## 5. Проверка софта по шагам (до полёта)

```bash
cd software
python tools/generate_aruco.py            # напечатать маркер ~30 см, размер в config.yaml
python tools/test_camera.py               # кадр с детекцией -> frame.jpg
python tools/test_link.py                 # heartbeat, режим, батарея, GPS
python -m follow.main --dry-run           # весь конвейер без отправки команд
```

Опционально, без дрона — SITL на ПК (симулятор ArduPilot):
```bash
# https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
# в config.yaml: connection: udp:127.0.0.1:14550, camera.backend: opencv
# маркер показывайте в веб-камеру
```

---

## 6. Полётная программа (по порядку, не перескакивать)

1. **Стенд**: первое включение только через smoke stopper. Без винтов.
2. **Полёт 1–2**: Stabilize/AltHold, триммирование, затем AUTOTUNE (с этой
   массой стоковые PID будут вялыми).
3. **Полёт 3**: Loiter — дрон должен неподвижно стоять в точке. Пока Loiter
   не идеален, follow-me не включать.
4. **Полёт 4**: Pi запущен (`python -m follow.main`), маркер стоит на земле.
   Взлёт в Loiter, повернуть дрон камерой на маркер, тумблер -> **GUIDED**.
   Дрон должен довернуться на маркер и подойти на 4 м. Рука на тумблере:
   что-то не так -> LOITER.
5. Маркер в руках, медленная ходьба. Потом поднимать скорости в config.yaml.

**Безопасность**: открытое поле, без людей в радиусе 30 м; цель потеряна ->
Pi сам зависает через 0.5 с и уходит в LOITER через 5 с; батарея < 21 В ->
LOITER; RC-тумблер всегда главнее Pi.

## 7. Что дальше (после MVP)
- Fisheye-калибровка камеры (cv2.fisheye) — точные углы/дистанция по всему кадру.
- Трекинг человека: YOLOv8n (640x384, ~5–10 FPS на Pi 5) вместо ArUco,
  файл `follow/tracker.py` — добавить класс по образцу.
- Удержание высоты по цели (vz), follow сбоку/сзади, гео-забор в `safety.py`.
