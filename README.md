# 🚌 Bulloch County Schools — Bus Navigation & Tracking System

An enterprise real-time fleet management, route building, and driver navigation application designed for **Bulloch County Schools**. Built with **Python**, **NiceGUI**, **FastAPI**, **Firebase Firestore**, **OpenWeatherMap API**, and **Google Maps Routes API**. Optimized for desktop administration as well as Raspberry Pi 5 touchscreens (1024x600) mounted in school buses.

---

## 📌 Table of Contents

* [Architecture Overview](#-architecture-overview)
* [Key Features](#-key-features)
* [Page-by-Page Overview](#-page-by-page-overview)
* [Project Structure](#-project-structure)
* [Prerequisites](#-prerequisites)
* [Installation & Local Setup](#-installation--local-setup)
* [Environment Variables Configuration](#-environment-variables-configuration)
* [Firebase Setup](#-firebase-setup)
* [Running the Application](#-running-the-application)
* [Hardware & Raspberry Pi 5 Deployment](#-hardware--raspberry-pi-5-deployment)

---

## 🏗 Architecture Overview

The system operates across a 3-tier architecture connecting bus hardware, cloud database, and web consoles:

```text
  [ GPS Trackers / Hardware ] ───────> [ Firebase Firestore ]
                                              │
                                              ▼
[ Driver CarPlay HUD Screen ] <───> [ FastAPI / NiceGUI ] <───> [ Admin Command Center ]
   (Raspberry Pi 5 Touch)              (App Server)               (Dispatch Web Console)
```

* **Backend Engine:** Powered by FastAPI and Uvicorn, handling API routes (`/api/v1/*`), session middleware, and authentication logic.
* **Real-time UI:** Built using NiceGUI (Python wrapper around Vue.js and Quasar) providing reactive map updates, live data streams, and touch-optimized controls without manual page reloads.
* **Session & Auth State:** Uses Starlette SessionMiddleware to share login state seamlessly between FastAPI endpoints (`/api/v1/auth/store-session`) and NiceGUI page handlers (`request.session`). Authentication is strictly restricted to domain emails ending in `@bullochschools.org`.
* **Cloud Persistence:** Firebase Firestore acts as the real-time source of truth for active bus positions, route configurations, stop sequences, and incident logs.
* **OpenWeatherMap API:** Live temperature, weather conditions, wind speed, and weather icon integration on driver displays.
* **Google Maps Routes / Directions API:** Polyline generation, turn-by-turn navigation steps, and route optimization.
* **Text-to-Speech (TTS):** Voice announcements triggered during route start, pause, and stop events.

---

## ✨ Key Features

* **Domain-Restricted SSO / Login:** Only authorized `@bullochschools.org` accounts can log in.
* **Role-Based Access Control (RBAC):** Supports admin, dispatch, dispatcher, and driver roles.
* **CarPlay-Style Driver HUD:** Specifically designed for 1024x600 touchscreen resolution with high-contrast, tactile touch targets.
* **Dual-Role Admin Driver HUD:** Administrators and transportation directors covering routes as sub-drivers have full operational access to the driver HUD with a one-tap `🖥️ Admin Console` toggle button.
* **Interactive Route Builder:** Admin map tool allowing dispatchers to click anywhere on a Leaflet map to drop stop markers, assign bus numbers, select shifts (Morning/Afternoon), and save routes directly to Firestore.
* **Live Fleet Tracking Map:** Dynamic Leaflet tracker updating bus marker positions and status counts (Total Active, On-Time, Alerts) automatically every 3 seconds.
* **Live Weather Integration:** Automatic 10-minute weather polling tailored for Bulloch County (Statesboro, GA).
* **One-Touch Dispatch Alerts:** Instant incident reporting for drivers (Mechanical Issue, Heavy Traffic, Weather Hazard, Sub Driver Request).

---

## 📄 Page-by-Page Overview

### Public & Authentication Routes

| Route | Authorized Roles | Description |
| :--- | :--- | :--- |
| `/login` | Public | Google / Email Domain Authentication restricted to `@bullochschools.org`. |
| `/` | Authenticated | Smart Root Router. Redirects drivers to HUD and admins to Fleet Command. |

### Driver HUD Routes

| Route | Authorized Roles | Description |
| :--- | :--- | :--- |
| `/driver` | Driver, Admin, Dispatch | CarPlay Dashboard. Route status, start/end buttons, weather, and alerts. |
| `/driver/map` | Driver, Admin, Dispatch | Full-Screen GPS Navigation Map with turn-by-turn tracking. |
| `/driver/alerts` | Driver, Admin, Dispatch | Large-button touch console for urgent alerts (Mechanical, Traffic, Weather). |

### Admin & Dispatch Console Routes

| Route | Authorized Roles | Description |
| :--- | :--- | :--- |
| `/admin` | Admin, Dispatch | Fleet Operations Center. Live stats and real-time Leaflet fleet tracker map. |
| `/admin/routes` | Admin, Dispatch | Interactive Route Builder. Map interface for building sequences and assigning buses. |
| `/admin/users` | Admin | User Management Console. Account role assignments for school staff. |
| `/admin/settings` | Admin, Dispatch | System Settings. API key management and system toggles. |

---

## 📁 Project Structure

```text
bulloch-transport/
├── app/
│   ├── api/                      # FastAPI REST endpoints
│   │   ├── admin.py              # Admin REST handlers
│   │   ├── auth.py               # Authentication & session storage endpoints
│   │   └── routes.py             # Route API endpoints
│   ├── config/                   # Configuration files
│   │   ├── firebase.py           # Firebase Admin SDK initialization
│   │   └── settings.py           # Pydantic environment settings
│   ├── services/                 # Business logic & external API integrations
│   │   ├── fleet.py              # Firestore live fleet tracking service
│   │   ├── routes.py             # Route creation & retrieval service
│   │   ├── routing.py            # Google Maps Routes API integration
│   │   ├── tts.py                # Text-To-Speech audio service
│   │   └── weather.py            # OpenWeatherMap API integration
│   ├── ui/                       # NiceGUI page definitions & UI components
│   │   ├── admin/                # Admin views
│   │   │   ├── fleet_map.py      # Fleet command dashboard (/admin)
│   │   │   └── routes.py         # Route builder dashboard (/admin/routes)
│   │   ├── auth/                 # Authentication views
│   │   │   └── login.py          # Login screen (/login)
│   │   └── driver/               # Driver touchscreen views
│   │       ├── alerts.py         # Incident report screen (/driver/alerts)
│   │       ├── dashboard.py      # Main CarPlay HUD (/driver)
│   │       ├── map.py            # GPS navigation map (/driver/map)
│   │       └── weather_widget.py # Live weather UI card component
│   ├── static/                   # Static files (icons, CSS, custom assets)
│   └── main.py                   # Main FastAPI entry point & NiceGUI router
├── .env                          # Environment variables configuration
├── .env.example                  # Example environment variables template
├── requirements.txt              # Python package dependencies
└── README.md                     # Project documentation
```

---

## 🛠 Prerequisites

Ensure you have the following installed on your system:

* Python 3.10+ (Tested on Python 3.12 & 3.14)
* Git
* Firebase Account with a Firestore Database instance initialized
* OpenWeatherMap API Key (Free tier supported)
* Google Cloud Platform Account with Routes API and Geocoding API enabled

---

## 🚀 Installation & Local Setup

**1. Clone the Repository**
```bash
git clone [https://github.com/bulloch-schools/bulloch-transport.git](https://github.com/bulloch-schools/bulloch-transport.git)
cd bulloch-transport
```

**2. Create and Activate a Virtual Environment (Windows PowerShell)**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**3. Create and Activate a Virtual Environment (macOS / Linux)**
```bash
python3 -m venv venv
source venv/bin/activate
```

**4. Install Required Dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 Environment Variables Configuration
**Do not set this up unless you know what you're doing**
Create a `.env` file in the root directory of the project:

```env
# Application Security
SECRET_KEY="replace-this-with-a-secure-random-string"

# External API Keys
OPENWEATHER_API_KEY="your_openweather_api_key_here"
GOOGLE_MAPS_API_KEY="your_google_maps_routes_api_key_here"

# Firebase Credentials Path (optional if using default credentials)
FIREBASE_CREDENTIALS_PATH="app/config/firebase-service-account.json"
```

---

## 🔥 Firebase Setup

1. Go to the Firebase Console and create a project.
2. Enable Firestore Database in production or test mode.
3. Download your Firebase Service Account Admin Key via Project Settings > Service Accounts.
4. Save the downloaded `.json` file as `app/config/firebase-service-account.json`.
5. Create a `buses` collection in Firestore for active vehicle locations (latitude, longitude, speed, status, has_alert).
6. Create a `routes` collection in Firestore for stop coordinates, route titles, shift, and bus assignments.

---

## 🏃 Running the Application

**Start the server with live auto-reload enabled:**
```bash
python -m app.main
```

**Or run directly with uvicorn:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Access the web application:**
* Driver Dashboard: `http://localhost:8000/driver`
* Admin Fleet Command: `http://localhost:8000/admin`
* Route Builder: `http://localhost:8000/admin/routes`
* Login Screen: `http://localhost:8000/login`

---

## 🖥 Hardware & Raspberry Pi 5 Deployment

* **Kiosk Mode Launch:** Configure Raspberry Pi OS to launch Chromium in kiosk mode targeting the application server URL:
  ```bash
  chromium-browser --kiosk --noerrdialogs --disable-infobars http://<server-ip>:8000/driver
  ```
* **Resolution Optimization:** The `/driver` page uses Tailwind classes fixed to full viewport height (`h-screen`) and grid spacing explicitly fitted for 1024x600 touch displays without scrollbars.
* **Audio Support:** Ensure `alsa-utils` or sound drivers are installed on the Pi to play Text-to-Speech (TTS) audio route status prompts through the bus speaker system.

---

## 📄 License & Attribution

Developed for Bulloch County Schools Transportation Department. All rights reserved.