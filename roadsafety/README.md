# 🚨 GuardianNodes RoadSoS — AI-Powered Emergency Road Accident Response System

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.67-FF4B4B.svg)](https://streamlit.io/)
[![NetworkX](https://img.shields.io/badge/networkx-3.7-orange.svg)](https://networkx.org/)
[![Plotly](https://img.shields.io/badge/plotly-7.1-00d2ff.svg)](https://plotly.com/)
[![Status](https://img.shields.io/badge/status-production--ready-2ed573.svg)](#)

> **Academic Mini-Project Submission**  
> **Team Name:** Coders  
> **Contributors:** Rohit Singh, Shawsti Singh, Utsav  
> **Domain:** Intelligent Transportation Systems (ITS) & Computer-Aided Dispatch (CAD)  
> **Deployment Node:** Delhi NCR Emergency Response Network (ERSS 112)

---

## 📖 Overview

**GuardianNodes RoadSoS** is an advanced Computer-Aided Dispatch (CAD) intelligence platform engineered to minimize emergency response times and safeguard the **"Golden Hour"** (the critical first 60 minutes after vehicular trauma).

When an accident occurs, the system:
1. **Understands & Triages**: Uses zero-shot NLP with entity extraction and negation detection to calculate an exact mathematical **Urgency Index (1.00 – 10.00)** and assign a **Golden Hour SLA**.
2. **Optimizes Dynamic Routes**: Snaps raw witness GPS coordinates to the nearest physical road intersection and calculates the fastest traffic-aware path using **NetworkX Dijkstra algorithms**.
3. **Overcomes RF Blackouts**: Relays emergency telemetry over an offline **BLE 5.0 / DSRC Vehicular Mesh Network (V2X)** with CRC-32 checksum integrity and automatic retransmissions.
4. **Coordinates Hospital Care**: Identifies the nearest capable trauma center (AIIMS, Safdarjung, RML, Max Saket) with free ICU beds and generates an automated **Common Alerting Protocol (CAP / OASIS)** emergency broadcast for ERSS 112.

---

## ⚡ Quick Start (One-Click Launch)

### Option 1: Double-Click Launcher (Windows)
Simply double-click **`run.bat`** in the project root directory! It will automatically launch the Streamlit command center in your default browser.

### Option 2: Command Line (PowerShell / Terminal)
```powershell
# Navigate to project directory
cd c:\Users\utsav\OneDrive\Desktop\miniProject

# Run via virtual environment
.\roadsafety\venv\Scripts\streamlit.exe run roadsafety\app.py
```

---

## 🧠 Core System Modules

### 1. Intelligent AI Triage Engine (`modules/triage_engine.py`)
- **Zero-Shot Classification**: DistilBERT / MNLI zero-shot pipeline with high-accuracy heuristic semantic fallback.
- **5 Emergency Classes**: *Critical Medical Trauma, Fire/Explosion, Vehicle Entrapment, Hazardous Material Leak, Minor Collision*.
- **Negation Logic**: Accurately recognizes statements like `"no injuries reported"` or `"zero casualties"` to suppress false high-urgency alarms.
- **Entity Extraction (NER)**: Parses casualty counts, vehicle types, fire/blast mentions, hazardous chemicals, and speeds.
- **Golden Hour SLA Enforcement**: Automatically bounds the dispatch timeline (&le; 8 min Critical, &le; 12 min High, &le; 20 min Moderate).
- **Multi-Modal Evidence Fusion**: Ingests camera, CCTV, or witness photo damage flags (*cabin intrusion, airbag deployment, dense smoke*) directly into urgency calculations.

### 2. Dynamic Dijkstra Graph Routing Engine (`modules/routing_engine.py`)
- **Municipal Road Graph**: 10&times;10 directed graph (100 nodes, ~180 directed edges) mapped to Delhi NCR landmarks.
- **GPS Nearest-Node Snapping**: Maps raw witness GPS coordinates (`lat`, `lon`) to the nearest road intersection.
- **Vehicle-Specific Penalties**: Custom multipliers for Fire Tenders, ALS Ambulances, Highway Patrol PCRs, HazMat Units, and Motorbike Medics.
- **Two-Leg Routing**: Simultaneously computes Leg 1 (Depot &rarr; Accident Scene) and Leg 2 (Accident Scene &rarr; Nearest Capable Trauma Hospital).

### 3. Decentralized V2X Mesh Relay Protocol (`modules/mesh_simulator.py`)
- **Compact 24-Byte Binary Frame**: Packed via Python `struct` (`!fffIHBB + CRC-32`):
  - Latitude (4B), Longitude (4B), Urgency Index (4B), Timestamp (4B), Sequence (2B), Flags (1B), Reserved (1B), and CRC-32 (4B).
- **Vehicular Ad-Hoc Network (VANET)**: Relays data across passing CATS Ambulances, Delhi Police PCRs, DTC Buses, and Smart Roadside Units (RSUs).
- **CRC-32 Error Correction**: Automatically identifies RF bit-flips and packet drops, triggering up to 3 automatic retransmissions.
- **Common Alerting Protocol (CAP)**: Generates ITU-T X.1303 / OASIS compliant JSON emergency alerts.

### 4. Regional Trauma Center Readiness
- Real-time coordination with premier tertiary trauma institutes in Delhi NCR:
  - **AIIMS Apex Trauma Centre** (Level-1 Apex Trauma Institute)
  - **Safdarjung Hospital Emergency Block** (Level-1 Burns & Trauma)
  - **Dr. Ram Manohar Lohia (RML) Hospital** (Level-2 Central Regional Facility)
  - **Max Super Speciality Hospital Saket** (Level-1 Cardiac & Neuro)
- Tracks available ICU beds, active trauma bays, blood bank supplies, and direct dispatch hotlines.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Runtime & Language** | Python 3.14 (64-bit) with localized isolated virtual environment |
| **Frontend UI** | Streamlit 1.67 with custom responsive dark glassmorphism CSS |
| **Graph & Pathfinding** | NetworkX 3.7 (Dijkstra Shortest Path, Single-Source Dijkstra) |
| **Natural Language Processing** | HuggingFace Transformers, Regex Semantic Tokenizer |
| **Visualization & Mapping** | Plotly 7.1 (Dark Scattermapbox, Polar Radar Charts, Spline Telemetry) |
| **Data Processing & Protocols** | Pandas 3.1, NumPy 2.5, Struct (Binary Packing), Binascii (CRC-32) |
| **Automated Export Suite** | FPDF (Project Documentation PDF), Python-PPTX (Presentation Slide Deck) |

---

## 📁 Project Directory Structure

```
miniProject/
├── run.bat                          # One-click Windows batch launcher
├── run.ps1                          # PowerShell launcher
├── roadsafety/
│   ├── app.py                       # Main Streamlit CAD command dashboard
│   ├── requirements.txt             # Project dependencies
│   ├── README.md                    # Project documentation
│   ├── Project_Documentation.html   # Comprehensive HTML documentation
│   ├── create_pdf.py                # Automated PDF report generator
│   ├── create_ppt.py                # Automated PowerPoint slide deck generator
│   ├── RoadSoS_Project_Document.pdf # Generated PDF project report
│   ├── Project_Presentation.pptx    # Generated PowerPoint slide deck
│   ├── .streamlit/
│   │   └── config.toml              # Streamlit server & theme configuration
│   ├── modules/
│   │   ├── __init__.py              # Package init
│   │   ├── triage_engine.py         # Multi-modal AI triage & NER engine
│   │   ├── routing_engine.py        # Dijkstra traffic-aware routing & landmark mapping
│   │   └── mesh_simulator.py        # V2X BLE/RF mesh simulator & CAP generator
│   └── venv/                        # Localized isolated Python virtual environment
```

---

## 📊 Automated Presentation & Document Generator

To re-generate the presentation slide deck and project documentation PDF at any time:

```powershell
# Generate PDF documentation
.\roadsafety\venv\Scripts\python.exe roadsafety\create_pdf.py

# Generate PowerPoint presentation
.\roadsafety\venv\Scripts\python.exe roadsafety\create_ppt.py
```

Both files are also downloadable with a single click inside **Tab 5 ("Project Docs & Presentation")** of the Streamlit application!

---

## 👥 Project Team

- **Team Name**: Coders
- **Team Leader**: Rohit Singh
- **Teammates**: Shawsti Singh, Utsav
- **Academic Year**: 2026
