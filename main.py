# main.py - Loop principal del juego

import random
from setup import setup_jugador, setup_personaje_femenino, setup_mundo
from personaje import ver_stats, actualizar_stats
from mundo import ver_mundo, actualizar_hora, elegir_npc_aleatorio
from ia import hablar, analizar_cambios, generar_evento, npc_habla, npc_decide_acercarse, resumir_memoria
from guardado import guardar_partida, cargar_partida, existe_save

# === SETUP ===
print("╔══════════════════════════╗")
print("║     VISUAL NOVEL RPG     ║")
print("╚══════════════════════════╝")

if existe_save():
    opcion = input("Se encontró una partida guardada. ¿Cargar? (s/n): ")
    if opcion.lower() == "s":
        datos = cargar_partida()
        jugador_nombre = datos["jugador_nombre"]
        personaje = datos["personaje"]
        mundo = datos["mundo"]
        historial = datos["historial"]
        memoria = datos.get("memoria", "")
    else:
        jugador_nombre = setup_jugador()
        personaje = setup_personaje_femenino()
        mundo = setup_mundo(personaje, jugador_nombre)
        historial = []
        memoria = ""
else:
    jugador_nombre = setup_jugador()
    personaje = setup_personaje_femenino()
    mundo = setup_mundo(personaje, jugador_nombre)
    historial = []
    memoria = ""

contador_mensajes = 0
contador_resumen = 0
proximo_evento = random.randint(1, 5)
proximo_npc = random.randint(2, 6)

# === INTRO ===
ver_mundo(mundo)

# === LOOP ===
print(f"✨ Comenzando historia con {personaje['nombre']}...")
print("Comandos: 'stats', 'mundo', 'guardar', 'salir'\n")

while True:
    entrada = input(f"{jugador_nombre}: ")

    if entrada.lower() == "salir":
        guardar_partida(jugador_nombre, personaje, mundo, historial, memoria)
        print("Fin de la sesión.")
        break
    elif entrada.lower() == "guardar":
        guardar_partida(jugador_nombre, personaje, mundo, historial, memoria)
    elif entrada.lower() == "stats":
        ver_stats(personaje)
    elif entrada.lower() == "mundo":
        ver_mundo(mundo)
    else:
        respuesta = hablar(personaje, jugador_nombre, historial, entrada, memoria)
        print(f"\n{personaje['nombre']}: {respuesta}\n")

        cambios = analizar_cambios(personaje, jugador_nombre, entrada, respuesta)
        actualizar_stats(personaje, cambios)

        contador_mensajes += 1
        contador_resumen += 1

        # Cada 8 mensajes actualiza la memoria
        if contador_resumen >= 8:
            contador_resumen = 0
            print("🧠 Actualizando memoria...")
            memoria = resumir_memoria(historial, memoria, personaje, jugador_nombre)

        # Evento del mundo
        if contador_mensajes >= proximo_evento:
            contador_mensajes = 0
            proximo_evento = random.randint(1, 5)

            ultimos = f"{jugador_nombre}: {entrada}\n{personaje['nombre']}: {respuesta}"
            evento, nueva_hora = generar_evento(mundo, personaje, jugador_nombre, ultimos)

            if evento:
                print(f"🌍 {evento}\n")
                if nueva_hora:
                    actualizar_hora(mundo, nueva_hora)

                # NPC que decide acercarse solo
                if contador_mensajes >= proximo_npc:
                    proximo_npc = random.randint(2, 6)
                    npc = elegir_npc_aleatorio(mundo)

                    if npc:
                        se_acerca, motivo = npc_decide_acercarse(npc, jugador_nombre, personaje, mundo)

                        if se_acerca:
                            contexto = f"{jugador_nombre} estaba hablando con {personaje['nombre']}. {motivo}"
                            dialogo = npc_habla(npc, jugador_nombre, personaje, mundo, contexto)
                            print(f"\n💬 {npc['nombre']} se acerca — {dialogo}")
                            print(f"[Podés responderle a {npc['nombre']} o ignorarlo]")

                            respuesta_jugador = input(f"{jugador_nombre} (a {npc['nombre']} / Enter para ignorar): ")

                            if respuesta_jugador.strip() != "":
                                # El jugador le responde al NPC
                                respuesta_npc = npc_habla(npc, jugador_nombre, personaje, mundo, respuesta_jugador)
                                print(f"💬 {npc['nombre']}: {respuesta_npc}\n")

                                # El personaje principal también puede reaccionar
                                reaccion = hablar(personaje, jugador_nombre, historial,
                                                  f"[{npc['nombre']} se acercó y dijo: '{dialogo}'. {jugador_nombre} le respondió: '{respuesta_jugador}']",
                                                  memoria)
                                print(f"{personaje['nombre']}: {reaccion}\n")
                            else:
                                print(f"[Ignorás a {npc['nombre']}]\n")