
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
