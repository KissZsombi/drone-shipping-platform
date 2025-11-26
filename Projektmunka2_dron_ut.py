import matplotlib.pyplot as plt
import math
import paho.mqtt.client as mqtt
import json
import time

# Deprecated: prototype script kept for reference. The live logic now uses SQLAlchemy + backend/services/route_planner.py.

#MQTT BEÁLLÍTÁSOK
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "dron/utvonal"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)
print("MQTT kapcsolat létrejött a HiveMQ brokerrel")


falvak = []
with open('dronoptimalisut.txt', encoding='UTF-8') as be:
    for sor in be:
        sor = sor.strip().split()
        falu = [sor[0], float(sor[1]), float(sor[2])]
        falvak.append(falu)


def tav_glstol(lista):
    GLS_Hungary = [19.160145, 47.340793]
    tavolsag = [lista[0], lista[1]-GLS_Hungary[0], lista[2]-GLS_Hungary[1]]
    return tavolsag


def pontok_tavolsaga(x, y, x2, y2):
    return math.sqrt((x-x2)**2 + (y-y2)**2)


koordinatak = []
y = []
x = []
n = []

for i in falvak:
    koordinatak.append(tav_glstol(i))
    y.append(tav_glstol(i)[2])
    x.append(tav_glstol(i)[1])
    n.append(tav_glstol(i)[0])

with open('kifele.txt', "w", encoding='UTF-8') as ki:
    for i in koordinatak:
        temp = ' '.join(str(y) for y in i)
        print(temp, file=ki)

plt.axhline(y=0, color='r', linestyle='-')
plt.axvline(x=0, color='r', linestyle='-')

plt.scatter(x=x, y=y)
for i, txt in enumerate(n):
    plt.annotate(txt, (x[i], y[i]))
plt.scatter(x=0, y=0)
plt.annotate("GLS Hungary", (0, 0))

sorrend = []


def kovetkezo(elozo):
    min = [100, elozo[0], elozo[1], '']
    for i in range(len(y)):
        if min[0] > pontok_tavolsaga(elozo[1], elozo[2], x[i], y[i]):
            min = [pontok_tavolsaga(elozo[1], elozo[2], x[i], y[i]), x[i], y[i], n[i]]

    sorrend.append(min[3])
    return min


elozo = [0, 0, 0, 'GLS Hungary']

while len(y) != 0:
    try:
        min = kovetkezo(elozo)
        plt.plot([elozo[1], min[1]], [elozo[2], min[2]], color="green")

        message = {
            "previous": elozo[3],
            "next": min[3],
            "coordinates": {"x": min[1], "y": min[2]},
            "distance": round(min[0], 4)
        }
        client.publish(TOPIC, json.dumps(message))
        print(f"MQTT → {message}")
        time.sleep(0.5)  

        y.remove(min[2])
        x.remove(min[1])
        n.remove(min[3])
        elozo = min
    except Exception as e:
        print("Hiba:", e)
        break


route_message = {"route": sorrend}
client.publish(TOPIC, json.dumps(route_message))
print("Teljes útvonal MQTT-re küldve:", sorrend)

with open("utvonal.txt", "w", encoding='UTF-8') as ki:
    for i in sorrend:
        print(i, file=ki)

plt.show()
client.disconnect()
print("MQTT kapcsolat bontva.")
