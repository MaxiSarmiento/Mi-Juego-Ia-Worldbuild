# ia.py - Todo lo que habla con Groq

import os
import json
from dotenv import load_dotenv
from groq import Groq
from flags import flags_para_prompt
load_dotenv()
cliente = Groq(api_key=os.getenv("GROQ_API_KEY"))


def construir_system_prompt(personaje, jugador_nombre, memoria="", flags={}, lugar=""):
    s = personaje["stats"]
    seccion_memoria = f"\nMemoria de lo que pasó hasta ahora:\n{memoria}\n" if memoria else ""
    seccion_flags = f"\nEventos importantes que ya ocurrieron:\n{flags_para_prompt(flags)}\n" if flags else ""
    seccion_lugar = f"\nUbicación actual: {lugar}\n" if lugar else ""

    return f"""
Sos {personaje['nombre']}, personaje de una visual novel romántica.
Apariencia: {personaje['apariencia']}.
Personalidad: {personaje['personalidad']}.
{seccion_memoria}{seccion_flags}{seccion_lugar}
Tus emociones actuales hacia {jugador_nombre}:
- Amistad: {s['amistad']}/100
- Cariño: {s['cariño']}/100
- Miedo: {s['miedo']}/100
- Odio: {s['odio']}/100

Respondé según esos números y según el lugar donde están.
No repitas eventos que ya ocurrieron.
Respondé siempre en personaje. Respuestas cortas y naturales.
El jugador se llama {jugador_nombre}.
"""

def hablar(personaje, jugador_nombre, historial, mensaje_jugador, memoria="", flags={}, lugar=""):
    historial.append({"role": "user", "content": mensaje_jugador})

    respuesta = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": construir_system_prompt(personaje, jugador_nombre, memoria, flags, lugar)}
        ] + historial
    )

    texto = respuesta.choices[0].message.content
    historial.append({"role": "assistant", "content": texto})
    return texto

def analizar_cambios(personaje, jugador_nombre, mensaje_jugador, respuesta_personaje):
    s = personaje["stats"]

    prompt = f"""
Analizá esta interacción en una visual novel romántica:

Jugador dijo: "{mensaje_jugador}"
{personaje['nombre']} respondió: "{respuesta_personaje}"

Stats actuales:
- amistad: {s['amistad']}/100
- cariño: {s['cariño']}/100
- miedo: {s['miedo']}/100
- odio: {s['odio']}/100

Devolvé SOLO un JSON con cuánto cambia cada stat (positivo o negativo, máximo ±10).
Ejemplo: {{"amistad": 2, "cariño": 1, "miedo": 0, "odio": -1}}
Sin texto extra, solo el JSON.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    try:
        return json.loads(texto)
    except:
        return {}

def generar_stats_iniciales(personaje):
    import random

    personalidad = personaje.get("personalidad", "").lower()

    # 🎲 Base aleatoria pura
    stats = {
        "amistad": random.randint(0, 20),
        "cariño": random.randint(0, 20),
        "miedo": random.randint(0, 20),
        "odio": random.randint(0, 20)
    }

    # 🎭 Modificadores por personalidad
    modificadores = {
        "tsundere": {"amistad": -3, "cariño": -5, "odio": +5},
        "amable": {"amistad": +5, "cariño": +5, "odio": -3},
        "fría": {"amistad": -5, "cariño": -5, "miedo": +2},
        "tímida": {"amistad": -2, "cariño": +2, "miedo": +5},
        "yandere": {"cariño": +8, "odio": +4, "miedo": +2},
        "agresiva": {"amistad": -5, "odio": +6},
        "alegre": {"amistad": +6, "cariño": +4, "miedo": -3},
        "coqueta": {"cariño": +6, "amistad": +3},
        "misteriosa": {"amistad": -2, "miedo": +4},
        "protectora": {"amistad": +4, "cariño": +3},
    }

    # 🔍 Aplicar modificadores si detecta keyword
    for clave, mods in modificadores.items():
        if clave in personalidad:
            for stat, valor in mods.items():
                stats[stat] += valor

    # 🧱 Clamp (0–20)
    for k in stats:
        stats[k] = max(0, min(20, stats[k]))

    return stats

def generar_mundo(contexto, personaje, jugador_nombre, npc_genero="female"):
    genero_prota = personaje.get("genero", "female")

    prompt = f"""
Sos un escritor de visual novels. El jugador te dio este contexto para su historia:

"{contexto}"

El personaje principal es {personaje['nombre']} ({genero_prota}) y es {personaje['personalidad']}.
El jugador se llama {jugador_nombre}.

Los NPCs pueden ser hombres o mujeres, pero tendé a generar más NPCs de género {npc_genero}.
Indicá el género implícitamente en la apariencia o descripción (ej: "chico alto", "mujer de cabello largo").

Evitá que todos los NPCs sean similares: variá edades, roles y actitudes.

Hacé dos cosas:

1. Escribí una descripción del escenario en 3 o 4 oraciones. Que sea atmosférica y detallada.

