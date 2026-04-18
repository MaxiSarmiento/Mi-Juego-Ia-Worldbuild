# app.py - Servidor web Flask

from flask import Flask, render_template, request, jsonify, send_from_directory
import random
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from personaje import actualizar_stats
from mundo import actualizar_hora, elegir_npc_aleatorio
from ia import (
    hablar, analizar_cambios, generar_evento, npc_habla,
    npc_decide_acercarse, resumir_memoria,
    generar_entrada_historial, detectar_flags,
    generar_lugares, detectar_movimiento
)
from guardado import guardar_partida, cargar_partida, listar_saves
from historial_narrativo import agregar_entrada
from flags import crear_flags, agregar_flag
from lugares import crear_lugares, moverse_a, lugar_actual
from pathlib import Path

# Ruta base en Documentos
BASE_DIR = Path.home() / "Documents" / "WaifuGame"

SPRITES_DIR = BASE_DIR / "sprites"
BACKGROUNDS_DIR = BASE_DIR / "backgrounds"
SAVES_DIR = BASE_DIR / "saves"

# Crear carpetas si no existen
SPRITES_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
SAVES_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.secret_key = "waifu_game_secret"

estado = {
    "nombre_slot": None,
    "jugador_nombre": None,
    "personaje": None,
    "mundo": None,
    "historial": [],
    "memoria": "",
    "contador_mensajes": 0,
    "contador_resumen": 0,
    "proximo_evento": random.randint(1, 5),
    "proximo_npc": random.randint(2, 6),
    "log_eventos": [],
    "historial_narrativo": [],
    "contador_historial": 0,
    "flags": {},
    "lugares": None,
    "sprites": {},
    "fondos": {},
}

# ---------------------------
# UTILIDADES
# ---------------------------
def sanitizar_nombre(nombre):
    return re.sub(r'[^a-z0-9_]', '', nombre.lower().replace(" ", "_"))


def generar_imagen_pollinations(prompt, ruta_local, intentos=2):
    import urllib.parse
    prompt_encoded = urllib.parse.quote(prompt)
    seed = abs(hash(prompt)) % 10000
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=512&height=768&nologo=true&seed={seed}&model=flux"

    for i in range(intentos):
        try:
            response = requests.get(
                url,
                timeout=45,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "http://localhost:5000"
                }
            )
            if response.status_code == 200 and len(response.content) > 1000:
                with open(ruta_local, "wb") as f:
                    f.write(response.content)
                print(f"✓ Imagen generada: {os.path.basename(ruta_local)}")
                return True
            else:
                print(f"Error {response.status_code}, reintentando...")
                time.sleep(3)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)
    return False



def agregar_evento(tipo, nombre, texto):
    estado["log_eventos"].append({
        "tipo": tipo,
        "nombre": nombre,
        "texto": texto
    })


# ---------------------------
# RUTAS
# ---------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/saves/<path:filename>")
def serve_save(filename):
    return send_from_directory(SAVES_DIR, filename)

@app.route("/api/estado_juego")
def estado_juego():
    if estado["personaje"] is None:
        return jsonify({"iniciado": False})

    lugar = None
    if estado["lugares"] and estado["lugares"].get("actual"):
        lugar = estado["lugares"]["actual"]["nombre"]

    return jsonify({
        "iniciado": True,
        "jugador": estado["jugador_nombre"],
        "personaje": estado["personaje"]["nombre"],
        "stats": estado["personaje"]["stats"],
        "mundo": estado["mundo"]["descripcion"],
        "hora": estado["mundo"]["hora_actual"],
        "lugar_actual": lugar,
        "npcs": [
            {"nombre": n["nombre"], "relacion": n["relacion"]}
            for n in estado["mundo"]["npcs"]
        ]
    })


@app.route("/api/descargar_imagen", methods=["POST"])
def descargar_imagen_ruta():
    datos = request.json
    if not datos or "url" not in datos:
        return jsonify({"ok": False, "error": "datos inválidos"})

    tipo = datos.get("tipo", "sprite")
    nombre = sanitizar_nombre(datos.get("nombre", "img"))
    prompt = datos.get("prompt", "")

    if tipo == "sprite":
        os.makedirs("static/sprites", exist_ok=True)
        ruta = f"static/sprites/{nombre}.png"
    else:
        os.makedirs("static/backgrounds", exist_ok=True)
        ruta = f"static/backgrounds/{nombre}.png"

    # Si ya existe la usamos
    if os.path.exists(ruta) and os.path.getsize(ruta) > 1000:
        return jsonify({"ruta": f"/{ruta}", "ok": True})

    exito = generar_imagen_pollinations(prompt, ruta)

    if exito:
        return jsonify({"ruta": f"/{ruta}", "ok": True})
    return jsonify({"ruta": None, "ok": False})

