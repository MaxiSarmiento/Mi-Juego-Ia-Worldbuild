# guardado.py - Sistema de guardado

import json
import shutil
from datetime import datetime
from pathlib import Path

# 📁 Base en Documentos
BASE_DIR = Path.home() / "Documents" / "WaifuGame"
SAVES_DIR = BASE_DIR / "saves"
SPRITES_DIR = BASE_DIR / "sprites"
BACKGROUNDS_DIR = BASE_DIR / "backgrounds"

SAVES_DIR.mkdir(parents=True, exist_ok=True)


def nombre_save(personaje_nombre):
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    nombre = personaje_nombre.lower().replace(" ", "_")
    return f"{nombre}_{fecha}"


def guardar_partida(
    jugador_nombre, personaje, mundo, historial, memoria,
    historial_narrativo, flags, lugares, sprites, fondos, nombre_slot=None
):
    if not nombre_slot:
        nombre_slot = nombre_save(personaje["nombre"])

    carpeta = SAVES_DIR / nombre_slot
    carpeta_sprites = carpeta / "sprites"
    carpeta_fondos = carpeta / "backgrounds"

    carpeta_sprites.mkdir(parents=True, exist_ok=True)
    carpeta_fondos.mkdir(parents=True, exist_ok=True)

    sprites_guardados = {}
    fondos_guardados = {}

    # -------------------
    # 🧍 SPRITES
    # -------------------
    for exp, ruta in sprites.items():
        try:
            # "/sprites/neutral.png" → "neutral.png"
            nombre_archivo = Path(ruta).name
            origen = SPRITES_DIR / nombre_archivo

            if origen.exists():
                destino = carpeta_sprites / nombre_archivo
                shutil.copy(origen, destino)

                sprites_guardados[exp] = f"/saves/{nombre_slot}/sprites/{nombre_archivo}"
                print(f"✓ Sprite guardado: {nombre_archivo}")
            else:
                print(f"✗ Sprite no encontrado: {origen}")
                sprites_guardados[exp] = ruta

        except Exception as e:
            print(f"Error sprite {exp}: {e}")
            sprites_guardados[exp] = ruta

    # -------------------
    # 🌄 FONDOS
    # -------------------
    for lugar, ruta in fondos.items():
        try:
            nombre_archivo = Path(ruta).name
            origen = BACKGROUNDS_DIR / nombre_archivo

            if origen.exists():
                destino = carpeta_fondos / nombre_archivo
                shutil.copy(origen, destino)

                fondos_guardados[lugar] = f"/saves/{nombre_slot}/backgrounds/{nombre_archivo}"
                print(f"✓ Fondo guardado: {nombre_archivo}")
            else:
                print(f"✗ Fondo no encontrado: {origen}")
                fondos_guardados[lugar] = ruta

        except Exception as e:
            print(f"Error fondo {lugar}: {e}")
            fondos_guardados[lugar] = ruta

    # -------------------
    # 💾 JSON
    # -------------------
    datos = {
        "nombre_slot": nombre_slot,
        "jugador_nombre": jugador_nombre,
        "personaje": personaje,
        "mundo": mundo,
        "historial": historial,
        "memoria": memoria,
        "historial_narrativo": historial_narrativo,
        "flags": flags,
        "lugares": lugares,
        "sprites": sprites_guardados,
        "fondos": fondos_guardados
    }

    ruta_json = carpeta / "partida.json"
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"💾 Partida guardada en: {carpeta}")
    return nombre_slot


def cargar_partida(nombre_slot):
    ruta = SAVES_DIR / nombre_slot / "partida.json"

    if not ruta.exists():
        return None

    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)

    print(f"📂 Partida cargada: {nombre_slot}")
    return datos


def listar_saves():
    if not SAVES_DIR.exists():
        return []

    saves = []

    for carpeta in SAVES_DIR.iterdir():
        ruta_json = carpeta / "partida.json"

        if ruta_json.exists():
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    datos = json.load(f)

                saves.append({
                    "slot": carpeta.name,
                    "personaje": datos["personaje"]["nombre"],
                    "jugador": datos["jugador_nombre"],
                    "mundo": datos["mundo"]["contexto"]
                })
            except:
                pass

    return saves


def existe_save():
    return len(listar_saves()) > 0


def get_ultimo_save():
    saves = listar_saves()
    if not saves:
        return None

    return sorted(saves, key=lambda s: s["slot"], reverse=True)[0]