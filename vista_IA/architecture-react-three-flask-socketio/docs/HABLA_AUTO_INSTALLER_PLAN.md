# HABLA Auto Installer Plan

## Objetivo

Crear un instalador profesional para que HABLA Observer IA / Harness Engineering se pueda instalar en una maquina nueva sin que el desarrollador tenga que resolver dependencias manualmente.

El instalador debe:

- Detectar sistema operativo: Windows, Linux o macOS.
- Detectar arquitectura: x86_64, arm64.
- Detectar GPU: NVIDIA RTX 4060/4070/4090 u otra.
- Detectar permisos: usuario normal, sudo/admin disponible.
- Instalar stack base de la aplicacion.
- Instalar PostgreSQL y SQL Server cuando el perfil lo pida.
- Instalar stack Python/Node/Flask/Socket.IO/Vite/React/Angular.
- Instalar stack ML, IA generativa, vision industrial y agentes IA por perfiles.
- Crear entornos aislados para no romper Python/Node del sistema.
- Configurar servicios y variables de entorno.
- Ejecutar validaciones finales y dejar bitacora de instalacion.

## Regla principal

No instalar todo a ciegas. El instalador debe trabajar por perfiles:

- `base`: dependencias minimas para correr la app.
- `db`: PostgreSQL y SQL Server.
- `web-dev`: Node.js, Vite, React, Angular CLI, herramientas frontend.
- `ml-cpu`: stack de machine learning sin GPU.
- `ml-nvidia`: stack RTX con PyTorch CUDA cuando haya GPU NVIDIA.
- `gen-ai`: transformers, datasets, accelerate y stack generativo.
- `vision-industrial`: OpenCV, YOLO/Ultralytics, Albumentations, ONNX.
- `agents`: librerias para agentes IA y automatizacion.
- `mlops`: Docker, compose, MLflow/Jupyter/servicios auxiliares.
- `full`: todo lo anterior.

## Estructura propuesta

```text
installer/
  install.sh
  install.ps1
  install.bat
  stack.manifest.json
  stack.lock.json
  lib/
    detect_os.sh
    detect_gpu.sh
    detect_python.sh
    detect_node.sh
    install_linux.sh
    install_macos.sh
    install_windows.ps1
    verify_stack.py
  profiles/
    base.json
    db.json
    web-dev.json
    ml-cpu.json
    ml-nvidia.json
    gen-ai.json
    vision-industrial.json
    agents.json
    mlops.json
    full.json
  docker/
    docker-compose.base.yml
    docker-compose.db.yml
    docker-compose.mlops.yml
  logs/
```

## Flujo de instalacion

1. `preflight`
   - Detectar OS, version, shell y permisos.
   - Detectar CPU, RAM, disco libre.
   - Detectar GPU con `nvidia-smi` si existe.
   - Detectar Docker, Python, Node, Git, PostgreSQL y SQL Server.
   - Crear reporte `installer/logs/preflight.json`.

2. `package-manager`
   - Windows: usar `winget` como primera opcion.
   - Linux: usar `apt`, `dnf`, `zypper` o `pacman` segun distro.
   - macOS: usar Homebrew.
   - Si falta el gestor requerido, mostrar instruccion controlada.

3. `system-runtime`
   - Instalar Git.
   - Instalar Python compatible con ML, sin reemplazar Python del sistema.
   - Crear `.venv` del proyecto.
   - Instalar Node.js LTS.
   - Instalar npm/pnpm segun manifest.
   - Instalar build tools del OS.

4. `database`
   - PostgreSQL:
     - Linux: paquete nativo o contenedor Docker.
     - Windows: instalador/winget o Docker.
     - macOS: Homebrew o Docker.
   - SQL Server:
     - Windows: SQL Server Developer/Express o Docker.
     - Linux: repos Microsoft o Docker.
     - macOS: Docker, porque SQL Server no corre nativo en macOS.
   - Crear `.env` con `DATABASE_URL` y/o `POSTGRES_*`.
   - Ejecutar `backend/postgresql_schema.sql`.

