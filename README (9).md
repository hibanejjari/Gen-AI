# LLM Council Local Deployment

## Group Information

TD Group: [PUT YOUR TD GROUP HERE]

### Team Members and Roles

| Name     | Machine Name | Role | Model |
|----------|--------------|------|-------|
| Cyprien  | cyprien | Council Member | llama3.2:1b |
| Lisa     | lisa-vivo15 | Council Member | phi3:mini |
| Neil     | neil | Council Member | smollm2:135m |
| Wendy    | wendy | Council Member | qwen2:1.5b |
| Hiba     | hiba | Council Member | qwen2.5:0.5b |
| Hiba     | hiba | Orchestrator Admin + Chairman | llama3.2:3b |

---

## Project Overview

This project is inspired by Andrej Karpathy’s LLM Council concept.  
Instead of relying on a single Large Language Model (LLM), multiple LLMs collaborate to answer a user query.

The original implementation relied on cloud-based APIs.  
This project was refactored so that the entire system runs locally and supports distributed execution across multiple machines.

Key goals:
- No cloud APIs
- All LLMs run locally (Ollama)
- Multiple machines communicate via REST APIs
- The full 3-stage workflow runs end-to-end

---

## What Is the LLM Council

The LLM Council is a three-stage reasoning system:

1. Multiple LLMs answer the same question independently  
2. LLMs anonymously review and rank each other’s answers  
3. A Chairman LLM synthesizes all outputs into a final response  

The user can inspect intermediate outputs (opinions and reviews).

---

## Council Workflow

### Stage 1: First Opinions
- The user submits a question.
- Each council node generates an answer independently.
- The orchestrator collects and returns all answers.

### Stage 2: Review and Ranking
- Each council node reviews anonymized answers from the other nodes.
- Identities are hidden (answers are labeled A, B, C, etc.).
- Each answer is scored on:
  - Accuracy (0–10)
  - Insight (0–10)
- Each reviewer also returns a ranking (best to worst).

### Stage 3: Chairman Final Answer
- A dedicated Chairman node receives:
  - All anonymized answers
  - All review scores and rankings
- The Chairman synthesizes a single final answer.

---

## Distributed Architecture and Networking

### Use of Tailscale

Some team members were not able to meet physically or share the same local network.  
To allow remote machines to communicate securely over distance, Tailscale was used.

What we did:
- Created one Tailscale account
- Connected all team machines to the same private Tailscale network
- Each machine received a private Tailscale IP address
- All REST API calls use Tailscale IPs, so machines can communicate from different locations

This enabled a fully distributed deployment across multiple places while keeping traffic private and encrypted.

---

## System Architecture

### Components

Orchestrator
- Central coordination service
- Loads configuration from config.yaml
- Monitors node health
- Executes the 3-stage workflow
- Serves the web interface and API

Council Nodes
- One service per model
- Endpoints: health, opinion, review, info
- Generates opinions (Stage 1) and reviews other answers (Stage 2)

Chairman
- Separate service with its own model instance
- Endpoints: health, synthesize
- Only synthesizes (Stage 3), does not generate first opinions

### Communication

All communication is REST over HTTP:
- Orchestrator calls council nodes for opinions and reviews
- Orchestrator calls chairman for synthesis
- Web UI calls orchestrator to run the workflow and display results

---

## Code Explanation and Logic

### Configuration Logic (config.yaml)
- The orchestrator reads config.yaml at startup.
- Each council node entry includes:
  - id, name, url (Tailscale IP and port), model, enabled
- The chairman entry includes its own url and model.
- Timeouts and fallback settings are also defined in config.yaml.

This design avoids hardcoding IPs in Python code and makes distributed deployment easy to update.

### Health Monitoring
- Each node exposes GET /health.
- The orchestrator periodically checks /health for all nodes.
- Nodes are marked healthy or unhealthy.
- The system can process a query only if:
  - The number of healthy council nodes is at least min_council_members
  - The chairman is healthy

