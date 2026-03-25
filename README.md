# COM2020 Team Project - Single-Scan Traceability Quest

The team project for the group 'HK Corner'. Intended to allow the user to enter or scan in product barcodes and view information about how the product was harvested, assembled and transported. Based on the specification for project 4. 

## Traceability Quest mission design

Traceability Quest questions are generated dynamically from the seeded product passport data when a player starts a mission run. The `missions` table is used to store generated mission history, player answers, score, and completion timestamps for progress tracking; it is not a static pre-seeded question bank.

## Team Members & Roles

- **Dawid Kwiecien** - Project Leader, Documentation Lead - GitHub: `Dawid-Kwiecien-86`
- **Simba Chan** - Programming Lead, Lead UI/UX Lead & Technical Lead - GitHub: `Shrlotia`
- **Cia Lloyd-Hole** - Data Lead - GitHub: `Cai7700`
- **Sylvester Koroma** - UI/UX Lead - GitHub: ``
- **Ali Mahdami** - Additional Programming & UI/UX Lead - GitHub: `aam232`
- **Johnny Lam Kwok King** - QA & Testing Lead & Technical Lead- GitHub: `johnny371123`

## Link to Scrum Board

- https://hkcorner.atlassian.net/jira/core/projects/ABCDE/board?filter=&groupBy=status

## How to run the Application (Vscode or GitHub Codespaces)

- Give permission to the shell script file
```bash
chmod +x run.sh
```

- Set an application secret before running in a shared or deployed environment
```bash
export SECRET_KEY="replace-with-a-long-random-value"
```

- Run the application by typing ```./run.sh```. This will check Python, Node.js, npm, `.venv`, Python packages, Node.js packages, and the frontend bundle. If something is missing, it will install/build it first.

- Access the application from your browser by shift-clicking on the ```http://127.0.0.1:8000``` link in the codespace terminal

## How to run the automated tests 

- Make sure you completed all instructions in the above section first

- Stop the application (if you have not already) by pressing ```Ctrl+C```

- If you want to activate the virtual environment manually
```bash
source .venv/bin/activate
```

- Run the full automated test suite
```bash
pytest -v
```

- You can also use the helper script
```bash
./pytest.sh
```

- If you want packaging-based installs instead of `requirements.txt`, install test extras
```bash
pip install -e ".[test]"
```

## How to run the Application (Windows 10 Local)

***Prerequisite**: must have **Python 3.11 (or higher)**, **PIP package installer** and **Node.js 24 (or higher)** installed*

- Move into the root folder of the code repository within the terminal (i.e.: ```cd Downloads\COM2020---Single-Scan-Traceability-Quest-main```)

- Set a secret key before running outside local development
```bat
set SECRET_KEY=replace-with-a-long-random-value
```

- Type in ```run``` or run ```run.bat``` to start the application.
  This will check Python, Node.js, npm, `.venv`, Python packages, Node.js packages, and the frontend bundle. If something is missing, it will install/build it first.

- You can access the application from your browser by typing ```http://127.0.0.1:8000``` into the address bar in your browser (***Note**: you can exit the application by pressing ```Ctrl+C```*)

## How to run the automated tests 

- Make sure you completed all instructions in the above section first

- Stop the application (if you have not already) by pressing ```Ctrl+C```

- If you want to activate the virtual environment manually in Command Prompt, use:
```bat
call .venv\Scripts\activate.bat
```

- If you are using PowerShell, use:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

- Run tests after `run.bat` has prepared the environment
```bat
pytest -v
```