2. Generá entre 3 y 10 NPCs que vivan en ese mundo. Para cada uno definí:
   - nombre
   - apariencia (una línea)
   - personalidad (una línea)
   - relacion: cómo se relaciona con el jugador y/o con {personaje['nombre']}

Pueden tener intenciones buenas o malas. No todos tienen que ser amistosos.

Devolvé SOLO un JSON con este formato exacto, sin texto extra:
{{
  "descripcion": "...",
  "npcs": [
    {{
      "nombre": "...",
      "apariencia": "...",
      "personalidad": "...",
      "relacion": "..."
    }}
  ]
}}
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        datos = json.loads(texto)
        return datos["descripcion"], datos["npcs"]
    except:
        return contexto, []

def generar_evento(mundo, personaje, jugador_nombre, ultimos_mensajes):
    npcs_texto = "\n".join([
        f"- {n['nombre']}: {n['personalidad']}, relación: {n['relacion']}"
        for n in mundo["npcs"]
    ])

    prompt = f"""
Sos el narrador de una visual novel. El mundo es:
{mundo['descripcion']}

Hora actual: {mundo['hora_actual']}

NPCs disponibles:
{npcs_texto}

Últimos mensajes de la conversación:
{ultimos_mensajes}

Generá UN evento corto que ocurra alrededor del jugador ({jugador_nombre}) y {personaje['nombre']}.
Puede ser:
- Un NPC que se acerca o hace algo
- Algo que cambia en el escenario (suena una campana, cambia el clima, termina una clase)
- Una combinación de ambos

También decidí cuánto tiempo pasó desde el último evento y cuál es la nueva hora del día.

Devolvé SOLO un JSON con este formato, sin texto extra:
{{
  "evento": "descripción del evento en 2 o 3 oraciones, narrado en presente",
  "nueva_hora": "ej: media mañana, hora del almuerzo, tarde"
}}
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        datos = json.loads(texto)
        return datos["evento"], datos["nueva_hora"]
    except:
        return None, None

def npc_habla(npc, jugador_nombre, personaje, mundo, mensaje_contexto):
    historial_npc = npc.get("historial", [])
    s = npc["stats"]

    system_npc = f"""
Sos {npc['nombre']}, un personaje secundario de una visual novel.
Apariencia: {npc['apariencia']}.
Personalidad: {npc['personalidad']}.
Tu relación con {jugador_nombre}: {npc['relacion']}.

Tus emociones actuales:
- Amistad: {s['amistad']}/100
- Rivalidad: {s['rivalidad']}/100
- Interés romántico: {s['interes']}/100

El escenario es: {mundo['descripcion']}
Hora: {mundo['hora_actual']}

Respondé en personaje. Una o dos oraciones, natural y directo.
"""

    historial_npc.append({"role": "user", "content": mensaje_contexto})

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_npc}
        ] + historial_npc
    )

    texto = resultado.choices[0].message.content
    historial_npc.append({"role": "assistant", "content": texto})
    npc["historial"] = historial_npc
    return texto

def npc_decide_acercarse(npc, jugador_nombre, personaje, mundo):
    prompt = f"""
Sos {npc['nombre']} en una visual novel. Estás en: {mundo['descripcion']}.
Es {mundo['hora_actual']}.

{jugador_nombre} está hablando con {personaje['nombre']}.

Tu personalidad: {npc['personalidad']}.
Tu relación con ellos: {npc['relacion']}.
Amistad: {npc['stats']['amistad']}/100, Interés: {npc['stats']['interes']}/100.

¿Te acercás a interrumpir o interactuar? Respondé SOLO con un JSON:
{{"acercarse": true, "motivo": "razón breve de por qué te acercás"}}
o
{{"acercarse": false, "motivo": ""}}
Sin texto extra, solo el JSON.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        datos = json.loads(texto)
        return datos.get("acercarse", False), datos.get("motivo", "")
    except:
        return False, ""

def resumir_memoria(historial, memoria_anterior, personaje, jugador_nombre):
    if len(historial) < 6:
        return memoria_anterior

    historial_texto = "\n".join([
        f"{'Jugador' if m['role'] == 'user' else personaje['nombre']}: {m['content']}"
        for m in historial[-10:]  # solo los últimos 10 mensajes
    ])

    prompt = f"""
Sos el narrador de una visual novel. Resumí lo más importante que pasó hasta ahora
en esta historia entre {jugador_nombre} y {personaje['nombre']}.

Memoria anterior:
{memoria_anterior if memoria_anterior else "No hay memoria previa."}

Conversación reciente:
{historial_texto}

Escribí un resumen corto (máximo 5 oraciones) que capture:
- El estado actual de la relación
- Los momentos importantes que pasaron
- Cualquier tension, acuerdo o evento relevante

Solo el resumen, sin títulos ni formato extra.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return resultado.choices[0].message.content.strip()

def generar_entrada_historial(personaje, jugador_nombre, mundo, historial, memoria, historial_narrativo):
    entradas_previas = "\n".join(historial_narrativo[-3:]) if historial_narrativo else "Ninguna todavía."

    ultimos_mensajes = "\n".join([
        f"{'Jugador' if m['role'] == 'user' else personaje['nombre']}: {m['content']}"
        for m in historial[-10:]
    ])

    s = personaje["stats"]

    prompt = f"""
