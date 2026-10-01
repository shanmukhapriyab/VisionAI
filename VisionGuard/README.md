# VisionGuard

Real-time hazard detection with spoken alerts, built as an accessibility prototype for people with low vision or blindness.

> ## ⚠️ Experimental accessibility prototype
> **VisionGuard is a research/learning prototype. Do not rely on it as your only navigation or safety system.**
> It can miss objects, misidentify them, mis-estimate distance, and it can stop working (camera, browser, backend or model failure).
> It is not a certified assistive device and has not been tested with real users. Always use a white cane, guide dog,
> sighted assistance or other proven mobility aids. The **Emergency** button only records an event on your own computer;
> **it does not contact anyone**. In an emergency, call your local emergency number.

```
Camera → YOLO object detection → identify object → estimate distance
       → LEFT / CENTER / RIGHT → danger level → spoken warning
```

Example alerts: *"Person ahead."* · *"Chair on your left."* · *"Warning. Vehicle approaching from your right."* · *"Stop. Chair very close ahead."*

---

## Quick start on Windows

### 1. Install two things (once)

| Tool | Version | Download |
|---|---|---|
| Python | 3.10, 3.11 or 3.12 (recommended) | https://www.python.org/downloads/ — tick **“Add python.exe to PATH”** |
| Node.js | LTS (18 or newer) | https://nodejs.org/ |

You also need a webcam and **Chrome or Edge** (best speech and camera support). No GPU is needed.

### 2. Run it

1. Unzip `VisionGuard.zip` somewhere simple, e.g. `C:\VisionGuard`.
2. Double-click **`start_all.bat`**.

The first run installs everything (PyTorch + YOLO, about 1–2 GB, 5–15 minutes). Later runs start in seconds.
When both services are ready your browser opens **http://localhost:5173**.

3. Click **Start detection** and allow camera access.

Prefer to start the parts yourself? Open two Command Prompt windows in the project folder:

```bat
:: window 1 - backend (API + YOLO)  -> http://127.0.0.1:8000
start_backend.bat

:: window 2 - frontend (web app)     -> http://localhost:5173
start_frontend.bat
```

Or by hand:

```bat
cd backend
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: in a second window
cd frontend
npm install
npm run dev
```

> Open the app at `http://localhost:5173` (or `127.0.0.1`). Browsers block the camera on other plain-HTTP addresses.

---

## Using VisionGuard

* **Start / Stop detection** – button, or press `Space`.
* **Voice on / off** – button, or press `V`. Settings has speech speed, volume, voice choice, and how often alerts repeat.
* **Alert panel** – shows the most dangerous thing in view in large text, exactly what is being spoken.
  Below it, Left / Center / Right lanes show what is on each side. The **In view** list shows every object with confidence, distance and side.
* **Video overlay** – bounding boxes with `object, confidence, distance, side`. Line style also changes with danger, so it never relies on colour alone.
* **Header** – FPS (results per second), model time (YOLO inference on the server) and total delay (camera frame → result).
* **History tab** – detections stored in SQLite (`backend/data/visionguard.db`). Filter by level, or clear it.
* **Settings** – minimum detection confidence, which levels are spoken, camera choice, dark/light theme, text size (up to 150%), optional emergency phone number.
* **Emergency** – records an event locally, speaks a reminder that this is a prototype, and (if you entered a number in Settings) shows a one-tap call link.

### Danger levels

| Level | Meaning | Typical example |
|---|---|---|
| **SAFE** | Far away or unimportant | Person 8 m away |
| **CAUTION** | Something to be aware of | Person 3–5 m ahead, chair on your left |
| **WARNING** | Slow down / prepare to avoid | Person about 2 m ahead, vehicle approaching from the side |
| **DANGER** | Stop | Obstacle under ~1 m in your path, vehicle closing fast |

Each level has its own **colour, shape and word** (circle / triangle / diamond / octagon).

The score combines distance, object type (vehicles weigh more, bottles less), position (straight ahead counts more than the sides) and time-to-collision. A few safety floors always apply, e.g. any obstacle within ~0.8 m straight ahead is DANGER. Traffic lights and stop signs are informational and never rise above CAUTION. The most dangerous object is always announced first.

### How voice alerts avoid nagging

* The same object on the same side is repeated only after a delay (Settings → *Repeat delay*, default 6 s; DANGER repeats sooner).
* If something gets **more** dangerous, it is announced immediately.
* Alerts below your chosen level (default: CAUTION) are shown on screen but not spoken.
* Speech never overlaps, except that DANGER interrupts whatever is being said.
* If detection fails (backend stops, camera unplugged) the app **speaks that as well** and shows an error banner.

---

## What it detects

`person, car, bus, truck, bicycle, motorcycle, chair, backpack, bottle, dog, cat, bench, traffic light, stop sign`
plus a few common obstacles: `fire hydrant, couch, dining table, potted plant, suitcase`.

Uses **YOLOv8n** (nano, ~6 MB, pretrained on COCO) on the CPU through Ultralytics + OpenCV. The weights file is included in `backend/models/`; if it is missing it is downloaded once from the official Ultralytics release. If the model cannot load, the API returns a real error and the UI shows it. **The app never invents detections.**

## Limitations you should understand

