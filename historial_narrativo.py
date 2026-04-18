# historial_narrativo.py - Diario de la historia

def crear_historial_narrativo():
    return []

def agregar_entrada(historial_narrativo, entrada):
    historial_narrativo.append(entrada)

def ver_historial_narrativo(historial_narrativo):
    if not historial_narrativo:
        print("No hay entradas en el historial todavía.")
        return
    for i, entrada in enumerate(historial_narrativo, 1):
        print(f"\n--- Entrada {i} ---")
        print(entrada)