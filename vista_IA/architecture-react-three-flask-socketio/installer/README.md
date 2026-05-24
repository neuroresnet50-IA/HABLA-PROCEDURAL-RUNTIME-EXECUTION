# HABLA Observer IA Installer

This installer turns the terminal UI prototype into a real staged installer.

Default launch installs the full stack:

```bash
./installer/install.sh
```

That opens the assistant box, asks what the client needs, shows the detected plan, installs/verifies dependencies, builds the frontend and writes a report.

Direct assistant mode:

```bash
./installer/install.sh --ask
```

The user can type a normal requirement there, for example:

```text
camaras USB, OpenCV, YOLO, PostgreSQL, dashboard React, sensores serial y reportes con matplotlib
```

Or a recipe name:

```text
industrial-vision
```

To skip the assistant and install full directly:

```bash
./installer/install.sh --profile full --execute --allow-system
```

To execute project-local commands:

```bash
./installer/install.sh --profile base --execute
```

To allow OS-level package installs too:

```bash
./installer/install.sh --profile full --execute --allow-system
```

Intelligent requirement planner:

```bash
./installer/install.sh --recipe industrial-vision
./installer/install.sh --from-requirement installer/client-requirement.example.txt
./installer/install.sh --requirement "camaras opencv yolo postgres dashboard react sensores serial"
```

The planner reads the client requirement and activates only the needed groups, for example `db`, `web-dev`, `vision-industrial`, `hardware-io-utils`, `agents`, `mlops` or `data-viz-ml-nlp-extended`.

Windows:

```powershell
installer\install.ps1
installer\install.ps1 -Ask
installer\install.ps1 -Profile full -Execute -AllowSystem
installer\install.ps1 -Profile base -Execute
installer\install.ps1 -Profile full -Execute -AllowSystem
installer\install.ps1 -Recipe industrial-vision
installer\install.ps1 -FromRequirement installer\client-requirement.example.txt
```

The launchers pause before closing so errors and the final report remain visible.
For automation, disable the pause:

```bash
HABLA_INSTALLER_NO_PAUSE=1 ./installer/install.sh --profile full
```

```powershell
installer\install.ps1 -Profile full -NoPause
```

Profiles:

- `base`
- `db`
- `web-dev`
- `ml-cpu`
- `ml-nvidia`
- `gen-ai`
- `vision-industrial`
- `agents`
- `mlops`
- `hardware-io-utils`
- `data-viz-ml-nlp-extended`
- `full`

Recipes:

- `base-app`
- `industrial-vision`
- `agent-platform`
- `ml-research`
- `data-dashboard`
- `iot-control`
- `document-ai`
- `security-observer`
- `rtx-vision`
- `full`

Reports are written to:

```text
installer/logs/
```

Important:

- `--execute` runs project commands such as creating `.venv`, installing Python requirements, running `npm install`, and building the frontend.
- `--allow-system` permits package manager commands such as `apt`, `winget`, `brew`, or Docker checks.
- `--requirement`, `--from-requirement` and `--recipe` enable automatic intelligent profile selection.
- SQL Server on macOS should run through Docker.
- NVIDIA/CUDA profile is marked degraded if `nvidia-smi` is missing.
