# COM2020 Team Project - Single-Scan Traceability Quest

The team project for the group 'HK Corner'. Intended to allow the user to enter or scan in product barcodes and view information about how the product was harvested, assembled and transported. Based on the specification for project 4. 

## Team Members & Roles

- **Dawid Kwiecien** - Project Leader, Technical Lead
- **Simba Chan** - Programming Lead
- **Cia Lloyd-Hole** - Data Lead
- **Sylvester Koroma** - Requirements Lead, Documentation Lead
- **Ali Mahdami** - UI/UX Lead
- **Johnny Lam Kwok King** - QA & Testing Lead

## Link to Scrum Board

- https://hkcorner.atlassian.net/jira/core/projects/ABCDE/board?filter=&groupBy=status

## How to run the Application (GitHub Codespaces)

- Giving permisson to the shell script file
```chmod +x build.sh run.sh```

- Get venv and Install the requirements
```./build.sh```

- Run the Application
```./run.sh```

- Access the application from your browser by shift-clicking on the ```http://127.0.0.1:8000``` link in the codespace terminal

## How to run the Application (Windows 10 Local)

***Prerequisite**: must have **Python 3.11 (or higher)** and **PIP package installer** installed*

- Move into the root folder of the code repository within the terminal (i.e.: ```cd Downloads\COM2020---Single-Scan-Traceability-Quest-main```)

- Type in ```build``` to build the ```.venv``` directory and install all of the required PyPi packages

- Type in ```run``` to start the application

- You can access the application from your browser by typing ```http://127.0.0.1:8000``` into the address bar in your browser (***Note**: you can exit the application by pressing ```Ctrl+C```*)