@app.route("/api/mensaje", methods=["POST"])
def mensaje():
    datos = request.json
    if not datos or "texto" not in datos:
        return jsonify({"ok": False, "error": "mensaje inválido"})

    entrada = datos["texto"]
    eventos_turno = []

    lugares_disp = estado["lugares"]["disponibles"] if estado["lugares"] else []
    lugar = lugar_actual(estado["lugares"])
    lugar_texto = f"{lugar['nombre']}: {lugar['descripcion']}" if lugar else ""

    # Movimiento
    se_mueve, destino = detectar_movimiento(entrada, lugares_disp)
    if se_mueve and destino:
        if moverse_a(estado["lugares"], destino):
            lugar = lugar_actual(estado["lugares"])
            eventos_turno.append({
                "tipo": "mundo",
                "nombre": "🗺️ Narrador",
                "texto": f"Te movés a {lugar['nombre']}. {lugar['descripcion']}"
            })

    # Respuesta personaje
    respuesta = hablar(
        estado["personaje"],
        estado["jugador_nombre"],
        estado["historial"],
        entrada,
        estado["memoria"],
        estado["flags"],
        lugar_texto
    )

    agregar_evento("personaje", estado["personaje"]["nombre"], respuesta)

    eventos_turno.append({
        "tipo": "personaje",
        "nombre": estado["personaje"]["nombre"],
        "texto": respuesta
    })

    # Stats
    cambios = analizar_cambios(
        estado["personaje"],
        estado["jugador_nombre"],
        entrada,
        respuesta
    )
    actualizar_stats(estado["personaje"], cambios)

    estado["contador_mensajes"] += 1
    estado["contador_resumen"] += 1
    estado["contador_historial"] += 1

    # Flags
    clave, descripcion = detectar_flags(
        estado["personaje"],
        estado["jugador_nombre"],
        entrada,
        respuesta,
        estado["flags"]
    )

    if clave:
        if agregar_flag(estado["flags"], clave, descripcion):
            eventos_turno.append({
                "tipo": "sistema",
                "nombre": "📌 Evento",
                "texto": f"Nuevo evento: {descripcion}"
            })

    # Historial narrativo (FIX IMPORTANTE)
    if estado["contador_historial"] >= 6:
        estado["contador_historial"] = 0
        entrada_historial = generar_entrada_historial(
            estado["personaje"],
            estado["jugador_nombre"],
            estado["mundo"],
            estado["historial"],
            estado["memoria"],
            estado["historial_narrativo"]
        )
        agregar_entrada(estado["historial_narrativo"], entrada_historial)

    # Memoria
    if estado["contador_resumen"] >= 8:
        estado["contador_resumen"] = 0
        estado["memoria"] = resumir_memoria(
            estado["historial"],
            estado["memoria"],
            estado["personaje"],
            estado["jugador_nombre"]
        )

    # Evento mundo
    if estado["contador_mensajes"] >= estado["proximo_evento"]:
        estado["contador_mensajes"] = 0
        estado["proximo_evento"] = random.randint(1, 5)

        ultimos = f"{estado['jugador_nombre']}: {entrada}\n{estado['personaje']['nombre']}: {respuesta}"

        evento, nueva_hora = generar_evento(
            estado["mundo"],
            estado["personaje"],
            estado["jugador_nombre"],
            ultimos
        )

        if evento:
            eventos_turno.append({
                "tipo": "mundo",
                "nombre": "🌍 Narrador",
                "texto": evento
            })
            if nueva_hora:
                actualizar_hora(estado["mundo"], nueva_hora)

    return jsonify({
        "eventos": eventos_turno,
        "stats": estado["personaje"]["stats"],
        "hora": estado["mundo"]["hora_actual"]
    })


