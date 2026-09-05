# applications.py

import subprocess


def open_notepad():
    subprocess.Popen(["notepad.exe"])
    return "Bloc de notas abierto."


def open_calculator():
    subprocess.Popen(["calc.exe"])
    return "Calculadora abierta."