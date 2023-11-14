from colorama import Fore, Style, init

# Inicializa colorama para colorear la salida de la consola
init()

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read().strip()

def print_colored(agent, text):
    agent_colors = {
        "User": Fore.LIGHTGREEN_EX,
        "Assistant": Fore.YELLOW,
    }
    color = agent_colors.get(agent, Fore.LIGHTWHITE_EX)
    print(color + f"{agent}: {text}" + Style.RESET_ALL)
