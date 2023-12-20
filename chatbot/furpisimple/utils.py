from colorama import Fore, Style, init
import os

# Obtén la ruta absoluta al directorio donde se encuentra este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializa colorama para colorear la salida de la consola
init()

def open_file(filename):
    # Construye la ruta al archivo utilizando la base del directorio de este script
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

def print_colored(agent, text):
    agent_colors = {
        "User": Fore.LIGHTGREEN_EX,
        "Assistant": Fore.YELLOW,
    }
    color = agent_colors.get(agent, Fore.LIGHTWHITE_EX)
    print(color + f"{agent}: {text}" + Style.RESET_ALL)
