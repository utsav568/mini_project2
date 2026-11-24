"""
create_pdf.py
=============
Automated PDF Project Documentation Generator for GuardianNodes RoadSoS.
Generates an academic mini-project report suitable for university evaluation.
"""

from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 102, 204)
        self.cell(0, 8, 'GuardianNodes RoadSoS - AI-Powered Emergency Response System', border=0, ln=1, align='C')
        self.set_draw_color(0, 150, 255)
        self.line(10, 18, 200, 18)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Team Coders - Mini Project Documentation', 0, 0, 'C')

def create_document():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title Block
    pdf.set_text_color(10, 20, 40)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 14, "GuardianNodes RoadSoS", ln=True, align='C')
    
    pdf.set_font("Arial", "I", 12)
    pdf.set_text_color(80, 90, 110)
    pdf.cell(0, 7, "AI-Powered Real-Time Road Accident Triage, Dynamic Routing & V2X Mesh System", ln=True, align='C')
    pdf.ln(4)
    
    # Team & Project Metadata Box
    pdf.set_fill_color(240, 245, 255)
    pdf.set_draw_color(180, 200, 230)
    pdf.rect(10, pdf.get_y(), 190, 26, 'DF')
    pdf.set_xy(14, pdf.get_y() + 3)
    pdf.set_font("Arial", "B", 9.5)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(90, 6, "Team Name: Coders", ln=False)
    pdf.cell(90, 6, "Project Domain: Intelligent Transport & Emergency CAD", ln=True)
    pdf.set_x(14)
    pdf.cell(90, 6, "Team Leader: Rohit Singh", ln=False)
    pdf.cell(90, 6, "Teammates: Shawsti Singh, Utsav", ln=True)
    pdf.set_x(14)
    pdf.cell(90, 6, "Target Deployment: Delhi NCR Emergency Network (112)", ln=False)
    pdf.cell(90, 6, "Implementation: Python 3.14 + Streamlit 1.67", ln=True)
    pdf.ln(10)
    
    # 1. Executive Summary & Problem Statement
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(0, 80, 160)
    pdf.cell(0, 7, "1. Executive Summary & Problem Statement", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5.5, (
        "In vehicular trauma management, the 'Golden Hour' principle dictates that rapid medical intervention "
        "within the first 60 minutes dramatically increases survival rates. However, modern emergency dispatch "
        "faces severe bottlenecks: delayed bystander reporting, inaccurate manual triage, congested urban traffic "
        "corridors, and communication blackouts in remote or damaged highway zones.\n\n"
        "GuardianNodes RoadSoS delivers an end-to-end, Computer-Aided Dispatch (CAD) platform combining: "
        "(1) AI-driven Zero-Shot Classification triage with casualty and hazard entity extraction; "
        "(2) NetworkX traffic-aware Dijkstra graph routing snapped to GPS intersections; "
        "(3) A decentralized BLE 5.0 / DSRC V2X Mesh Network protocol with CRC-32 automated error correction; "
        "(4) Real-time Trauma Hospital coordination with automated ICU bed allocation and Common Alerting Protocol (CAP) broadcasting."
    ))
    pdf.ln(3)
    
    # 2. Key Modules & Technical Architecture
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(0, 80, 160)
    pdf.cell(0, 7, "2. Key Modules & Architectural Design", ln=True)
    
    # A
    pdf.set_font("Arial", "B", 10.5)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 6, "A. Intelligent Zero-Shot Triage Engine & Entity Extraction", ln=True)
    pdf.set_font("Arial", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, (
        "- Dual-Mode Classification: DistilBERT Zero-Shot Classification with high-accuracy heuristic semantic fallback.\n"
        "- Entity Extraction: Automatically parses casualty counts, vehicle types, fire/blast mentions, and hazmat leaks.\n"
        "- Negation Handling: Accurately identifies expressions like 'no injuries' or 'zero casualties' to prevent false alarms.\n"
        "- Golden Hour SLA Window: Automatically assigns maximum target response SLAs (<= 8 min Critical, <= 12 min High).\n"
        "- Multi-Modal Tag Fusion: Integrates visual evidence flags (cabin intrusion, airbag deployment, dense smoke) into urgency."
    ))
    pdf.ln(2)
    
    # B
    pdf.set_font("Arial", "B", 10.5)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 6, "B. Traffic-Aware Dijkstra Routing Engine & Landmark Snapping", ln=True)
    pdf.set_font("Arial", "", 9.5)
    pdf.multi_cell(0, 5, (
        "- Municipal Road Graph: 10x10 directed network topology mapped to Delhi NCR coordinates.\n"
        "- Dynamic Cost Weighting: Cost = Base_Distance x Road_Multiplier x Traffic_Level x Vehicle_Road_Penalty.\n"
        "- GPS Nearest-Node Snapping: Automatically translates incident coordinates to the nearest physical road intersection.\n"
        "- Designated Landmark Corridors: Generates navigation waypoints between Connaught Place, Ring Road, AIIMS, and NH-48.\n"
        "- Hospital Evacuation Leg: Identifies the nearest capable trauma center and plots the secondary evacuation corridor."
    ))
    pdf.ln(2)
    
    # C
    pdf.set_font("Arial", "B", 10.5)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 6, "C. Offline V2X Mesh Relay Protocol & CAP Broadcast", ln=True)
    pdf.set_font("Arial", "", 9.5)
    pdf.multi_cell(0, 5, (
        "- Compact 24-Byte Binary Frame: Formatted as !fffIHBB + 4-byte CRC-32 checksum containing coordinates, urgency, and flags.\n"
        "- Ad-Hoc Multi-Hop Routing: Relays packets through passing ambulances, police patrol cars, buses, and smart RSUs.\n"
        "- Error Detection & Retransmission: Detects bit-flips and RF loss via CRC-32, automatically triggering up to 3 retransmissions.\n"
        "- Common Alerting Protocol (CAP): Generates OASIS-compliant JSON alert payloads for ERSS 112 and CATS ambulance terminals."
    ))
    pdf.ln(3)
    
    # 3. Technology Stack
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(0, 80, 160)
    pdf.cell(0, 7, "3. Implementation & Technology Stack", ln=True)
    pdf.set_font("Arial", "", 9.5)
    pdf.cell(0, 5, "- Runtime & Environment: Python 3.14 (64-bit) with localized isolated virtual environment", ln=True)
    pdf.cell(0, 5, "- Frontend & UI: Streamlit 1.67 featuring responsive dark glassmorphism styling", ln=True)
    pdf.cell(0, 5, "- Algorithms: NetworkX 3.7 (Dijkstra Shortest Path, Single-Source Pathfinding)", ln=True)
    pdf.cell(0, 5, "- Machine Learning & NLP: HuggingFace Transformers, Regex Semantic Tokenizer", ln=True)
    pdf.cell(0, 5, "- Visualization & Maps: Plotly 7.1 (Dark Scattermapbox, Radar Polar Charts, Spline Telemetry)", ln=True)
    pdf.cell(0, 5, "- Data Processing & Protocol: Pandas 3.1, NumPy 2.5, Struct (Binary Encoding), Binascii (CRC-32)", ln=True)
    pdf.ln(3)
    
    # 4. Regional Trauma Care & Impact
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(0, 80, 160)
    pdf.cell(0, 7, "4. Hospital Trauma Fleet Coordination & Impact", ln=True)
    pdf.set_font("Arial", "", 9.5)
    pdf.multi_cell(0, 5, (
        "The system coordinates in real-time with premier medical institutes across Delhi NCR: "
        "AIIMS Apex Trauma Centre, Safdarjung Emergency Block, Dr. RML Hospital, and Max Super Speciality Saket. "
        "By matching triage severity against free ICU beds, blood bank availability, and traffic-cleared corridors, "
        "the system eliminates secondary transfers and guarantees care within the critical Golden Hour window."
    ))
    
    output_filename = "RoadSoS_Project_Document.pdf"
    pdf.output(output_filename)
    print(f"PDF created successfully as {output_filename}")

if __name__ == '__main__':
    create_document()
