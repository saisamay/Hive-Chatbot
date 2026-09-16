# AmazonHelp Trust-Safe AI Support Agent

## Project Overview
This project implements an offline prototype (Track A MVP) of an AI-powered customer support agent for AmazonHelp. The primary objective is to build a "Trust-Safe" system that can resolve what it can prove, verify what it is unsure of, and explicitly escalate issues that demand human empathy, physical logistics, or advanced authority.

**Note:** This system is a proof-of-concept prototype. It is **not** production-ready and does not claim to outperform existing commercial baselines.

## Architecture and End-to-End Flow
The pipeline follows a modular, retrieval-augmented generation (RAG) architecture:
1. **Ingestion & Privacy:** Twitter support conversations are ingested, threads are reconstructed, and PII is scrubbed.
2. **Intent Classification:** Inbound messages are classified into a fixed taxonomy.
3. **Retrieval:** Relevant historical agent resolutions (playbooks) are fetched via a FAISS vector index.
4. **Safety & Capability:** A safety detector scans for safety vs frustration vs abuse, with serious safety/legal situations triggering escalation. A capability layer assesses if the system actually has the tools to fulfill the request.
5. **Trust Gate:** An orchestrator routes the conversation into one of three tiers (`AUTO_HANDLE`, `DEEP_ANALYSIS`, or `HUMAN_ESCALATION`).
6. **Grounded Generation:** A language model generates the final response grounded purely in the retrieved evidence.

## Scope: Track A MVP
This project is built under **Track A** constraints:
- Operates entirely offline using historical dataset dumps.
- Focuses on classification, retrieval, and trust-routing.
- Includes a local interactive UI for testing.

**Explicit Track B Exclusions:**
- No live connection to the Twitter API.
- No live backend writes, real-time ticket creation, or active CRM mutation.

## Dataset and Privacy
The system leverages a large historical dataset of customer service interactions on Twitter. 
- All data ingested into the pipeline undergoes strict PII scrubbing. Known entities like emails, phone numbers, and addresses are replaced with placeholders (e.g., `[LOCATION_1]`, `[PERSON_1]`). 
- Raw datasets are explicitly excluded from version control to prevent exposure.

## Thread Reconstruction and Lifecycle Semantics
Conversations are reconstructed from flat CSVs into tree-based dialogue structures. The conversational lifecycle is explicitly decoupled from the resolution outcome:
- **ACTIVE:** The last message was inbound (from the customer), awaiting a system response.
- **WAITING:** The last message was outbound (from the agent), awaiting customer follow-up (silence does *not* imply closure).
- **CLOSED:** Determined directly by the resolution outcome (i.e. `outcome == "RESOLVED"` maps to `CLOSED`).

## Intent Taxonomy
Inbound requests are classified into the following canonical taxonomy:
- `Delivery_Delayed`
- `Package_Missing_Or_Stolen`
- `Order_Cancellation`
- `Refund_Or_Return_Status`
- `Account_Compromised`
- `Item_Damaged_Or_Defective`
- `Fraud_Or_Fake_Product`
- `Digital_Content_Or_Streaming`
- `Billing_Or_Prime_Charge`
- `Device_Technical_Issue`
- `UNKNOWN`

## Retrieval and Grounded Generation
The retrieval engine uses MiniLM embeddings stored in a FAISS index to find historical precedents. The generator uses these retrieved precedents to draft a response. Historical playbooks are not truth. Current verified backend/policy/capability evidence has higher authority.

## Trust Gate
The Trust Gate routes conversations based on confidence, safety, and capability:
- **AUTO_HANDLE:** Fully confident, high evidence similarity, standard request.
- **DEEP_ANALYSIS:** Moderate confidence or missing context; the system attempts to clarify or research further. Capability UNKNOWN immediately routes here.
- **HUMAN_ESCALATION:** Triggered only after Deep verification fails, or by hard Human rules which include: explicit human request, serious safety/legal situations, suspicious identity, or a persistent loop after Deep.

## Evaluation Methodology and Gold-Set Isolation
The system is evaluated against a locked canonical "Gold Set" of 200 human-labeled cases.
- **Absolute Segregation:** The 200 canonical IDs are strictly excluded from the classifier's training, validation, and calibration sets, as well as the FAISS retrieval index.
- **Hold-out Integrity:** The 200 human-labeled gold cases are held out from training, validation, calibration, and retrieval.

## Final Verified Metrics
Evaluated on the locked 200-case canonical gold set (using Gemini as the generator):
- **Intent Accuracy:** 49.5%
- **Intent Macro F1:** 47.5%
- **Retrieval Proxy P@1:** 33.0%
- **Retrieval Proxy P@3:** 21.5%
- **Safety Precision:** 100%
- **Safety Recall:** 29.4%
- **Capability Accuracy:** 86.5%
- **Trust Gate Correctly Predicted:** Auto: 0, Deep: 78, Human: 5

## Known Limitations and Failure Modes
- **Safety Recall:** The safety detector exhibits low recall (29.4%), meaning it occasionally misses nuanced safety or frustration cues.
- **Retrieval:** P@1 is relatively low, meaning the single most relevant playbook isn't always the first result fetched, leading to generation reliance on secondary matches.
- **Intent Drift:** The classifier struggles with overlapping classes like `Package_Missing` vs `Delivery_Delayed`.

## Setup and Running Locally

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. UI and OpenAI Provider Setup
The interactive UI can be powered by either Gemini or OpenAI models.
Create a `.env` file in the root directory:
```env
GENERATOR_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=<your_configured_model>
```
*Note: API keys are strictly evaluated server-side. Do not expose them in the frontend.*

### 3. Run the Local Interactive UI
Spin up the Flask server which serves both the frontend and backend API:
```bash
PYTHONPATH=. ./venv/bin/python3 src/api/server.py
```
Navigate to `http://127.0.0.1:5000` in your browser.

### 4. Run the Final Evaluation
The evaluation is hardcoded to run reproducibly against the Gemini provider to prevent environment variables from altering the locked metrics.
```bash
PYTHONPATH=. ./venv/bin/python3 src/evaluation/run_final_evaluation.py
```
