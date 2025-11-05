import matplotlib.pyplot as plt
import math


falvak = []
with open('dronoptimalisut.txt', encoding='UTF-8') as be:
    for sor in be:
        sor = sor.strip().split()
        falu= [sor[0], float(sor[1]), float(sor[2])]
        falvak.append(falu)


def tav_glstol(lista):
    #nagybetű, szóval konstans megállapodás alapján
    GLS_Hungary = [19.160145, 47.340793]
    tavolsag = [lista[0], lista[1]-GLS_Hungary[0], lista[2]-GLS_Hungary[1]]
    return tavolsag

def pontok_tavolsaga(x, y, x2, y2,):
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


#Descartes-kr
plt.axhline(y=0, color='r', linestyle='-')
plt.axvline(x=0, color='r', linestyle='-')

plt.scatter(x=x,y=y)
for i, txt in enumerate(n):
    plt.annotate(txt, (x[i], y[i]))
plt.scatter(x=0, y=0)
plt.annotate("GLS Hungary",(0,0))


sorrend= list()
def kovetkezo(elozo):
    min = [100,elozo[0], elozo[1], '']

    for i in range(len(y)):
        if min[0] > pontok_tavolsaga(elozo[1], elozo[2], x[i], y[i]):
            min = [pontok_tavolsaga(elozo[1], elozo[2], x[i], y[i]), x[i], y[i], n[i]]

    sorrend.append(min[3])
    return(min)

elozo = [0, 0, 0, '']
while(len(y)!= 0):
    try:
        min = kovetkezo(elozo)
        plt.plot([elozo[1],min[1]], [elozo[2],min[2]], color="green")

        y.remove(min[2])
        x.remove(min[1])
        n.remove(min[3])
        elozo = min
    except:
        pass

print(sorrend)
with open("utvonal.txt", "w", encoding='UTF-8') as ki:
    for i in sorrend:
        print(i, file=ki)
plt.show()