This explains why offline nodes appear in the UI and why the workflow may still run with fewer nodes.

### Stage 1 Implementation (Opinions)
- Orchestrator calls POST /opinion on each healthy council node.
- Each node uses Ollama to generate text and returns:
  - node_id, model, answer, generation_time_ms
- Orchestrator collects results into a dictionary keyed by node_id.

### Anonymization (Important for Stage 2)
- Orchestrator maps node IDs to anonymous labels A, B, C, etc.
- Only the text is shared with reviewers.
- Reviewers do not see which model produced which label.

### Stage 2 Implementation (Reviews)
- Each node receives:
  - question
  - responses: { "A": "...", "B": "...", ... }
- Each node generates strict JSON:
  - scores: { label: {accuracy, insight}, ... }
  - ranking: [label1, label2, ...]
- To prevent missing values and N/A in the UI:
  - the node normalizes parsed JSON
  - ensures every label has numeric accuracy and insight
  - clamps values to [0, 10]
  - ensures ranking only contains allowed labels

### Scoring Display Logic (Frontend)
- The frontend aggregates reviewer scores per label:
  - Average accuracy across reviewers
  - Average insight across reviewers
  - Total score is derived from these averages
- If many nodes are offline, fewer reviews are collected and averages are less stable.

### Stage 3 Implementation (Synthesis)
- Orchestrator calls POST /synthesize on the chairman with:
  - question
  - answers (A, B, C, ...)
  - reviews (scores and rankings)
- Chairman generates the final answer and returns it to the orchestrator.
- Orchestrator returns the final response to the UI with timing information.

---

## Configuration Files

- config.yaml  
  Main configuration used by the orchestrator.

- config.distributed.yaml  
  Template configuration for distributed runs (useful when changing IPs or machines).

---

## Running the Demo

1. Start Ollama on all machines  
2. Start each council node service on its assigned machine  
3. Start the chairman service  
4. Start the orchestrator service  
5. Open the web interface and submit a question  

---

## Work Path and Collaboration

This is the path we followed as a team to complete the project:

1. Start from the original LLM Council idea  
   We studied the council workflow and the original cloud-based version to understand the stages.

2. Remove cloud dependencies  
   We replaced cloud calls with local inference using Ollama on each machine.

3. Split the system into services  
   We implemented separate FastAPI services for:
   - council nodes
   - chairman
   - orchestrator

4. Make the system distributed  
   We replaced localhost-only assumptions with configurable URLs and enabled remote nodes.

5. Add secure networking for remote collaboration  
   Because the team could not always meet physically, we used Tailscale to connect machines at distance.

6. Add configuration and robustness  
   We added config.yaml to manage node URLs, timeouts, and fallback rules.  
   We added health checks to automatically detect offline machines.

7. Improve usability and testing  
   We added a web UI to inspect all stages and a test client to validate system health and run queries.

---

## Improvements Over the Original Implementation

- Removed all cloud-based APIs
- Fully local inference using Ollama
- Distributed multi-machine execution through REST APIs
- Secure networking using Tailscale
- Clear separation between council nodes and chairman
- Robust handling of offline nodes with health checks and fallback rules
- Full visibility of intermediate results (opinions and reviews)

---

## Media

Create a folder named docs at the project root.

Inside it, create:
- docs/screenshots
- docs/video

Place the following files:

Screenshots:
- docs/screenshots/system_status.png
- docs/screenshots/stage_1.png
- docs/screenshots/stage_2.png
- docs/screenshots/stage_3.png

Video:
- docs/video/demo.mp4

The video demonstrates:
- startup of services
- node health and distributed connectivity
- Stage 1 opinions
- Stage 2 review scores and ranking
- Stage 3 final answer

---

## Conclusion

This project demonstrates a fully local, distributed LLM Council running across multiple machines.
It fulfills the mandatory requirements and showcases collaborative reasoning using local LLMs connected over a network.
