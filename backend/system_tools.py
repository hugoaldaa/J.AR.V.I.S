import datetime
import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

import psutil
import requests


# ============================================================
# INFORMACIÓN DE FECHA Y HORA
# ============================================================

def get_time() -> str:
    """
    Devuelve la hora actual del ordenador.
    """

    now = datetime.datetime.now()

    return now.strftime("%H:%M")


def get_date() -> str:
    """
    Devuelve la fecha actual del ordenador.
    """

    now = datetime.datetime.now()

    weekdays = [
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo"
    ]

    months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre"
    ]

    weekday = weekdays[now.weekday()]
    month = months[now.month - 1]

    return (
        f"{weekday}, "
        f"{now.day} de {month} de {now.year}"
    )


# ============================================================
# INFORMACIÓN DEL ORDENADOR
# ============================================================

def get_system_info() -> str:
    """
    Obtiene información básica del ordenador.
    """

    memory = psutil.virtual_memory()

    cpu_percent = psutil.cpu_percent(
        interval=0.5
    )

    total_ram = memory.total / (1024 ** 3)
    used_ram = memory.used / (1024 ** 3)

    disks = []

    for partition in psutil.disk_partitions():

        try:

            usage = psutil.disk_usage(
                partition.mountpoint
            )

            total = usage.total / (1024 ** 3)
            used = usage.used / (1024 ** 3)
            free = usage.free / (1024 ** 3)

            disks.append(
                f"{partition.mountpoint}: "
                f"{used:.1f} GB usados / "
                f"{total:.1f} GB totales "
                f"({free:.1f} GB libres)"
            )

        except PermissionError:
            continue

    disk_info = "\n".join(disks)

    return (
        f"Sistema operativo: {os.name}\n"
        f"CPU: {psutil.cpu_count(logical=True)} núcleos lógicos\n"
        f"Uso actual de CPU: {cpu_percent:.1f}%\n"
        f"RAM total: {total_ram:.1f} GB\n"
        f"RAM utilizada: {used_ram:.1f} GB\n"
        f"Discos:\n{disk_info}"
    )


# ============================================================
# ABRIR PROGRAMAS
# ============================================================

PROGRAMS = {

    # Navegadores
    "chrome": [
        "chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],

    "google chrome": [
        "chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],

    "edge": [
        "msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],

    "microsoft edge": [
        "msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],

    "firefox": [
        "firefox.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
    ],


    # Desarrollo
    "visual studio code": [
        "code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],

    "vs code": [
        "code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],

    "vscode": [
        "code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],


    # Aplicaciones
    "obsidian": [
        "Obsidian.exe",
    ],

    "discord": [
        "Discord.exe",
    ],

    "spotify": [
        "Spotify.exe",
    ],

    "steam": [
        "steam.exe",
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],


    # Windows
    "bloc de notas": [
        "notepad.exe",
    ],

    "notepad": [
        "notepad.exe",
    ],

    "calculadora": [
        "calc.exe",
    ],

    "calculator": [
        "calc.exe",
    ],

    "explorador": [
        "explorer.exe",
    ],

    "explorador de archivos": [
        "explorer.exe",
    ],

    "terminal": [
        "wt.exe",
    ],
}


def open_program(program: str) -> str:
    """
    Abre un programa de la lista permitida.
    """

    program = program.lower().strip()

    if program not in PROGRAMS:
        return f"No tengo configurado el programa '{program}'."

    # Calculadora de Windows
    if program in ("calculadora", "calculator"):
        try:
            os.startfile("ms-calculator:")
            return "OK"
        except Exception as e:
            return f"ERROR: {e}"

    candidates = PROGRAMS[program]

    for candidate in candidates:

        # Buscar en PATH
        if not os.path.isabs(candidate):

            executable = shutil.which(candidate)

            if executable:
                try:
                    os.startfile(executable)
                    return "OK"
                except Exception as e:
                    return f"ERROR: {e}"

        # Ruta absoluta
        else:

            path = Path(candidate)

            if path.exists():
                try:
                    os.startfile(str(path))
                    return "OK"
                except Exception as e:
                    return f"ERROR: {e}"

    return f"ERROR: No he encontrado {program} instalado."


# ============================================================
# ABRIR CARPETAS
# ============================================================

def open_folder(path: str) -> str:
    """
    Abre una carpeta de Windows.
    """

    folder = Path(path).expanduser()

    if not folder.exists():

        return (
            f"La carpeta no existe: {path}"
        )

    if not folder.is_dir():

        return (
            f"La ruta no es una carpeta: {path}"
        )

    try:

        os.startfile(str(folder))

        return (
            f"He abierto la carpeta {folder}."
        )

    except Exception as e:

        return (
            f"No he podido abrir la carpeta: {e}"
        )


# ============================================================
# ABRIR WEBS
# ============================================================

def open_website(url: str) -> str:
    """
    Abre una página web en el navegador
    predeterminado.
    """

    url = url.strip()

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    try:

        webbrowser.open(url)

        return (
            f"He abierto {url}."
        )

    except Exception as e:

        return (
            f"No he podido abrir la página: {e}"
        )


# ============================================================
# TIEMPO METEOROLÓGICO
# ============================================================

def get_weather(city: str) -> str:
    """
    Obtiene el tiempo actual de una ciudad.
    """

    city = city.strip()

    if not city:

        return "No se ha indicado ninguna ciudad."

    try:

        url = (
            "https://wttr.in/"
            + requests.utils.quote(city)
            + "?format=j1"
        )

        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        current = data["current_condition"][0]

        temperature = current["temp_C"]
        feels_like = current["FeelsLikeC"]
        humidity = current["humidity"]
        description = (
            current["weatherDesc"][0]["value"]
        )
        wind = current["windspeedKmph"]

        return (
            f"Ciudad: {city}\n"
            f"Condición: {description}\n"
            f"Temperatura: {temperature} °C\n"
            f"Sensación térmica: {feels_like} °C\n"
            f"Humedad: {humidity}%\n"
            f"Viento: {wind} km/h"
        )

    except Exception as e:

        return (
            f"No he podido consultar el tiempo "
            f"de {city}: {e}"
        )


# ============================================================
# DICCIONARIO DE HERRAMIENTAS
# ============================================================

AVAILABLE_FUNCTIONS = {
    "get_time": get_time,
    "get_date": get_date,
    "get_system_info": get_system_info,
    "open_program": open_program,
    "open_folder": open_folder,
    "open_website": open_website,
    "get_weather": get_weather,
}