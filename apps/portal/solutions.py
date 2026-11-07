"""Robot va Xato ovchisi yechimlari. Brauzerga faqat o'quvchi 3 marta urinib, yechimni so'raganda boradi."""

ORQAGA = "def orqaga():\n    chapga()\n    chapga()\n"
ONG_QOL = """
while not yetib_keldi():
    if not ongda_devor():
        ongga()
        {step}
    elif not oldinda_devor():
        {step}
    else:
        chapga()
"""
QADAM = "def qadam():\n    yur()\n    if kristall_bor():\n        ol()\n"

SOLUTIONS = {
    "salom-robot": "yur()\n" * 4,
    "birinchi-kristall": "yur()\nyur()\nol()\nyur()\nyur()\n",
    "burilish": "yur()\nyur()\nongga()\nyur()\nyur()\nchapga()\nyur()\n",
    "ilon-yol": "yur()\nyur()\nol()\nongga()\nyur()\nyur()\nol()\nchapga()\nyur()\nyur()\n",
    "uzun-yol": "for i in range(10):\n    yur()\n",
    "kristall-qatori": "for i in range(6):\n    yur()\n    ol()\nyur()\n",
    "kvadrat": "for i in range(3):\n    yur()\n    yur()\n    yur()\n    ol()\n    ongga()\nyur()\n",
    "zinapoya": "for i in range(4):\n    yur()\n    ongga()\n    yur()\n    chapga()\n",
    "ichma-ich": """
for i in range(3):
    yur()
    ongga()
    for j in range(2):
        yur()
    ol()
    for j in range(2):
        chapga()
    for j in range(2):
        yur()
    ongga()
    yur()
""",
    "orqaga-qayt": ORQAGA
    + """
for i in range(3):
    yur()
ol()
orqaga()
for i in range(6):
    yur()
ol()
orqaga()
for i in range(4):
    yur()
""",
    "ikki-qator": """
def qator():
    for i in range(5):
        yur()
        ol()

qator()
ongga()
yur()
yur()
ongga()
qator()
ongga()
yur()
""",
    "parametr": """
def qadam(n):
    for i in range(n):
        yur()

qadam(6)
ongga()
qadam(4)
ongga()
qadam(6)
ongga()
qadam(2)
ongga()
qadam(3)
""",
    "minoralar": """
def minora(n):
    chapga()
    for i in range(n):
        yur()
    ol()
    chapga()
    chapga()
    for i in range(n):
        yur()
    chapga()

yur()
minora(1)
yur()
yur()
minora(3)
yur()
yur()
minora(2)
yur()
""",
    "bormi": "for i in range(6):\n    yur()\n    if kristall_bor():\n        ol()\n",
    "devor-oldida": "for i in range(6):\n    if oldinda_devor():\n        ongga()\n    yur()\n",
    "chap-yoki-ong": """
for i in range(8):
    if oldinda_devor():
        if chapda_devor():
            ongga()
        else:
            chapga()
    yur()
""",
    "aqlli-qadam": QADAM
    + """
for i in range(4):
    qadam()
ongga()
for i in range(2):
    qadam()
ongga()
for i in range(4):
    qadam()
""",
    "devorgacha": "while not oldinda_devor():\n    yur()\n",
    "manzilgacha": "while not yetib_keldi():\n    yur()\n",
    "kristall-ovi": "while not oldinda_devor():\n    yur()\n    if kristall_bor():\n        ol()\n",
    "ong-qol": ONG_QOL.format(step="yur()"),
    "yarim-yol": """
qadam = 0
while not oldinda_devor():
    yur()
    qadam = qadam + 1
ol()
chapga()
chapga()
for i in range(qadam // 2):
    yur()
""",
    "osuvchi-spiral": """
n = 1
for i in range(5):
    for j in range(n):
        yur()
    ongga()
    n = n + 1
""",
    "sanab-ber": """
def yigish():
    soni = 0
    while not oldinda_devor():
        yur()
        if kristall_bor():
            ol()
            soni = soni + 1
    return soni

k = yigish()
ongga()
for i in range(k):
    yur()
""",
    "katta-sinov": QADAM + ONG_QOL.format(step="qadam()"),
}

FIXES = {
    "xato-son": "for i in range(4):\n    yur()\n",
    "xato-surilish": "for i in range(6):\n    yur()\n    ol()\nyur()\n",
    "xato-tomon": "yur()\nyur()\nongga()\nyur()\nyur()\nchapga()\nyur()\n",
    "xato-shart": "for i in range(6):\n    yur()\n    if kristall_bor():\n        ol()\n",
    "xato-chaqiruv": "def yetkaz():\n    for i in range(4):\n        yur()\nyetkaz()\n",
    "xato-cheksiz": "n = 0\nwhile n < 3:\n    yur()\n    n = n + 1\n",
}
