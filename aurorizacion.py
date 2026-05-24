#!/usr/bin/env python3
import subprocess
import time
import re

print("="*60)
print("AUTO-RESPONDEDOR para CODEX")
print("Detecta la terminal de Codex y presiona ENTER")
print("Presiona Ctrl+C para detener")
print("="*60)

# Instalar dependencias
subprocess.call(["sudo", "apt", "install", "xdotool", "wmctrl", "-y"], stderr=subprocess.DEVNULL)

contador = 0
try:
    while True:
        contador += 1
        
        # Obtener todas las ventanas
        output = subprocess.check_output(["wmctrl", "-l"]).decode()
        
        # Buscar ventanas de Codex o terminales específicas
        for linea in output.split('\n'):
            if not linea.strip():
                continue
                
            # Buscar ventanas que contengan Codex, BASE_METACOGNICION o terminal
            if re.search(r'codex|BASE|METACOGNICION|terminal|Terminal|neurodriver', linea, re.I):
                win_id = linea.split()[0]
                
                # Activar la ventana específica
                subprocess.call(["xdotool", "windowactivate", win_id], 
                              stderr=subprocess.DEVNULL)
                time.sleep(0.3)
                
                # Solo ENTER (sin texto)
                subprocess.call(["xdotool", "key", "Return"], 
                              stderr=subprocess.DEVNULL)
                
                print(f"[{contador}] ✓ ENTER enviado a: {linea[:50]}")
                break  # Solo responder a una ventana por ciclo
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print(f"\n✅ Detenido. Total respuestas: {contador}")






#!/usr/bin/env python3
import subprocess
import time
import re

print("="*60)
print("AUTO-RESPONDEDOR para CODEX")
print("Detecta la terminal de Codex y presiona ENTER")
print("Presiona Ctrl+C para detener")
print("="*60)

# Instalar dependencias
subprocess.call(["sudo", "apt", "install", "xdotool", "wmctrl", "-y"], stderr=subprocess.DEVNULL)

contador = 0
try:
    while True:
        contador += 1
        
        # Obtener todas las ventanas
        output = subprocess.check_output(["wmctrl", "-l"]).decode()
        
        # Buscar ventanas de Codex o terminales específicas
        for linea in output.split('\n'):
            if not linea.strip():
                continue
                
            # Buscar ventanas que contengan Codex, BASE_METACOGNICION o terminal
            if re.search(r'codex|BASE|METACOGNICION|terminal|Terminal|neurodriver', linea, re.I):
                win_id = linea.split()[0]
                
                # Activar la ventana específica
                subprocess.call(["xdotool", "windowactivate", win_id], 
                              stderr=subprocess.DEVNULL)
                time.sleep(0.3)
                
                # Solo ENTER (sin texto)
                subprocess.call(["xdotool", "key", "Return"], 
                              stderr=subprocess.DEVNULL)
                
                print(f"[{contador}] ✓ ENTER enviado a: {linea[:50]}")
                break  # Solo responder a una ventana por ciclo
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print(f"\n✅ Detenido. Total respuestas: {contador}")

    
















    