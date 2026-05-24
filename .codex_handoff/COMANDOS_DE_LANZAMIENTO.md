# Comandos de Lanzamiento

## Ruta principal

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
```

## Lanzamiento recomendado de la version parcheada

Usar `5001` para evitar mezclarte con procesos viejos en `5000`.

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
bash start.sh stop
PORT=5001 OPEN_BROWSER=0 APP_URL=http://127.0.0.1:5001/ BACKEND_URL=http://127.0.0.1:5001/api/architecture bash start.sh start
```

Abrir despues:

```text
http://127.0.0.1:5001/
```

## Ver estado

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
bash start.sh status
```

## Ver logs

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
bash start.sh logs
```

## Reiniciar limpio

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
bash start.sh stop
PORT=5001 OPEN_BROWSER=0 APP_URL=http://127.0.0.1:5001/ BACKEND_URL=http://127.0.0.1:5001/api/architecture bash start.sh start
```

## Backend directo sin launcher

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
PORT=5001 /home/neurodriver/ferrari_env/bin/python backend/app.py
```

## Validacion rapida del backend

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
python3 -m unittest discover -s backend -p 'test_*.py' -q
```

## Validacion rapida del proyecto demo generado

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/demo-agent-lab"
python3 -m unittest discover -s tests -q
```

## Que deberia verse en la UI al lanzar una sesion nueva

1. Nodo `docs/habla-session.md`.
2. Nodo `LACE_LOG.md`.
3. Diez nodos `docs/lace_cycles/ciclo-01.md` a `ciclo-10.md`.
4. Panel del agente mostrando `HABLA`, `laceCycles` y subtareas si aplica.
5. El mapa actualizandose en vivo mientras cambia `LACE_LOG.md`.
6. Puntos rojos/parpadeo cuando el lint detecte desconexiones reales.

## No usar como referencia principal

- `http://127.0.0.1:5000/`

Ese puerto puede seguir mostrando procesos viejos o una instancia previa sin el parche completo.