Sos el narrador de una visual novel. Escribí una entrada de diario que resuma
lo que acaba de pasar en la historia.

Contexto del mundo: {mundo['descripcion']}
Hora actual: {mundo['hora_actual']}

Estado emocional de {personaje['nombre']} hacia {jugador_nombre}:
- Amistad: {s['amistad']}/100
- Cariño: {s['cariño']}/100
- Miedo: {s['miedo']}/100
- Odio: {s['odio']}/100

Entradas anteriores del diario:
{entradas_previas}

Conversación reciente:
{ultimos_mensajes}

Escribí UNA entrada narrativa corta (3 a 5 oraciones) en tercera persona,
estilo novela, que capture los momentos importantes. Que fluya con las
entradas anteriores sin repetirlas. Solo el texto, sin título ni formato.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return resultado.choices[0].message.content.strip()

def generar_introduccion(mundo, personaje, jugador_nombre, lugares):
    nombres_lugares = ", ".join([l["nombre"] for l in lugares["disponibles"]]) if lugares else ""

    prompt = f"""
Sos el narrador de una visual novel romántica. Escribí la introducción de la historia.

Mundo: {mundo['descripcion']}
Hora: {mundo['hora_actual']}
Lugares disponibles: {nombres_lugares}
Personaje principal: {personaje['nombre']} — {personaje['personalidad']}
El jugador se llama: {jugador_nombre}

Escribí una introducción narrativa de 3 a 4 oraciones en presente, estilo novela,
que sitúe al jugador en el mundo, mencione dónde están y presente sutilmente
a {personaje['nombre']}. Que sea atmosférica e invite a explorar.
Solo el texto, sin títulos.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return resultado.choices[0].message.content.strip()


def generar_lugares(contexto, mundo_descripcion, personaje, jugador_nombre):
    prompt = f"""
Sos un diseñador de visual novels. Basándote en este mundo:

Contexto: {contexto}
Descripción: {mundo_descripcion}

Generá entre 4 y 6 lugares que el jugador pueda visitar en este mundo.
Cada lugar debe tener atmósfera y personalidad propia.

Devolvé SOLO un JSON con este formato, sin texto extra:
{{
  "lugares": [
    {{
      "nombre": "Nombre del lugar",
      "descripcion": "Descripción atmosférica en 2 oraciones",
      "ambiente": "tranquilo / tenso / romántico / peligroso / misterioso",
      "desbloqueado": true
    }}
  ]
}}
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        datos = json.loads(texto)
        return datos["lugares"]
    except:
        return [{
            "nombre": "Lugar desconocido",
            "descripcion": mundo_descripcion,
            "ambiente": "neutral",
            "desbloqueado": True
        }]

def detectar_movimiento(mensaje_jugador, lugares_disponibles):
    nombres = [l["nombre"] for l in lugares_disponibles]
    nombres_texto = ", ".join(nombres)

    prompt = f"""
El jugador escribió: "{mensaje_jugador}"

Lugares disponibles: {nombres_texto}

¿El jugador está intentando moverse a algún lugar?
Devolvé SOLO un JSON:
{{"moverse": true, "destino": "nombre exacto del lugar"}}
o
{{"moverse": false}}
Sin texto extra.
"""

    resultado = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resultado.choices[0].message.content.strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        datos = json.loads(texto)
        return datos.get("moverse", False), datos.get("destino", "")
    except:
        return False, ""

def detectar_flags(personaje, jugador_nombre, mensaje_jugador, respuesta_personaje, flags_actuales):
        flags_texto = "\n".join([f"- {desc}" for desc in flags_actuales.values()]) if flags_actuales else "Ninguno."

        prompt = f"""
     Analizá esta interacción de una visual novel y detectá si ocurrió algo
     importante que deba recordarse para siempre en la historia.

     Jugador dijo: "{mensaje_jugador}"
     {personaje['nombre']} respondió: "{respuesta_personaje}"

     Eventos ya registrados (no repetir):
     {flags_texto}

     ¿Ocurrió algo nuevo e importante? Ejemplos de cosas importantes:
     - Una confesión o revelación personal
     - Un primer encuentro significativo
     - Una decisión importante del jugador
     - Un conflicto que escaló
     - Un momento romántico o de quiebre

     Si ocurrió algo importante devolvé un JSON con este formato:
     {{"hay_flag": true, "clave": "nombre_corto_sin_espacios", "descripcion": "Descripción corta en español de qué pasó"}}

     Si no ocurrió nada importante:
     {{"hay_flag": false}}

     Solo el JSON, sin texto extra.
     """

        resultado = cliente.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )

        texto = resultado.choices[0].message.content.strip()

        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]

        try:
            datos = json.loads(texto)
            if datos.get("hay_flag"):
                return datos["clave"], datos["descripcion"]
            return None, None
        except:
            return None, None