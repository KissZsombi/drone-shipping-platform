# Drone Shipping Platform

Egyszerű FastAPI alapú backend és böngészős UI demonstráció drónos kiszállítási útvonalakhoz. Az alkalmazás a háttérben SQLite adatbázist használ, MQTT-n keresztül route üzeneteket tud fogadni/küldeni, és egy statikus HTML UI-t szolgál ki.

## Fő komponensek és felelősségek
- `backend/main.py` – FastAPI alkalmazás, CORS beállítás, HTML kiszolgálás (`/`), REST végpontok (megyék, helyek, rendelés létrehozás, cache-elt útvonal/telemetria), WebSocket streaming (`/ws`). Startupkor indítja a háttér MQTT klienst.
- `backend/db.py` – SQLAlchemy engine, session factory, `Base`. Alapértelmezett SQLite útvonal: `backend/drone_delivery.db`.
- `backend/models.py` – ORM modellek és relációk: `County`, `Station`, `Drone`, `Location`, `Order`.
- `backend/mqtt_bg.py` – Háttér MQTT kliens: feliratkozik a route (`dron/utvonal`) és target (`dron/celpontok`) témákra; target payload érkezésekor a DB-ből kikeresi a helyeket és drónt, átadja az útvonaltervezést a `services/route_planner.py`-nak, és publikálja az eredményt. Cache-eli az utolsó üzenetet/útvonalat, amit a REST és a WebSocket ad vissza.
- `backend/services/route_planner.py` – Útvonaltervezés (haversine távolság, akku/payload modell, töltés a hubban, nearest-neighbour léptetés) és az útvonal lépéseinek MQTT publikálása.
- `backend/optimizer_service.py` – Egyszerűbb rendelés-tervező példa: ellenőrzi, hogy egy megye függőben lévő rendelései beleférnek-e a drón hatótávjába, megjelöli a túl messzi rendeléseket.
- `backend/templates/index.html` – A böngészős UI (Leaflet térkép, űrlapok), REST-ről tölti a megyéket/helyeket, MQTT-n kapja a route lépéseket, a WebSocketen pedig a legutóbbi telemetriát.
- `backend/init_db.py` – Seeder: létrehozza és feltölti az `drone_delivery.db`-t mintamegyékkel, állomásokkal, drónokkal, helyekkel.

## Adatáramlás röviden
- DB (`backend/drone_delivery.db`) ←→ REST végpontok (`backend/main.py`) szolgálják ki a megyék/helyek lekérését és a rendelés mentést.
- UI (`backend/templates/index.html`) REST-en keres megyét/helyet, rendelést küld; MQTT-n route lépéseket kap; WebSocketen a legutóbbi telemetriát.
- MQTT háttér (`backend/mqtt_bg.py`): `dron/celpontok` payloadból DB-olvasás után útvonalat számol (`route_planner.py`), lépésenként publikál a `dron/utvonal` témára, és cache-eli az utolsó üzenetet/útvonalat.

## Telepítés és futtatás (Windows, PowerShell)
1. Lépj a projekt gyökerébe:
   ```powershell
   cd ...\drone-shipping-platform
   ```
2. (Ha van régi, hiányos virtuális környezet, töröld: `Remove-Item -Recurse -Force .\venv`)
3. Hozz létre új virtualenv-et:
   ```powershell
   python -m venv venv
   ```
4. Aktiváld:
   ```powershell
   .\venv\Scripts\activate
   ```
5. Függőségek telepítése:
   ```powershell
   pip install -r backend\requirements.txt
   ```
6. (Opcionális) Környezeti változók beállítása: másold az `.env`-et és szerkeszd, ha kell:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```
7. Adatbázis inicializálása mintadatokkal:
   ```powershell
   python backend\init_db.py
   ```
8. Backend indítása:
   ```powershell
   uvicorn backend.main:app --reload --port 8000
   ```
   Böngészőben: http://127.0.0.1:8000

## Tippek
- Ha az UVicorn “No pyvenv.cfg” hibát ír, hozz létre új `venv`-et a fenti lépésekkel.
- A `.gitignore` már kizárja a virtuális környezetet és az `archive/` mappát.
