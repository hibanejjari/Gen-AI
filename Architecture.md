Here you can find the architecture behind our project and the folder structure indicating what each file is used for : 
## Architecture Overview (Diagram)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               LLM COUNCIL                                    │
│                    Distributed Local Deployment (Tailscale)                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: HIBA                                                                      │
│ Roles: Orchestrator + UI + Chairman + Council Node                            │
│                                                                              │
│ Services                                                                      │
│  - frontend/index.html                                                        │
│  - orchestrator/main.py   (8080)                                              │
│  - chairman/main.py       (9000)                                              │
│  - council_node/main.py   (5001)                                              │
│                                                                              │
│ Responsibilities                                                             │
│  - Entry point for UI                                                        │
│  - Coordinates workflow                                                      │
│  - Health checks & aggregation                                                │
│  - Final synthesis (Chairman)                                                 │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ REST over Tailscale (http://100.x.x.x)
                │
                │ Stage 1: POST /opinion
                │ Stage 2: POST /review
                │ Stage 3: POST /synthesize
                │
                ▼
        ┌──────────────────────┬──────────────────────┬──────────────────────┐
        │                      │                      │                      │
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ PC: CYPRIEN           │ │ PC: LISA-VIVO15      │ │ PC: NEIL              │ │ PC: WENDY            │
│ Council Node 1        │ │ Council Node 2        │ │ Council Node 3        │ │ Council Node 5        │
│                       │ │                       │ │                       │ │                       │
│ council_node/main.py  │ │ council_node/main.py  │ │ council_node/main.py  │ │ council_node/main.py  │
│ port: 5001            │ │ port: 5001            │ │ port: 5001            │ │ port: 5001            │
│                       │ │                       │ │                       │ │                       │
│ Endpoints             │ │ Endpoints             │ │ Endpoints             │ │ Endpoints             │
│  - /health            │ │  - /health            │ │  - /health            │ │  - /health            │
│  - /opinion           │ │  - /opinion           │ │  - /opinion           │ │  - /opinion           │
│  - /review            │ │  - /review            │ │  - /review            │ │  - /review            │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```
## The project structure and role of each file : 

```

Gen-AI-main/
├── chairman/                          -> Agent/service: “Chairman” role entrypoint
│   ├── __init__.py                    -> Package marker for chairman module
│   └── main.py                        -> Runs the Chairman logic (starts its workflow/API)
│
├── common/                            -> Shared utilities used by all services
│   ├── __init__.py                    -> Package marker for common module
│   ├── config.py                      -> Loads/handles config values (e.g., from config.yaml)
│   ├── http_client.py                 -> Reusable HTTP requests client (calls between services/APIs)
│   └── logging_config.py              -> Central logging setup (format, level, handlers)
│
├── council_node/                      -> Agent/service: “Council Node” entrypoint
│   ├── __init__.py                    -> Package marker for council_node module
│   └── main.py                        -> Runs the Council Node logic (starts its workflow/API)
│
├── frontend/                          -> Simple UI layer
│   └── index.html                     -> Web page to interact with the system (basic front-end)
│
├── images/                            -> Documentation assets ( screenshots)                 
│
├── orchestrator/                      -> Coordinator service (routes tasks between agents)
│   ├── __init__.py                    -> Package marker for orchestrator module
│   └── main.py                        -> Starts the orchestrator (dispatch/coordination logic)
│
├── .gitignore                         -> Git ignore rules (what not to commit)
├── Architecture Overview.md           -> High-level architecture explanation (components + flow)
├── README(2).md                       -> Setup/guide + usage steps + references to screenshots in /images
├── README.md                          -> Project overview (short intro / quick summary)
├── config.yaml                        -> Main configuration file (ports, endpoints, model settings, etc.)
└── requirements.txt                   -> Python dependencies to install (pip install -r ...)

```