@app.route("/api/responder_npc", methods=["POST"])
def responder_npc():
    datos = request.json
    if not datos or "npc_id" not in datos:
        return jsonify({"ok": False, "error": "npc inválido"})

    npc_id = datos["npc_id"]
    if npc_id >= len(estado["mundo"]["npcs"]):
        return jsonify({"ok": False, "error": "npc fuera de rango"})

    npc = estado["mundo"]["npcs"][npc_id]

    respuesta_npc = npc_habla(
        npc,
        estado["jugador_nombre"],
        estado["personaje"],
        estado["mundo"],
        datos.get("texto", "")
    )

    reaccion = hablar(
        estado["personaje"],
        estado["jugador_nombre"],
        estado["historial"],
        f"[{npc['nombre']} dijo: '{datos.get('texto', '')}']",
        estado["memoria"],
        estado["flags"]
    )

    return jsonify({
        "npc_respuesta": {"nombre": npc["nombre"], "texto": respuesta_npc},
        "personaje_reaccion": {
            "nombre": estado["personaje"]["nombre"],
            "texto": reaccion
        }
    })


@app.route("/api/lugares")
def get_lugares():
    if not estado["lugares"]:
        return jsonify({"lugares": [], "actual": None})

    actual = estado["lugares"]["actual"]["nombre"] if estado["lugares"]["actual"] else None

    return jsonify({
        "lugares": estado["lugares"]["disponibles"],
        "actual": actual
    })

@app.route("/sprites/<filename>")
def serve_sprite(filename):
    return send_from_directory(SPRITES_DIR, filename)

@app.route("/backgrounds/<filename>")
def serve_background(filename):
    return send_from_directory(BACKGROUNDS_DIR, filename)

def descargar_imagen(url, ruta_local, intentos=3):
    # 🧠 CACHE: si ya existe, no descargar de nuevo
    if os.path.exists(ruta_local):
        return True

    for i in range(intentos):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(ruta_local, "wb") as f:
                    f.write(response.content)
                return True
        except:
            time.sleep(2)
    return False

def generar_sprite(expresion, apariencia):
    try:
        nombre_archivo = sanitizar_nombre(expresion)
        ruta = SPRITES_DIR / f"{nombre_archivo}.png"

        prompt = f"""
        anime girl, {apariencia},
        {expresion} expression,
        unique character design,
        distinct face, different eye color, varied features,
        visual novel style, portrait
        """
        seed = ord(expresion[0]) * 100

        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=400&height=600&nologo=true&seed={seed}"

        if descargar_imagen(url, ruta):
            return expresion, f"/sprites/{nombre_archivo}.png"

        return expresion, None

    except Exception as e:
        print(f"Error sprite {expresion}: {e}")
        return expresion, None

def generar_sprites_paralelo(apariencia):
    expresiones = ["neutral", "happy", "sad", "angry", "surprised", "crying"]
    resultados = {}

    os.makedirs("static/sprites", exist_ok=True)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(generar_sprite, exp, apariencia)
            for exp in expresiones
        ]

        for future in as_completed(futures):
            exp, ruta = future.result()
            if ruta:
                resultados[exp] = ruta

    return resultados

def generar_fondo(lugar, mundo_desc):
    try:
        nombre = sanitizar_nombre(lugar["nombre"])
        ruta = BACKGROUNDS_DIR / f"{nombre}.png"

        prompt = f"{lugar['descripcion']}, {mundo_desc}, anime background, visual novel style"
        seed = sum(ord(c) for c in lugar["nombre"])

        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1200&height=800&nologo=true&seed={seed}"

        if descargar_imagen(url, ruta):
            return lugar["nombre"], f"/backgrounds/{nombre}.png"

        return lugar["nombre"], None

    except Exception as e:
        print(f"Error fondo {lugar['nombre']}: {e}")
        return lugar["nombre"], None

def generar_fondos_paralelo(lugares, mundo_desc):
    resultados = {}

    os.makedirs("static/backgrounds", exist_ok=True)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(generar_fondo, lugar, mundo_desc)
            for lugar in lugares
        ]

        for future in as_completed(futures):
            nombre, ruta = future.result()
            if ruta:
                resultados[nombre] = ruta

    return resultados
@app.route("/api/guardar", methods=["POST"])
def guardar():
    slot = guardar_partida(
        estado["jugador_nombre"],
        estado["personaje"],
        estado["mundo"],
        estado["historial"],
        estado["memoria"],
        estado["historial_narrativo"],
        estado["flags"],
        estado["lugares"],
        estado.get("sprites", {}),
        estado.get("fondos", {}),
        estado.get("nombre_slot")
    )

    estado["nombre_slot"] = slot
    return jsonify({"ok": True, "slot": slot})


@app.route("/api/saves")
def get_saves():
    return jsonify({"saves": listar_saves()})

