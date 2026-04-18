# setup.py - Configuración inicial del juego

from personaje import crear_personaje
from mundo import crear_mundo
from ia import generar_stats_iniciales, generar_mundo

def setup_jugador():
    print("\n=== TU PERSONAJE ===")
    nombre = input("¿Cómo se llama tu personaje? ")
    return nombre

def setup_personaje_femenino():
    print("\n=== CREÁ TU PERSONAJE FEMENINO ===")

    nombre = input("Nombre: ")

    print("\nApariencia:")
    cabello = input("  Color de cabello: ")
    ojos = input("  Color de ojos: ")
    estilo = input("  Estilo de ropa (ej: casual, elegante, deportivo): ")

    print("\nPersonalidad:")
    print("  1. Tímida y reservada")
    print("  2. Alegre y extrovertida")
    print("  3. Tsundere (fría por fuera, cálida por dentro)")
    print("  4. Misteriosa y seria")
    print("  5. Personalizada")

    opcion = input("\n  Elegí una opción (1-5): ")

    personalidades = {
        "1": "tímida y reservada, le cuesta abrirse pero es muy leal",
        "2": "alegre y extrovertida, siempre positiva y energética",
        "3": "tsundere, fría y sarcástica al principio pero se va abriendo",
        "4": "misteriosa y seria, habla poco pero cada palabra importa",
    }

    if opcion in personalidades:
        personalidad = personalidades[opcion]
    else:
        personalidad = input("  Describí su personalidad: ")

    apariencia = f"cabello {cabello}, ojos {ojos}, estilo {estilo}"

    # Primero creamos el personaje, después lo usamos
    personaje_creado = crear_personaje(nombre, personalidad, apariencia)

    print("\n⏳ Generando stats iniciales...")
    stats_iniciales = generar_stats_iniciales(personaje_creado)
    print(f"DEBUG stats: {stats_iniciales}")
    personaje_creado["stats"] = stats_iniciales
    print("✨ Stats iniciales generados según su personalidad")

    return personaje_creado


def setup_mundo(personaje, jugador_nombre):
    print("\n=== EL MUNDO ===")
    print("Describí el contexto de tu historia.")
    print("Ejemplos: 'colegio secundario en Japón', 'reino medieval fantástico', 'ciudad cyberpunk'")

    contexto = input("\nContexto: ")

    print("\n⏳ Generando el mundo...")
    descripcion, npcs = generar_mundo(contexto, personaje, jugador_nombre)
    print("✨ Mundo generado")

    return crear_mundo(contexto, descripcion, npcs)