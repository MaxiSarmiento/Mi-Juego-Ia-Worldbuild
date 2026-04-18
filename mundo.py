# mundo.py - El escenario y los NPCs del juego

import random

def crear_mundo(contexto_jugador, descripcion_generada, npcs):
    # Le agregamos memoria y stats a cada NPC
    for npc in npcs:
        npc["historial"] = []
        npc["stats"] = {
            "amistad": random.randint(5, 20),
            "rivalidad": random.randint(0, 10),
            "interes": random.randint(0, 15)
        }
    return {
        "contexto": contexto_jugador,
        "descripcion": descripcion_generada,
        "npcs": npcs,
        "hora_actual": "mañana temprano"
    }

def ver_mundo(mundo):
    print(f"""
=== EL MUNDO ===
{mundo['descripcion']}

=== PERSONAJES CERCANOS ===""")
    for npc in mundo["npcs"]:
        s = npc["stats"]
        print(f"""
  👤 {npc['nombre']}
     Apariencia  : {npc['apariencia']}
     Personalidad: {npc['personalidad']}
     Relación    : {npc['relacion']}
     😊 Amistad  : {s['amistad']}/100
     ⚔️  Rivalidad: {s['rivalidad']}/100
     💘 Interés  : {s['interes']}/100""")
    print("================\n")

def debe_ocurrir_evento():
    return random.random() < 0.4

def actualizar_hora(mundo, nueva_hora):
    mundo["hora_actual"] = nueva_hora

def elegir_npc_aleatorio(mundo):
    if mundo["npcs"]:
        return random.choice(mundo["npcs"])
    return None