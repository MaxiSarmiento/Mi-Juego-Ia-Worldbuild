import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image

# cargar variables
load_dotenv()

# configurar API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# modelo
model = genai.GenerativeModel("gemini-1.5-flash")


def analizar_imagen(ruta_imagen):
    img = Image.open(ruta_imagen)

    prompt = """
Analiza esta imagen como personaje.

Devuelve SOLO JSON con:
- cabello
- ojos
- ropa
- estilo
- expresion
- detalles

No inventes cosas que no se ven.
"""

    response = model.generate_content([prompt, img])

    return response.text


# 🔽 PROBAR
if __name__ == "__main__":
    ruta = r"F:\Repos\Mi_Juego_IA\Goth.jpg" # tu imagen
    resultado = analizar_imagen(ruta)

    print("\nResultado de la IA:\n")
    print(resultado)