@app.route("/api/generar_imagenes", methods=["POST"])
def generar_imagenes():
    datos = request.json
    apariencia = datos.get("apariencia", "")
    mundo_desc = datos.get("mundo", "")
    lugares = datos.get("lugares", [])

    sprites = generar_sprites_paralelo(apariencia)
    fondos = generar_fondos_paralelo(lugares, mundo_desc)

    # Guardamos en estado global
    estado["sprites"] = sprites
    estado["fondos"] = fondos

    return jsonify({
        "ok": True,
        "sprites": sprites,
        "fondos": fondos
    })
@app.route("/api/cargar_save", methods=["POST"])
def cargar_save():
    datos = request.json
    if not datos or "slot" not in datos:
        return jsonify({"ok": False})

    partida = cargar_partida(datos["slot"])
    if not partida:
        return jsonify({"ok": False})

    estado.update({
        "jugador_nombre": partida["jugador_nombre"],
        "personaje": partida["personaje"],
        "mundo": partida["mundo"],
        "historial": partida["historial"],
        "memoria": partida.get("memoria", ""),
        "historial_narrativo": partida.get("historial_narrativo", []),
        "flags": partida.get("flags", {}),
        "lugares": partida.get("lugares"),
        "apariencia": partida["personaje"]["apariencia"],
        "sprites": partida.get("sprites", {}),
        "fondos": partida.get("fondos", {}),
        "nombre_slot": datos["slot"],
        "log_eventos": [],
        "contador_mensajes": 0,
        "contador_resumen": 0,
        "contador_historial": 0,
        "proximo_evento": 3,
        "proximo_npc": 4
    })


    return jsonify({
        "ok": True,
        "datos": {
            "personaje": partida["personaje"]["nombre"],
            "jugador": partida["jugador_nombre"],
            "sprites": estado["sprites"],
            "fondos": estado["fondos"]
        }
    })

@app.route("/api/historial_narrativo")
def get_historial_narrativo():
    return jsonify({"entradas": estado["historial_narrativo"]})
@app.route("/api/historial_chat")
def get_historial_chat():
    # Devuelve solo los últimos 50 mensajes para no saturar
    historial = estado["historial"][-50:]
    return jsonify({"historial": historial})

@app.route("/api/flags")
def get_flags():
    return jsonify({"flags": estado["flags"]})


@app.route("/api/introduccion")
def get_introduccion():
    from ia import generar_introduccion
    intro = generar_introduccion(
        estado["mundo"],
        estado["personaje"],
        estado["jugador_nombre"],
        estado["lugares"]
    )
    return jsonify({"introduccion": intro})


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    datos = request.json
    jugador_nombre = datos["jugador_nombre"]
    personaje = datos["personaje"]
    contexto = datos["contexto_mundo"]
    npc_genero = datos.get("npc_genero", "female")
    estado["jugador_nombre"] = jugador_nombre
    estado["personaje"] = personaje
    estado["historial"] = []
    estado["memoria"] = ""
    estado["log_eventos"] = []
    estado["historial_narrativo"] = []
    estado["flags"] = crear_flags()
    estado["contador_mensajes"] = 0
    estado["contador_resumen"] = 0
    estado["contador_historial"] = 0
    estado["proximo_evento"] = random.randint(1, 5)
    estado["proximo_npc"] = random.randint(2, 6)
    estado["sprites"] = {}
    estado["fondos"] = {}
    estado["nombre_slot"] = None

    from ia import generar_mundo
    from mundo import crear_mundo
    print(f"⏳ Generando mundo: {contexto}")
    descripcion, npcs = generar_mundo(contexto, personaje, jugador_nombre, npc_genero)
    estado["mundo"] = crear_mundo(contexto, descripcion, npcs)

    from ia import generar_stats_iniciales

    personaje = datos["personaje"]

    # ⚡ Generar stats dinámicos
    personaje["stats"] = generar_stats_iniciales(personaje)

    print("⏳ Generando lugares...")
    lista_lugares = generar_lugares(
        contexto,
        estado["mundo"]["descripcion"],
        personaje,
        jugador_nombre
    )
    estado["lugares"] = crear_lugares(lista_lugares)
    print("✨ Lugares generados")

    agregar_evento("sistema", "Narrador", estado["mundo"]["descripcion"])
    # Limpiar sprites y fondos viejos para la nueva partida
    import shutil
    if os.path.exists("static/sprites"):
        shutil.rmtree("static/sprites")
    if os.path.exists("static/backgrounds"):
        shutil.rmtree("static/backgrounds")
    os.makedirs("static/sprites", exist_ok=True)
    os.makedirs("static/backgrounds", exist_ok=True)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)