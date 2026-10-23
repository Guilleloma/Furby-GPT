from colorama import Fore, Style, init
import os

# Obtén la ruta absoluta al directorio donde se encuentra este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializa colorama para colorear la salida de la consola
init()

# Carga las claves desde .env si python-dotenv está instalado
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass

def open_file(filename):
    # Construye la ruta al archivo utilizando la base del directorio de este script
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

def get_env_key(name):
    # Lee una clave de las variables de entorno; si falta, falla sin mostrar valores
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}. Defínela en .env (ver .env.example).")
    return value

def print_colored(agent, text):
    agent_colors = {
        "User": Fore.LIGHTGREEN_EX,
        "Assistant": Fore.YELLOW,
    }
    color = agent_colors.get(agent, Fore.LIGHTWHITE_EX)
    print(color + f"{agent}: {text}" + Style.RESET_ALL)
