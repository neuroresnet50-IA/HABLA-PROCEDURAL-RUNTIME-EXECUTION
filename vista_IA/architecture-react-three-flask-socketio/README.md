# Architecture View: React + Three.js + Flask-SocketIO

Prototipo funcional de un mapa conceptual donde cada archivo generado por un agente aparece como un módulo conectado.

## Ejecutar backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Backend: http://localhost:5000

## Ejecutar frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Enviar un grafo nuevo

```bash
curl -X POST http://localhost:5000/api/architecture \
  -H 'Content-Type: application/json' \
  -d '{"nodes":[],"edges":[],"metadata":{"projectName":"Nuevo turno"}}'
```