5. `web-stack`
   - Instalar dependencias frontend con `npm ci` si hay lockfile, si no `npm install`.
   - Instalar Vite/React desde dependencias del proyecto.
   - Angular CLI solo si el perfil `web-dev` lo pide.
   - Compilar frontend con `npm run build`.

6. `python-backend`
   - Instalar `backend/requirements.txt`.
   - Instalar dependencias runtime Flask/Socket.IO.
   - Validar `python -m py_compile backend/app.py backend/auth_routes.py`.

7. `ml-stack`
   - Crear requirements separados:
     - `requirements-ml-cpu.txt`
     - `requirements-ml-nvidia.txt`
     - `requirements-gen-ai.txt`
     - `requirements-vision.txt`
     - `requirements-agents.txt`
   - Instalar PyTorch CPU si no hay NVIDIA.
   - Instalar PyTorch CUDA si hay RTX y driver compatible.
   - No instalar paquetes GPU incompatibles en macOS/CPU.

8. `docker-mlops`
   - Instalar Docker Desktop en Windows/macOS.
   - Instalar Docker Engine en Linux.
   - Crear compose para:
     - postgres
     - sqlserver
     - redis
     - mlflow
     - jupyter
     - minio opcional
   - Verificar `docker compose version`.

9. `services`
   - Linux: crear servicio `systemd` para backend si el usuario lo pide.
   - Windows: crear servicio con herramienta compatible o tarea programada.
   - macOS: crear `launchd` opcional.
   - Modo dev: arrancar backend y frontend manualmente.
   - Modo prod local: backend Flask sirve `frontend/dist`.

10. `smoke-tests`
    - `GET /api/health`
    - `GET /`
    - Verificar JS/CSS servidos.
    - Verificar conexion PostgreSQL si esta configurado.
    - Verificar `torch.cuda.is_available()` en perfil NVIDIA.
    - Verificar import de OpenCV, transformers, ultralytics.
    - Guardar `installer/logs/install-report.json`.

## Stack base de aplicacion

- Python compatible con ML.
- Git.
- Node.js LTS.
- npm.
- Flask.
- Flask-CORS.
- Flask-SocketIO.
- Eventlet o modo threading.
- psycopg para PostgreSQL.
- Vite.
- React.
- Three.js.
- Socket.IO client.

## Stack DB

- PostgreSQL.
- SQL Server.
- Cliente `psql`.
- Cliente `sqlcmd` o alternativa moderna disponible.
- Docker fallback para entornos donde la instalacion nativa sea dificil.

## Stack ML base

Paquetes solicitados por el usuario:

```bash
pip install torch torchvision torchaudio
pip install opencv-contrib-python
pip install numpy pandas matplotlib seaborn scikit-learn jupyter
pip install transformers datasets accelerate
pip install ultralytics
pip install albumentations tensorboard wandb
```

El instalador no debe ejecutar esos comandos sin seleccionar variante:

- CPU: usar wheels CPU.
- NVIDIA RTX: usar wheels CUDA compatibles con driver.
- macOS Apple Silicon: usar variante compatible con MPS cuando aplique.
- Docker GPU: usar imagen NVIDIA/PyTorch cuando el host soporte NVIDIA Container Toolkit.

## Stack RTX 4060/4070/4090

Secuencia:

1. Verificar `nvidia-smi`.
2. Verificar version del driver.
3. Verificar CUDA runtime compatible.
4. Elegir indice PyTorch CUDA desde el selector oficial.
5. Instalar `torch`, `torchvision`, `torchaudio` con indice CUDA.
6. Validar:

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

Regla: si `torch.cuda.is_available()` falla, no continuar instalando perfil GPU como exitoso; marcarlo como `degraded` y ofrecer CPU/Docker.

## Stack IA generativa

Perfil `gen-ai`:

- transformers
- datasets
- accelerate
- safetensors
- sentencepiece
- tokenizers
- peft
- diffusers
- bitsandbytes solo en Linux/NVIDIA compatible
- vllm solo en Linux/NVIDIA compatible
- ollama opcional, separado del core

## Stack vision industrial

Perfil `vision-industrial`:

