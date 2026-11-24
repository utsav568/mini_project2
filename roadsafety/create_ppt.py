"""
create_ppt.py
=============
Automated PowerPoint Presentation Generator for GuardianNodes RoadSoS.
Generates an academic mini-project slide deck suitable for evaluation.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def create_presentation():
    prs = Presentation()
    
    # Define slide layouts
    title_layout = prs.slide_layouts[0]
    bullet_layout = prs.slide_layouts[1]
    
    # ── Slide 1: Title Slide ──────────────────────────────────────────────
    slide1 = prs.slides.add_slide(title_layout)
    title1 = slide1.shapes.title
    subtitle1 = slide1.placeholders[1]
    
    title1.text = "GuardianNodes RoadSoS"
    subtitle1.text = (
        "AI-Powered Emergency Road Accident Response, Dynamic Routing & V2X Mesh System\n\n"
        "Team: Coders\n"
        "Contributors: Rohit Singh, Shawsti Singh, Utsav\n"
        "Deployment Node: Delhi NCR Emergency Network (ERSS 112)"
    )

    # ── Slide 2: Problem Statement & Golden Hour Challenge ────────────────
    slide2 = prs.slides.add_slide(bullet_layout)
    slide2.shapes.title.text = "Problem Statement & The Golden Hour"
    tf2 = slide2.shapes.placeholders[1].text_frame
    tf2.text = "Critical delays during the 'Golden Hour' (first 60 min) lead to preventable fatalities."
    p = tf2.add_paragraph()
    p.text = "Imprecise Manual Triage: Emergency operators struggle to quickly assess crash severity from panicked witness calls."
    p = tf2.add_paragraph()
    p.text = "Urban Traffic Bottlenecks: Standard routing fails to factor in dynamic vehicle penalties and congestion choke points."
    p = tf2.add_paragraph()
    p.text = "Communication Blackouts: Cellular tower outages or congestion on highways prevent emergency telemetry transmission."

    # ── Slide 3: End-to-End System Architecture ───────────────────────────
    slide3 = prs.slides.add_slide(bullet_layout)
    slide3.shapes.title.text = "System Architecture & Core Pipeline"
    tf3 = slide3.shapes.placeholders[1].text_frame
    tf3.text = "1. Incident Intake & Multi-Modal Triage: Free-text reports & camera evidence analyzed instantly."
    p = tf3.add_paragraph()
    p.text = "2. Mathematical Urgency Scoring: Sigmoid-bounded Urgency Index (1.00 – 10.00) + Golden Hour SLA."
    p = tf3.add_paragraph()
    p.text = "3. GPS Snapping & Dijkstra Corridor: Incident lat/lon mapped to network nodes for traffic-aware vehicle dispatch."
    p = tf3.add_paragraph()
    p.text = "4. V2X Offline Mesh Protocol: 24-byte binary packet relay with CRC-32 automated retransmissions."
    p = tf3.add_paragraph()
    p.text = "5. Hospital Readiness & CAP Broadcast: Real-time ICU bed allocation & automated ERSS 112 alerts."

    # ── Slide 4: Multi-Modal Intelligent Triage Engine ────────────────────
    slide4 = prs.slides.add_slide(bullet_layout)
    slide4.shapes.title.text = "Module 1: Intelligent AI Triage Engine"
    tf4 = slide4.shapes.placeholders[1].text_frame
    tf4.text = "Zero-Shot Classification (DistilBERT / MNLI) + High-Accuracy Heuristic Engine."
    p = tf4.add_paragraph()
    p.text = "5 Emergency Categories: Fire/Explosion, Critical Trauma, Vehicle Entrapment, HazMat Leak, Minor Crash."
    p = tf4.add_paragraph()
    p.text = "Negation Awareness: Accurately identifies 'no injuries' to suppress false high-urgency alarms."
    p = tf4.add_paragraph()
    p.text = "Entity Extraction: RegEx NER extracts vehicle counts, casualties, speeds, and chemical hazards."
    p = tf4.add_paragraph()
    p.text = "Golden Hour SLA Enforcement: Strict target response thresholds (<= 8 min Critical, <= 12 min High)."

    # ── Slide 5: Traffic-Aware Dynamic Graph Routing ──────────────────────
    slide5 = prs.slides.add_slide(bullet_layout)
    slide5.shapes.title.text = "Module 2: Traffic-Aware Dijkstra Routing"
    tf5 = slide5.shapes.placeholders[1].text_frame
    tf5.text = "NetworkX Directed Graph: Municipal road network mapped to Delhi NCR landmarks."
    p = tf5.add_paragraph()
    p.text = "GPS Nearest-Node Snapping: Matches user-entered GPS coordinates to physical road intersections."
    p = tf5.add_paragraph()
    p.text = "Composite Edge Cost = Base_Distance x Road_Type x Traffic_Level x Vehicle_Penalty."
    p = tf5.add_paragraph()
    p.text = "Vehicle Customization: Tailored penalties for Fire Engines, ALS Ambulances, HazMat Units, and Medics."
    p = tf5.add_paragraph()
    p.text = "Two-Leg Response: Computes primary arrival corridor + secondary hospital evacuation route."

    # ── Slide 6: Offline V2X Mesh Network Protocol ────────────────────────
    slide6 = prs.slides.add_slide(bullet_layout)
    slide6.shapes.title.text = "Module 3: BLE/Wi-Fi Direct V2X Mesh Relay"
    tf6 = slide6.shapes.placeholders[1].text_frame
    tf6.text = "Decentralized Ad-Hoc Communication: Zero reliance on cellular towers or internet connectivity."
    p = tf6.add_paragraph()
    p.text = "Compact 24-Byte Binary Struct: (!fffIHBB + 4-byte CRC-32) encoding coordinates, urgency, and timestamp."
    p = tf6.add_paragraph()
    p.text = "Vehicular Hops: Relays through passing ambulances, police patrol cars, city buses, and roadside units."
    p = tf6.add_paragraph()
    p.text = "CRC-32 Error Correction: Automatic bit-flip detection with up to 3 automatic retransmission attempts."
    p = tf6.add_paragraph()
    p.text = "Common Alerting Protocol (CAP): Generates OASIS-compliant JSON alert broadcasts for national ERSS 112."

    # ── Slide 7: Regional Trauma Care & Hospital Fleet ────────────────────
    slide7 = prs.slides.add_slide(bullet_layout)
    slide7.shapes.title.text = "Module 4: Hospital Trauma Fleet Coordination"
    tf7 = slide7.shapes.placeholders[1].text_frame
    tf7.text = "Delhi NCR Apex Facilities: AIIMS Trauma Centre, Safdarjung Hospital, Dr. RML Hospital, Max Saket."
    p = tf7.add_paragraph()
    p.text = "Live Resource Tracking: Real-time monitoring of available ICU beds, trauma bays, and blood bank units."
    p = tf7.add_paragraph()
    p.text = "Automated Facility Matching: Assigns patients to the nearest hospital capable of treating the triaged trauma."
    p = tf7.add_paragraph()
    p.text = "Direct Emergency Hotline Integration: Enables instant medical coordination before ambulance arrival."

    # ── Slide 8: Real-Time Operations Dashboard & Analytics ───────────────
    slide8 = prs.slides.add_slide(bullet_layout)
    slide8.shapes.title.text = "Module 5: Real-Time Operations Telemetry"
    tf8 = slide8.shapes.placeholders[1].text_frame
    tf8.text = "Interactive CAD Interface: Sleek dark glassmorphism dashboard built with Streamlit and Plotly."
    p = tf8.add_paragraph()
    p.text = "Performance Metrics: Mean Response ETA, Mesh Delivery Rate, Critical Incident Percentile."
    p = tf8.add_paragraph()
    p.text = "Visual Telemetry: Response ETA trendlines, Mesh delivery bar charts, Incident category distribution."
    p = tf8.add_paragraph()
    p.text = "Data Persistence & Export: Filterable dispatch history with one-click CSV export."

    # ── Slide 9: Technology Stack & Implementation ────────────────────────
    slide9 = prs.slides.add_slide(bullet_layout)
    slide9.shapes.title.text = "Technology Stack & Engineering"
    tf9 = slide9.shapes.placeholders[1].text_frame
    tf9.text = "Frontend: Streamlit 1.67 with custom CSS glassmorphism & responsive layout."
    p = tf9.add_paragraph()
    p.text = "Language & Environment: Python 3.14 (64-bit) with localized isolated virtual environment."
    p = tf9.add_paragraph()
    p.text = "Machine Learning: HuggingFace Transformers, PyTorch, Custom Regex Semantic Tokenizer."
    p = tf9.add_paragraph()
    p.text = "Algorithms & Data: NetworkX 3.7 (Dijkstra), Pandas 3.1, NumPy 2.5, SciPy."
    p = tf9.add_paragraph()
    p.text = "Networking & Serialization: Python Struct (Binary Packing), Binascii (CRC-32), JSON."
    p = tf9.add_paragraph()
    p.text = "Document Generation: FPDF (Automated PDF Reports), Python-PPTX (Automated Slide Decks)."

    # ── Slide 10: Conclusion & Thank You ──────────────────────────────────
    slide10 = prs.slides.add_slide(title_layout)
    title10 = slide10.shapes.title
    subtitle10 = slide10.placeholders[1]
    
    title10.text = "Thank You!"
    subtitle10.text = (
        "GuardianNodes RoadSoS — Saving Lives Within the Golden Hour\n\n"
        "Questions & Discussion Welcome\n\n"
        "Team: Coders\n"
        "Contributors: Rohit Singh, Shawsti Singh, Utsav"
    )

    prs.save('Project_Presentation.pptx')
    print("Presentation created successfully as Project_Presentation.pptx")

if __name__ == '__main__':
    create_presentation()
