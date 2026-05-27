# CyberLACE Postmortem: cuello de botella del runtime

Fecha UTC: 2026-05-24T23:36:18.295167+00:00

## Sintoma reportado
La interfaz quedo lenta o bloqueada, botones inaccesibles y el login/modal parecia no iniciar despues de la integracion CyberLACE.

## Hallazgo principal
No fue una sola falla. Hubo cuatro problemas encadenados:

1. `backend/editor_state.json` crecio a ~41 MB y quedo incluido dentro de su propio grafo. `/api/architecture` llego a devolver ~45 MB y tardar ~8.17s.
2. Varias pestanas antiguas del navegador seguian usando Socket.IO por polling y endpoints de refresco frecuente, saturando el backend principal.
3. El reinicio del backend se rompio por un `threaded=True` incompatible en `socketio.run()`.
4. El modal inicial tenia una espera de 30 segundos, lo que hacia parecer que login/setup no cargaba.

## Reparaciones aplicadas
- `backend/project_graph.py` ahora ignora `editor_state.json`, `reverse_engineering_state.json`, caches y artefactos generados.
- El grafo trunca payloads de codigo grandes para evitar respuestas gigantes.
- `backend/editor_state.json` fue compactado; backup previo en `runtime/artifacts/editor_state_before_bottleneck_fix_20260524T220000Z.json`.
- `backend/app.py` ya no emite el grafo completo automaticamente en cada conexion Socket.IO.
- Se elimino `threaded=True` del arranque Socket.IO.
- Socket.IO frontend/backend permite WebSocket y deja polling como fallback.
- `CyberLACEPanel` no descarga evidencia mientras esta colapsado.
- Se redujeron intervalos de polling en `CodeWorkbench`.
- `WelcomeAuthGate` redujo espera inicial de 30000 ms a 1200 ms.

## Validacion ejecutada
- `python3 -B -m py_compile backend/project_graph.py backend/app.py backend/test_workspace_visual_sync.py`: OK.
- `python3 -m unittest backend.test_workspace_visual_sync`: OK.
- `npm --prefix frontend run build`: OK, bundle final `frontend/dist/assets/index-DYvKCqrt.js`.
- `OPEN_BROWSER=0 ./start.sh restart`: OK, backend activo en `http://127.0.0.1:5001/`, PID observado `1955912`.
- Navegador headless fresco: modal de acceso visible rapidamente con `Acceso inicial`, `Crear cuenta`, `Iniciar sesion`.

## Evidencia de rendimiento
- Antes: `backend/editor_state.json` ~41 MB; `/api/architecture` ~45 MB y ~8.17s.
- Despues: `backend/editor_state.json` ~3.3 MB, 148 nodos, sin nodo `backend__editor_state_json`.
- Backend aislado sin pestanas: 0.0% CPU y `/api/health` ~0.004240s.

## Riesgo residual
El backend principal puede seguir viendose lento si hay pestanas antiguas abiertas, porque el JavaScript viejo ya cargado sigue haciendo polling. Hay que cerrar esas pestanas o hacer recarga fuerte para cargar el bundle nuevo.

## Siguiente paso operativo
Cerrar todas las pestanas existentes de `http://127.0.0.1:5001/` o hacer `Ctrl+Shift+R`, abrir una sola pestana nueva y repetir la prueba de login/botones. No matar procesos de navegador sin autorizacion humana.