- opencv-contrib-python
- ultralytics
- albumentations
- onnx
- onnxruntime o onnxruntime-gpu segun hardware
- pillow
- scikit-image
- tensorboard
- jupyterlab

## Stack agentes IA

Perfil `agents`:

- openai
- anthropic opcional si el usuario lo configura
- langchain opcional
- llama-index opcional
- pydantic
- httpx
- tenacity
- python-dotenv
- rich
- typer

Las claves API nunca se escriben dentro del repo. Solo `.env.local` ignorado por git.

## Stack MLOps

Perfil `mlops`:

- Docker.
- Docker Compose.
- MLflow.
- JupyterLab.
- PostgreSQL.
- MinIO opcional.
- Redis opcional.
- Prometheus/Grafana opcional, no en instalacion base.

## Windows

Script principal:

```powershell
installer/install.ps1 -Profile full
```

Wrapper:

```bat
installer\install.bat full
```

Plan:

- Usar PowerShell 7 si esta disponible.
- Usar `winget` para Git, Node.js, Python compatible, VS Code y Docker Desktop.
- SQL Server puede instalarse con winget o Docker.
- PostgreSQL puede instalarse con winget o Docker.
- NVIDIA: validar driver con `nvidia-smi`; si falta, abrir instruccion oficial y pedir reinicio.
- Crear `.venv` y usar pip dentro de `.venv`.

## Linux

Script principal:

```bash
./installer/install.sh --profile full
```

Plan:

- Detectar distro.
- Ubuntu/Debian: `apt`.
- Fedora/RHEL: `dnf`.
- Arch: `pacman`.
- Instalar build essentials.
- Instalar Docker Engine.
- Instalar PostgreSQL nativo o Docker.
- SQL Server nativo donde Microsoft soporte la distro; si no, Docker.
- NVIDIA: validar driver, CUDA y NVIDIA Container Toolkit cuando se use Docker GPU.
- Crear servicio systemd opcional.

## macOS

Script principal:

```bash
./installer/install.sh --profile full
```

Plan:

- Usar Homebrew.
- Instalar Git, Node.js, Python compatible, VS Code.
- PostgreSQL por Homebrew o Docker.
- SQL Server por Docker.
- Docker Desktop requerido para servicios SQL Server y MLOps.
- ML GPU NVIDIA no aplica en macOS moderno; usar CPU/MPS segun PyTorch soporte.

## Seguridad

- No pedir claves en texto visible si se puede evitar.
- No guardar passwords de DB en archivos versionados.
- `.env`, `.env.local`, `installer/logs/*.secrets.json` deben estar ignorados.
- Logs deben ocultar passwords y tokens.
- El instalador debe pedir confirmacion antes de:
  - instalar drivers,
  - reiniciar,
  - abrir puertos,
  - crear servicios,
  - instalar SQL Server nativo,
  - modificar PATH global.

## Resultado final esperado

El usuario ejecuta un solo comando:

```bash
./installer/install.sh --profile full
```

o en Windows:

```powershell
installer/install.ps1 -Profile full
```

Y al final obtiene:

- backend listo,
- frontend compilado,
- PostgreSQL configurado,
- SQL Server disponible si el perfil lo pidio,
- stack ML instalado segun hardware,
- Docker/MLOps listo si el perfil lo pidio,
- reporte de instalacion,
- app abriendo en `http://127.0.0.1:5000/`.

## Fuentes oficiales a usar durante implementacion

- PyTorch install selector: https://pytorch.org/get-started/locally/
- NVIDIA CUDA Linux guide: https://docs.nvidia.com/cuda/cuda-installation-guide-linux/
- NVIDIA cuDNN install guide: https://docs.nvidia.com/deeplearning/cudnn/installation/
- Docker Engine install: https://docs.docker.com/engine/install/
- Docker Desktop macOS: https://docs.docker.com/installation/mac/
- PostgreSQL downloads: https://www.postgresql.org/download/
- SQL Server Docker: https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker
- SQL Server tools: https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools
- VS Code setup: https://code.visualstudio.com/docs/setup/linux
- Node/npm install guidance: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm/
