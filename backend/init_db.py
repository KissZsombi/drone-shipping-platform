from __future__ import annotations

from contextlib import contextmanager
from typing import Dict
import random

from sqlalchemy.exc import IntegrityError

from backend.db import Base, SessionLocal, engine
from backend import models


COUNTY_SEED = [
    {"name": "Budapest", "lat": 47.4979, "lon": 19.0402, "base_range_km": 200.0, "max_payload_kg": 5.0},
    {"name": "Bacs-Kiskun", "lat": 46.9062, "lon": 19.6913, "base_range_km": 195.0, "max_payload_kg": 5.0},
    {"name": "Bekes", "lat": 46.6833, "lon": 21.1000, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Hajdu-Bihar", "lat": 47.5316, "lon": 21.6273, "base_range_km": 205.0, "max_payload_kg": 5.5},
    {"name": "Jasz-Nagykun-Szolnok", "lat": 47.1833, "lon": 20.2000, "base_range_km": 195.0, "max_payload_kg": 5.0},
    {"name": "Szabolcs-Szatmar-Bereg", "lat": 47.9554, "lon": 21.7167, "base_range_km": 200.0, "max_payload_kg": 5.0},
    {"name": "Baranya", "lat": 46.0727, "lon": 18.2323, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Fejer", "lat": 47.1860, "lon": 18.4221, "base_range_km": 195.0, "max_payload_kg": 5.0},
    {"name": "Gyor-Moson-Sopron", "lat": 47.6875, "lon": 17.6504, "base_range_km": 210.0, "max_payload_kg": 6.0},
    {"name": "Komarom-Esztergom", "lat": 47.5849, "lon": 18.3933, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Somogy", "lat": 46.3667, "lon": 17.8000, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Tolna", "lat": 46.3501, "lon": 18.7091, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Vas", "lat": 47.2307, "lon": 16.6218, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Veszprem", "lat": 47.0933, "lon": 17.9115, "base_range_km": 195.0, "max_payload_kg": 5.0},
    {"name": "Zala", "lat": 46.8417, "lon": 16.8456, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Borsod-Abauj-Zemplen", "lat": 48.1031, "lon": 20.7783, "base_range_km": 205.0, "max_payload_kg": 5.5},
    {"name": "Heves", "lat": 47.9026, "lon": 20.3733, "base_range_km": 190.0, "max_payload_kg": 5.0},
    {"name": "Nograd", "lat": 48.0935, "lon": 19.7999, "base_range_km": 185.0, "max_payload_kg": 4.5},
    {"name": "Csongrad-Csanad", "lat": 46.2530, "lon": 20.1414, "base_range_km": 195.0, "max_payload_kg": 5.0},
    {"name": "Pest", "lat": 47.5309, "lon": 19.2614, "base_range_km": 185.0, "max_payload_kg": 4.5},
]


LOCATION_SEED = [
    # Budapest
    {"name": "Budapest I. kerulet", "county": "Budapest", "lat": 47.4979, "lon": 19.0402},
    {"name": "Budapest II. kerulet", "county": "Budapest", "lat": 47.5190, "lon": 19.0220},
    {"name": "Budapest III. kerulet", "county": "Budapest", "lat": 47.5410, "lon": 19.0450},
    {"name": "Budapest XI. kerulet", "county": "Budapest", "lat": 47.4740, "lon": 19.0470},
    {"name": "Budapest XIII. kerulet", "county": "Budapest", "lat": 47.5280, "lon": 19.0720},
    {"name": "Budapest XIV. kerulet", "county": "Budapest", "lat": 47.5100, "lon": 19.1080},

    # Bacs-Kiskun
    {"name": "Kecskemet", "county": "Bacs-Kiskun", "lat": 46.9062, "lon": 19.6913},
    {"name": "Baja", "county": "Bacs-Kiskun", "lat": 46.1823, "lon": 18.9560},
    {"name": "Kalocsa", "county": "Bacs-Kiskun", "lat": 46.5310, "lon": 18.9856},
    {"name": "Kiskunfelegyhaza", "county": "Bacs-Kiskun", "lat": 46.7120, "lon": 19.8520},
    {"name": "Kiskunhalas", "county": "Bacs-Kiskun", "lat": 46.4343, "lon": 19.4844},
    {"name": "Kiskoros", "county": "Bacs-Kiskun", "lat": 46.6215, "lon": 19.2872},

    # Baranya
    {"name": "Pecs", "county": "Baranya", "lat": 46.0727, "lon": 18.2323},
    {"name": "Komlo", "county": "Baranya", "lat": 46.1919, "lon": 18.2647},
    {"name": "Mohacs", "county": "Baranya", "lat": 45.9931, "lon": 18.6835},
    {"name": "Szigetvar", "county": "Baranya", "lat": 46.0486, "lon": 17.8052},
    {"name": "Siklos", "county": "Baranya", "lat": 45.8549, "lon": 18.2972},
    {"name": "Harkany", "county": "Baranya", "lat": 45.8482, "lon": 18.2365},

    # Bekes
    {"name": "Bekescsaba", "county": "Bekes", "lat": 46.6720, "lon": 21.0870},
    {"name": "Gyula", "county": "Bekes", "lat": 46.6500, "lon": 21.2833},
    {"name": "Bekes", "county": "Bekes", "lat": 46.7666, "lon": 21.1333},
    {"name": "Oroshaza", "county": "Bekes", "lat": 46.5667, "lon": 20.6667},
    {"name": "Szarvas", "county": "Bekes", "lat": 46.8667, "lon": 20.5500},
    {"name": "Szeghalom", "county": "Bekes", "lat": 47.0333, "lon": 21.1667},

    # Borsod-Abauj-Zemplen
    {"name": "Miskolc", "county": "Borsod-Abauj-Zemplen", "lat": 48.1031, "lon": 20.7783},
    {"name": "Ozd", "county": "Borsod-Abauj-Zemplen", "lat": 48.2191, "lon": 20.3005},
    {"name": "Kazincbarcika", "county": "Borsod-Abauj-Zemplen", "lat": 48.2526, "lon": 20.6394},
    {"name": "Satoraljaujhely", "county": "Borsod-Abauj-Zemplen", "lat": 48.3954, "lon": 21.6676},
    {"name": "Mezokovesd", "county": "Borsod-Abauj-Zemplen", "lat": 47.8100, "lon": 20.5670},
    {"name": "Tiszaujvaros", "county": "Borsod-Abauj-Zemplen", "lat": 47.9333, "lon": 21.0833},

    # Csongrad-Csanad
    {"name": "Szeged", "county": "Csongrad-Csanad", "lat": 46.2530, "lon": 20.1414},
    {"name": "Hodmezovasarhely", "county": "Csongrad-Csanad", "lat": 46.4167, "lon": 20.3333},
    {"name": "Mako", "county": "Csongrad-Csanad", "lat": 46.2167, "lon": 20.4833},
    {"name": "Szentes", "county": "Csongrad-Csanad", "lat": 46.6500, "lon": 20.2667},
    {"name": "Morahalom", "county": "Csongrad-Csanad", "lat": 46.2167, "lon": 19.8833},
    {"name": "Kistelek", "county": "Csongrad-Csanad", "lat": 46.4854, "lon": 19.9746},

    # Fejer
    {"name": "Szekesfehervar", "county": "Fejer", "lat": 47.1860, "lon": 18.4221},
    {"name": "Dunaujvaros", "county": "Fejer", "lat": 46.9667, "lon": 18.9333},
    {"name": "Bicske", "county": "Fejer", "lat": 47.4833, "lon": 18.6333},
    {"name": "Enying", "county": "Fejer", "lat": 46.9333, "lon": 18.2500},
    {"name": "Martonvasar", "county": "Fejer", "lat": 47.3167, "lon": 18.7833},
    {"name": "Sarbogard", "county": "Fejer", "lat": 46.8825, "lon": 18.6208},

    # Gyor-Moson-Sopron
    {"name": "Gyor", "county": "Gyor-Moson-Sopron", "lat": 47.6875, "lon": 17.6504},
    {"name": "Mosonmagyarovar", "county": "Gyor-Moson-Sopron", "lat": 47.8672, "lon": 17.2690},
    {"name": "Sopron", "county": "Gyor-Moson-Sopron", "lat": 47.6817, "lon": 16.5845},
    {"name": "Csorna", "county": "Gyor-Moson-Sopron", "lat": 47.6100, "lon": 17.2460},
    {"name": "Kapvar", "county": "Gyor-Moson-Sopron", "lat": 47.5918, "lon": 17.0289},
    {"name": "Pannonhalma", "county": "Gyor-Moson-Sopron", "lat": 47.5460, "lon": 17.7610},

    # Hajdu-Bihar
    {"name": "Debrecen", "county": "Hajdu-Bihar", "lat": 47.5316, "lon": 21.6273},
    {"name": "Hajduszoboszlo", "county": "Hajdu-Bihar", "lat": 47.4500, "lon": 21.4000},
    {"name": "Hajduboszormeny", "county": "Hajdu-Bihar", "lat": 47.6713, "lon": 21.5086},
    {"name": "Balmazujvaros", "county": "Hajdu-Bihar", "lat": 47.6167, "lon": 21.3500},
    {"name": "Berettyoujfalu", "county": "Hajdu-Bihar", "lat": 47.2167, "lon": 21.5333},
    {"name": "Puspokladany", "county": "Hajdu-Bihar", "lat": 47.3167, "lon": 21.1167},

    # Heves
    {"name": "Eger", "county": "Heves", "lat": 47.9026, "lon": 20.3733},
    {"name": "Gyongyos", "county": "Heves", "lat": 47.7833, "lon": 19.9333},
    {"name": "Hatvan", "county": "Heves", "lat": 47.6667, "lon": 19.6833},
    {"name": "Fuzesabony", "county": "Heves", "lat": 47.7500, "lon": 20.4000},
    {"name": "Heves", "county": "Heves", "lat": 47.6000, "lon": 20.2833},
    {"name": "Recsk", "county": "Heves", "lat": 47.9333, "lon": 20.1167},

    # Jasz-Nagykun-Szolnok
    {"name": "Szolnok", "county": "Jasz-Nagykun-Szolnok", "lat": 47.1833, "lon": 20.2000},
    {"name": "Jaszbereny", "county": "Jasz-Nagykun-Szolnok", "lat": 47.5000, "lon": 19.9167},
    {"name": "Karcag", "county": "Jasz-Nagykun-Szolnok", "lat": 47.3167, "lon": 20.9333},
    {"name": "Tiszafured", "county": "Jasz-Nagykun-Szolnok", "lat": 47.6167, "lon": 20.7667},
    {"name": "Mezotur", "county": "Jasz-Nagykun-Szolnok", "lat": 47.0000, "lon": 20.6333},
    {"name": "Kunhegyes", "county": "Jasz-Nagykun-Szolnok", "lat": 47.3667, "lon": 20.6333},

    # Komarom-Esztergom
    {"name": "Tatabanya", "county": "Komarom-Esztergom", "lat": 47.5849, "lon": 18.3933},
    {"name": "Komarom", "county": "Komarom-Esztergom", "lat": 47.7433, "lon": 18.1197},
    {"name": "Esztergom", "county": "Komarom-Esztergom", "lat": 47.7860, "lon": 18.7430},
    {"name": "Oroszlany", "county": "Komarom-Esztergom", "lat": 47.4862, "lon": 18.3122},
    {"name": "Dorog", "county": "Komarom-Esztergom", "lat": 47.7207, "lon": 18.7379},
    {"name": "Nyergesujfalu", "county": "Komarom-Esztergom", "lat": 47.7610, "lon": 18.5550},

    # Nograd
    {"name": "Salgotarjan", "county": "Nograd", "lat": 48.0935, "lon": 19.7999},
    {"name": "Balassagyarmat", "county": "Nograd", "lat": 48.0750, "lon": 19.3000},
    {"name": "Paszto", "county": "Nograd", "lat": 47.9167, "lon": 19.7000},
    {"name": "Szecseny", "county": "Nograd", "lat": 48.0833, "lon": 19.5167},
    {"name": "Retsag", "county": "Nograd", "lat": 47.9333, "lon": 19.1333},
    {"name": "Batonterenye", "county": "Nograd", "lat": 48.0167, "lon": 19.8333},

    # Pest
    {"name": "Erd", "county": "Pest", "lat": 47.3917, "lon": 18.9130},
    {"name": "Szentendre", "county": "Pest", "lat": 47.6737, "lon": 19.0716},
    {"name": "Vac", "county": "Pest", "lat": 47.7759, "lon": 19.1361},
    {"name": "Godollo", "county": "Pest", "lat": 47.5966, "lon": 19.3552},
    {"name": "Cegled", "county": "Pest", "lat": 47.1726, "lon": 19.7998},
    {"name": "Dunakeszi", "county": "Pest", "lat": 47.6364, "lon": 19.1424},

    # Somogy
    {"name": "Kaposvar", "county": "Somogy", "lat": 46.3667, "lon": 17.8000},
    {"name": "Siofok", "county": "Somogy", "lat": 46.9062, "lon": 18.0520},
    {"name": "Marcali", "county": "Somogy", "lat": 46.5833, "lon": 17.4000},
    {"name": "Fonyod", "county": "Somogy", "lat": 46.7500, "lon": 17.5833},
    {"name": "Nagyatad", "county": "Somogy", "lat": 46.2333, "lon": 17.3667},
    {"name": "Barcs", "county": "Somogy", "lat": 45.9600, "lon": 17.4600},

    # Szabolcs-Szatmar-Bereg
    {"name": "Nyiregyhaza", "county": "Szabolcs-Szatmar-Bereg", "lat": 47.9554, "lon": 21.7167},
    {"name": "Kisvarda", "county": "Szabolcs-Szatmar-Bereg", "lat": 48.2167, "lon": 22.0833},
    {"name": "Mateszalka", "county": "Szabolcs-Szatmar-Bereg", "lat": 47.9550, "lon": 22.3270},
    {"name": "Fehergyarmat", "county": "Szabolcs-Szatmar-Bereg", "lat": 47.9865, "lon": 22.5203},
    {"name": "Vasarosnameny", "county": "Szabolcs-Szatmar-Bereg", "lat": 48.1258, "lon": 22.3139},
    {"name": "Tiszavasvari", "county": "Szabolcs-Szatmar-Bereg", "lat": 47.9667, "lon": 21.3667},

    # Tolna
    {"name": "Szekszard", "county": "Tolna", "lat": 46.3501, "lon": 18.7091},
    {"name": "Paks", "county": "Tolna", "lat": 46.6333, "lon": 18.8500},
    {"name": "Dombovar", "county": "Tolna", "lat": 46.3833, "lon": 18.1333},
    {"name": "Bonyhad", "county": "Tolna", "lat": 46.3000, "lon": 18.5333},
    {"name": "Tolna", "county": "Tolna", "lat": 46.4167, "lon": 18.7833},
    {"name": "Tamasi", "county": "Tolna", "lat": 46.6333, "lon": 18.2833},

    # Vas
    {"name": "Szombathely", "county": "Vas", "lat": 47.2307, "lon": 16.6218},
    {"name": "Kormend", "county": "Vas", "lat": 47.0110, "lon": 16.6050},
    {"name": "Sarvar", "county": "Vas", "lat": 47.2539, "lon": 16.9358},
    {"name": "Celldomolk", "county": "Vas", "lat": 47.2630, "lon": 17.1501},
    {"name": "Csepreg", "county": "Vas", "lat": 47.4100, "lon": 16.7080},
    {"name": "Koszeg", "county": "Vas", "lat": 47.3893, "lon": 16.5404},

    # Veszprem
    {"name": "Veszprem", "county": "Veszprem", "lat": 47.0933, "lon": 17.9115},
    {"name": "Papa", "county": "Veszprem", "lat": 47.3300, "lon": 17.4667},
    {"name": "Ajka", "county": "Veszprem", "lat": 47.1019, "lon": 17.5582},
    {"name": "Balatonalmadi", "county": "Veszprem", "lat": 47.0333, "lon": 18.0167},
    {"name": "Balatonfured", "county": "Veszprem", "lat": 46.9619, "lon": 17.8719},
    {"name": "Tapolca", "county": "Veszprem", "lat": 46.8800, "lon": 17.4400},

    # Zala
    {"name": "Zalaegerszeg", "county": "Zala", "lat": 46.8417, "lon": 16.8456},
    {"name": "Nagykanizsa", "county": "Zala", "lat": 46.4530, "lon": 16.9910},
    {"name": "Keszthely", "county": "Zala", "lat": 46.7681, "lon": 17.2474},
    {"name": "Letenye", "county": "Zala", "lat": 46.4333, "lon": 16.7333},
    {"name": "Lenti", "county": "Zala", "lat": 46.6263, "lon": 16.5336},
    {"name": "Zalaszentgrot", "county": "Zala", "lat": 46.9448, "lon": 17.0790},
]


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_data() -> None:
    if Base.metadata.tables == {}:
        raise RuntimeError("Metadata not configured before seeding.")

    Base.metadata.create_all(bind=engine)

    with session_scope() as session:
        if session.query(models.County).count() > 0:
            print("Database already contains data; skipping seed records.")
            return

        county_lookup: Dict[str, models.County] = {}

        # Counties + stations + drones
        for entry in COUNTY_SEED:
            county = models.County(name=entry["name"])
            station = models.Station(
                name=f"{entry['name']} Hub",
                lat=entry["lat"],
                lon=entry["lon"],
                county=county,
            )
            drone = models.Drone(
                base_range_km=entry["base_range_km"],
                max_payload_kg=entry["max_payload_kg"],
                speed_kmh=round(random.uniform(50.0, 90.0), 1),
                station=station,
            )
            session.add_all([county, station, drone])
            county_lookup[county.name] = county

        # Locations
        for loc in LOCATION_SEED:
            county = county_lookup.get(loc["county"])
            if not county:
                continue

            session.add(
                models.Location(
                    name=loc["name"],
                    lat=loc["lat"],
                    lon=loc["lon"],
                    county=county,
                )
            )

        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise RuntimeError(f"Failed to insert seed data: {exc}") from exc

    print("Database initialized with seed data.")


if __name__ == "__main__":
    seed_data()
