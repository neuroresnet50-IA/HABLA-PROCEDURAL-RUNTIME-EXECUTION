# Process Killer

Utilidad para limpiar procesos de desarrollo y pruebas de `Vista IA`.

## Uso rapido

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/devtools/process-killer"
./mata_procesos.sh
```

Tambien puedes abrir `Mata Procesos Vista IA.desktop` como programa.

## Que limpia

- PIDs guardados en `.runtime/pids/`
- Puertos `5000`, `5173` y `4173`

## Opciones

```bash
./mata_procesos.sh --hold
./mata_procesos.sh 5000 5173 8000
DRY_RUN=1 ./mata_procesos.sh
```