* **Distance is an estimate**, computed from the bounding-box height and a typical real-world size for that object (pinhole camera model with an assumed 65° field of view; change with `VISIONGUARD_HFOV`). Children, unusual objects, tilted cameras and partly hidden objects give wrong numbers. Objects cut off by the frame edge are flagged and estimated cautiously.
* **Moving-object detection** tracks objects across frames and measures how fast their estimated distance shrinks. Because the *camera* moves when you walk, this is relative motion: a chair you walk toward also “closes in”. The app only says **“approaching”** for things that can move by themselves (people, vehicles, animals, bikes). Camera shake can cause false alarms.
* YOLOv8n is small and fast, not perfect: it misses objects, especially in the dark, far away, small or blurry. It does not detect stairs, kerbs, holes, wet floors, poles, glass doors or many other real hazards.
* Speed depends on your CPU. Around 5–10 FPS is normal on a laptop; lower `VISIONGUARD_IMGSZ` to speed up.
* “No known objects in view” does **not** mean the way is clear.

## Privacy

Camera frames go from your browser to the backend on **your own computer** (`127.0.0.1`) and are not saved or sent anywhere else. Only detection results (label, confidence, distance, side, level, message) are stored in the local SQLite database.

---

## Project structure

```
VisionGuard/
├── start_all.bat  start_backend.bat  start_frontend.bat
├── README.md  requirements.txt  package.json
├── backend/                     Python + FastAPI
│   ├── requirements.txt  requirements-dev.txt  pytest.ini
│   ├── app/
│   │   ├── main.py              API endpoints
│   │   ├── detector.py          YOLO + OpenCV wrapper, real error reporting
│   │   ├── pipeline.py          frame → detections → distance/side/motion → danger → message
│   │   ├── geometry.py          distance estimate, LEFT/CENTER/RIGHT
│   │   ├── tracker.py           frame-to-frame tracking, approach speed
│   │   ├── danger.py            SAFE / CAUTION / WARNING / DANGER + prioritisation
│   │   ├── messages.py          spoken sentences
│   │   ├── objects.py           supported objects + typical sizes
│   │   ├── database.py          SQLite history + emergency events
│   │   └── config.py
│   ├── models/yolov8n.pt        pretrained lightweight model
│   ├── data/                    SQLite database is created here
│   └── tests/                   pytest suite
└── frontend/                    React + Vite
    ├── package.json  vite.config.js  index.html
    └── src/
        ├── App.jsx  styles.css  main.jsx
        ├── components/          CameraView, AlertPanel, ControlBar, SettingsPanel, HistoryPanel, ...
        ├── hooks/               useDetection (camera + detection loop), useSettings
        └── lib/                 api.js, speech.js (text-to-speech + cooldown), draw.js
```

## API (http://127.0.0.1:8000, docs at `/docs`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | model state (`loading` / `ok` / `error` + reason), database state |
| POST | `/api/detect?session_id=…&conf=0.4` | body = one JPEG frame → detections with box, confidence, distance, side, danger, message |
| GET / DELETE | `/api/history` | stored detections (`limit`, `offset`, `level`, `label`) / clear |
| GET | `/api/history/stats` | counts by level and label |
| POST / GET | `/api/emergency` | record / list prototype emergency events |

Error responses look like `{"error": {"code": "MODEL_LOADING", "message": "…"}}`.

## Configuration (environment variables, all optional)

| Variable | Default | Meaning |
|---|---|---|
| `VISIONGUARD_IMGSZ` | `416` | YOLO input size. `320` = faster, `640` = more accurate |
| `VISIONGUARD_CONF` | `0.40` | default minimum confidence |
| `VISIONGUARD_HFOV` | `65` | camera horizontal field of view in degrees (distance accuracy) |
| `VISIONGUARD_MODEL` | `yolov8n.pt` | model file in `backend/models/` |
| `VISIONGUARD_DB` | `backend/data/visionguard.db` | database path |

Example: `set VISIONGUARD_IMGSZ=320` then `start_backend.bat`.

## Tests

```bat
cd backend
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q

cd ..\frontend
npm test
```

Backend tests cover distance/position geometry, danger classification and prioritisation, spoken messages, the motion tracker, the pipeline, the API and database (using a stand-in detector **only inside tests**), error handling when the model is unavailable, and an end-to-end test with the **real YOLO model** on a real photo (`tests/fixtures/bus.jpg`). Frontend tests cover the voice-alert cooldown logic.

## Troubleshooting

| Problem | Fix |
|---|---|
| “Cannot reach the backend” | Run `start_backend.bat` and wait until it prints *Application startup complete*. |
| “The AI model is still loading” | Wait a few seconds; detection begins by itself. |
| “The YOLO model could not be downloaded” | Connect to the internet once, or place `yolov8n.pt` in `backend\models\`. |
| Camera permission denied | Click the camera/lock icon in the address bar → allow → Start again. |
| “The camera is busy” | Close Teams/Zoom/other tabs using the camera. |
| Wrong camera | Settings → Detection → Camera. |
| No sound | Turn *Voice* on, raise volume, use *Test voice*. Chrome/Edge need one click on the page first (pressing Start counts). |
| Low FPS | Set `VISIONGUARD_IMGSZ=320`, close other programs, use a wired power connection. |
| `pip install` fails on PyTorch | Use Python 3.11 or 3.12, delete `backend\.venv`, run `start_backend.bat` again. |
| Port already in use | Close old VisionGuard windows (ports 8000 and 5173). |
| Optional single-port mode | `cd frontend && npm run build`, then only run the backend and open http://127.0.0.1:8000 |

## Licenses and credits

* YOLOv8 / Ultralytics is licensed **AGPL-3.0** (commercial use needs an Ultralytics enterprise license). Weights: pretrained on COCO by Ultralytics.
* UI font: Atkinson Hyperlegible (Braille Institute), SIL Open Font License, designed for low-vision readability.
* React, Vite, FastAPI, OpenCV, PyTorch and their dependencies keep their own licenses.
* `backend/tests/fixtures/bus.jpg` is the sample image bundled with Ultralytics.
