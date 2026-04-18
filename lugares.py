# lugares.py - Sistema de lugares visitables

def crear_lugares(lista_lugares):
    return {
        "disponibles": lista_lugares,
        "actual": lista_lugares[0] if lista_lugares else None,
        "visitados": []
    }

def moverse_a(lugares, nombre_lugar):
    for lugar in lugares["disponibles"]:
        if lugar["nombre"].lower() == nombre_lugar.lower():
            lugares["actual"] = lugar
            if nombre_lugar not in lugares["visitados"]:
                lugares["visitados"].append(nombre_lugar)
            return True
    return False

def desbloquear_lugar(lugares, lugar):
    nombres = [l["nombre"] for l in lugares["disponibles"]]
    if lugar["nombre"] not in nombres:
        lugares["disponibles"].append(lugar)
        return True
    return False

def lugar_actual(lugares):
    return lugares["actual"]