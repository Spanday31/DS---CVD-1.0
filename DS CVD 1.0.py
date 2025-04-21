import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
from fpdf import FPDF
import base64
import json
from io import BytesIO
from PIL import Image
import os

# ======================
# CONSTANTS & EVIDENCE BASE
# ======================

INTERVENTIONS = [
    {
        "name": "Smoking cessation",
        "arr_5yr": 5,
        "arr_lifetime": 17,
        "mechanism": "Reduces endothelial dysfunction and thrombotic risk",
        "source": "Haberstick BMJ 2018 (PMID: 29367388)"
    },
    {
        "name": "Mediterranean diet",
        "arr_5yr": 3,
        "arr_lifetime": 10,
        "mechanism": "Improves lipid profile and reduces inflammation",
        "source": "PREDIMED NEJM 2018 (PMID: 29897866)"
    }
]

LDL_THERAPIES = {
    "Atorvastatin 20 mg": {"reduction": 40, "source": "STELLAR JAMA 2003 (PMID: 14699082)"},
    "Atorvastatin 80 mg": {"reduction": 50, "source": "TNT NEJM 2005 (PMID: 15930428)"},
    "Rosuvastatin 10 mg": {"reduction": 45, "source": "JUPITER NEJM 2008 (PMID: 18997196)"},
    "Rosuvastatin 20 mg": {"reduction": 55, "source": "SATURN NEJM 2011 (PMID: 22010916)"}
}

EVIDENCE_DB = {
    "ldl": {
        "effect": "22% RRR per 1 mmol/L LDL reduction",
        "source": "CTT Collaboration, Lancet 2010",
        "pmid": "21067804"
    },
    "bp": {
        "effect": "10% RRR per 10 mmHg reduction",
        "source": "SPRINT NEJM 2015",
        "pmid": "26551272"
    }
}

# ======================
# CORE CALCULATIONS
# ======================

@st.cache_data
def calculate_smart_risk(age, sex, sbp, total_chol, hdl, smoker, diabetes, egfr, crp, vasc_count):
    """Enhanced SMART Risk Score with input validation"""
    try:
        sex_val = 1 if sex == "Male" else 0
        smoking_val = 1 if smoker else 0
        diabetes_val = 1 if diabetes else 0
        crp_log = math.log(crp + 1)
        
        lp = (0.064*age + 0.34*sex_val + 0.02*sbp + 0.25*total_chol -
              0.25*hdl + 0.44*smoking_val + 0.51*diabetes_val -
              0.2*(egfr/10) + 0.25*crp_log + 0.4*vasc_count)
        
        risk10 = 1 - 0.900**math.exp(lp - 5.8)
        return max(1.0, min(99.0, round(risk10 * 100, 1)))
    except Exception as e:
        st.error(f"Error calculating risk: {str(e)}")
        return None

def calculate_ldl_effect(baseline_risk, baseline_ldl, final_ldl):
    """Based on CTT Collaboration meta-analysis"""
    try:
        ldl_reduction = baseline_ldl - final_ldl
        rrr = min(22 * ldl_reduction, 60)  # Cap at 60% RRR
        return baseline_risk * (1 - rrr/100)
    except Exception as e:
        st.error(f"Error calculating LDL effect: {str(e)}")
        return baseline_risk

def validate_drug_classes(selected_therapies):
    """Ensure only one drug per class is selected"""
    drug_classes = {
        'statins': ['atorvastatin', 'rosuvastatin'],
        'pcsk9': ['pcsk9', 'evlocumab', 'alirocumab'],
        'ezetimibe': ['ezetimibe'],
        'inclisiran': ['inclisiran']
    }
    
    conflicts = []
    for class_name, drugs in drug_classes.items():
        class_drugs = [d for d in selected_therapies if any(drug in d.lower() for drug in drugs)]
        if len(class_drugs) > 1:
            conflicts.append(f"Multiple {class_name}: {', '.join(class_drugs)}")
    
    return conflicts

def calculate_ldl_reduction(current_ldl, pre_statin, discharge_statin, discharge_add_ons):
    """Calculate LDL reduction accounting for prior statin use"""
    statin_reduction = LDL_THERAPIES.get(discharge_statin, {}).get("reduction", 0)
    
    # Adjustment for prior statin use (diminished additional effect)
    if pre_statin != "None":
        statin_reduction *= 0.5  # 50% reduced effect if already on statin
    
    total_reduction = statin_reduction
    
    # Add-on therapies (full effect)
    if "Ezetimibe" in discharge_add_ons:
        total_reduction += 20
    if "PCSK9 inhibitor" in discharge_add_ons:
        total_reduction += 60
    if "Inclisiran" in discharge_add_ons:
        total_reduction += 50
    
    projected_ldl = current_ldl * (1 - total_reduction/100)
    return projected_ldl, total_reduction

def generate_recommendations(final_risk):
    """Generate evidence-based recommendations"""
    if final_risk >= 30:
        return """
        🔴 Very High Risk Management:
        - High-intensity statin (atorvastatin 80mg or rosuvastatin 20-40mg)
        - Consider PCSK9 inhibitor if LDL ≥1.8 mmol/L after statin
        - Target SBP <130 mmHg if tolerated
        - Comprehensive lifestyle modification
        - Consider colchicine 0.5mg daily for inflammation
        """
    elif final_risk >= 20:
        return """
        🟠 High Risk Management:
        - At least moderate-intensity statin
        - Target SBP <130 mmHg
        - Address all modifiable risk factors
        - Consider ezetimibe if LDL >1.8 mmol/L
        """
    else:
        return """
        🟢 Moderate Risk Management:
        - Maintain current therapies
        - Focus on lifestyle adherence
        - Annual risk reassessment
        """

# ======================
# PDF REPORT GENERATION
# ======================

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'PRIME CVD Risk Assessment Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf_report(patient_data, risk_data, ldl_history):
    pdf = PDFReport()
    pdf.add_page()
    
    # Header
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'PRIME CVD Risk Assessment', 0, 1, 'C')
    pdf.ln(10)
    
    # Patient Information
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Patient Information', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Name: {patient_data.get('name', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Age: {patient_data.get('age', 'N/A')} | Sex: {patient_data.get('sex', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Assessment Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    # Risk Assessment
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Risk Assessment Summary', 0, 1)
    pdf.set_font('Arial', '', 12)
    
    col_widths = [60, 60, 60]
    pdf.cell(col_widths[0], 10, "Metric", border=1)
    pdf.cell(col_widths[1], 10, "Value", border=1)
    pdf.cell(col_widths[2], 10, "Target", border=1)
    pdf.ln()
    
    risk_data_rows = [
        ("Baseline Risk", f"{risk_data['baseline_risk']}%", "-"),
        ("Post-Treatment Risk", f"{risk_data['final_risk']}%", "-"),
        ("LDL-C", f"{risk_data['current_ldl']} mmol/L", f"< {risk_data['ldl_target']} mmol/L")
    ]
    
    for row in risk_data_rows:
        pdf.cell(col_widths[0], 10, row[0], border=1)
        pdf.cell(col_widths[1], 10, row[1], border=1)
        pdf.cell(col_widths[2], 10, row[2], border=1)
        pdf.ln()
    
    # LDL Trend Plot
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'LDL-C Trend', 0, 1)
    
    buf = BytesIO()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(ldl_history['dates'], ldl_history['values'], 
            marker='o', color='#4e8cff', linewidth=2)
    ax.set_title('LDL-C Reduction Over Time', pad=10)
    ax.set_ylabel('LDL-C (mmol/L)')
    ax.grid(True, linestyle='--', alpha=0.3)
    fig.tight_layout()
    fig.savefig(buf, format='png', dpi=120)
    plt.close()
    
    pdf.image(buf, x=10, w=190)
    
    # Recommendations
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Clinical Recommendations', 0, 1)
    pdf.set_font('Arial', '', 12)
    
    recommendations = risk_data['recommendations'].split('\n')
    for rec in recommendations:
        if rec.strip().startswith("🔴"):
            pdf.set_text_color(220, 50, 50)  # Red
        elif rec.strip().startswith("🟠"):
            pdf.set_text_color(210, 140, 0)  # Orange
        elif rec.strip().startswith("🟢"):
            pdf.set_text_color(50, 150, 50)  # Green
        
        pdf.multi_cell(0, 8, rec.strip())
        pdf.set_text_color(0, 0, 0)  # Reset to black
    
    return pdf.output(dest='S').encode('latin1')

# ======================
# STREAMLIT APP
# ======================

def main():
    st.set_page_config(
        page_title="PRIME CVD Risk Calculator",
        layout="wide",
        page_icon="❤️",
        initial_sidebar_state="expanded"
    )
    
    # ============ CUSTOM CSS ============
    st.markdown("""
    <style>
        /* Modern professional styling */
        .main { background-color: #f8fafc; }
        .sidebar .sidebar-content { 
            background: white; 
            box-shadow: 1px 0 5px rgba(0,0,0,0.1);
        }
        
        /* Section headers */
        .section-header {
            background-color: #3b82f6;
            padding: 0.5rem;
            border-radius: 5px;
            color: white;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .risk-factors-header {
            background-color: #10b981;
        }
        .vascular-header {
            background-color: #8b5cf6;
        }
        .biomarkers-header {
            background-color: #f59e0b;
        }
        .time-header {
            background-color: #64748b;
        }
        
        /* Cards */
        .card {
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background: white;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        
        /* Risk boxes */
        .risk-high { 
            border-left: 5px solid #ef4444; 
            background-color: #fef2f2; 
        }
        .risk-medium { 
            border-left: 5px solid #f59e0b; 
            background-color: #fffbeb; 
        }
        .risk-low { 
            border-left: 5px solid #10b981; 
            background-color: #ecfdf5; 
        }
        
        /* Logo styling */
        .logo-container {
            text-align: center;
            margin-bottom: 1rem;
        }
        .logo-img {
            max-width: 80%;
            margin: 0 auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ============ SESSION STATE ============
    if 'patient_mode' not in st.session_state:
        st.session_state.patient_mode = False
    if 'calculated' not in st.session_state:
        st.session_state.calculated = False
    if 'final_risk' not in st.session_state:
        st.session_state.final_risk = None
    if 'ldl_results' not in st.session_state:
        st.session_state.ldl_results = None
    
    # ============ HEADER ============
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("""
        <div class='card' style='background:linear-gradient(135deg,#3b82f6,#2563eb);color:white;'>
            <h1 style='color:white;margin:0;'>PRIME CVD Risk Calculator</h1>
            <p style='color:#e0f2fe;margin:0;'>Secondary Prevention After Myocardial Infarction</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try:
            logo = Image.open("logo.png")
            st.image(logo, width=100)
        except:
            st.warning("Logo image not found")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ============ SIDEBAR ============
    with st.sidebar:
        # Logo at the top
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try:
            logo = Image.open("logo.png")
            st.image(logo, use_column_width=True)
        except:
            st.warning("Logo not found (expected 'logo.png')")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # PATIENT DEMOGRAPHICS
        st.markdown("""
        <div class="section-header">
            <h3 style="color:white;margin:0;">Patient Demographics</h3>
        </div>
        """, unsafe_allow_html=True)
        
        age = st.number_input("Age (years)", min_value=30, max_value=100, value=65)
        sex = st.radio("Sex", ["Male", "Female"], horizontal=True)
        
        st.markdown("---")
        
        # RISK FACTORS
        st.markdown("""
        <div class="section-header risk-factors-header">
            <h3 style="color:white;margin:0;">Risk Factors</h3>
        </div>
        """, unsafe_allow_html=True)
        
        diabetes = st.checkbox("Diabetes mellitus")
        smoker = st.checkbox("Current smoker")
        
        st.markdown("---")
        
        # VASCULAR DISEASE
        st.markdown("""
        <div class="section-header vascular-header">
            <h3 style="color:white;margin:0;">Vascular Disease Territories</h3>
        </div>
        """, unsafe_allow_html=True)
        
        cad = st.checkbox("Coronary artery disease (CAD)")
        stroke = st.checkbox("Cerebrovascular disease (Stroke/TIA)")
        pad = st.checkbox("Peripheral artery disease (PAD)")
        vasc_count = sum([cad, stroke, pad])
        
        st.markdown("---")
        
        # BIOMARKERS
        st.markdown("""
        <div class="section-header biomarkers-header">
            <h3 style="color:white;margin:0;">Biomarkers</h3>
        </div>
        """, unsafe_allow_html=True)
        
        total_chol = st.number_input("Total Cholesterol (mmol/L)", 
                                   min_value=2.0, max_value=10.0, value=5.0, step=0.1)
        hdl = st.number_input("HDL-C (mmol/L)", 
                             min_value=0.5, max_value=3.0, value=1.0, step=0.1)
        ldl = st.number_input("LDL-C (mmol/L)", 
                             min_value=0.5, max_value=6.0, value=3.5, step=0.1)
        sbp = st.number_input("SBP (mmHg)", 
                             min_value=90, max_value=220, value=140)
        
        if diabetes:
            hba1c = st.number_input("HbA1c (%)", 
                                   min_value=5.0, max_value=12.0, value=7.0, step=0.1)
        
        egfr = st.slider("eGFR (mL/min/1.73m²)", 
                         min_value=15, max_value=120, value=80)
        crp = st.number_input("hs-CRP (mg/L) - baseline level", 
                             min_value=0.1, max_value=20.0, value=2.0, step=0.1,
                             help="Use baseline value (not during acute illness)")
        
        st.markdown("---")
        
        # TIME HORIZON
        st.markdown("""
        <div class="section-header time-header">
            <h3 style="color:white;margin:0;">Time Horizon</h3>
        </div>
        """, unsafe_allow_html=True)
        
        horizon = st.radio("Select time frame", ["5yr", "10yr", "lifetime"], 
                          index=1, label_visibility="collapsed")
        
        st.markdown("---")
        
        # VIEW MODE
        st.session_state.patient_mode = st.checkbox("Patient-Friendly View", 
                                                  help="Simplified interface for patient education")
        
        st.markdown("---")
        
        # SAVE/LOAD
        with st.expander("💾 Save/Load Case"):
            case_name = st.text_input("Case Name", placeholder="Patient ID or name")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Current Case"):
                    case_data = {
                        'demographics': {'age': age, 'sex': sex},
                        'risk_factors': {
                            'diabetes': diabetes, 
                            'smoker': smoker,
                            'vasc_count': vasc_count
                        },
                        'biomarkers': {
                            'ldl': ldl, 
                            'sbp': sbp,
                            'hdl': hdl,
                            'total_chol': total_chol,
                            'crp': crp
                        },
                        'timestamp': str(datetime.now())
                    }
                    with open(f"{case_name}.json", "w") as f:
                        json.dump(case_data, f)
                    st.success("Case saved successfully!")
            with col2:
                uploaded_file = st.file_uploader("📂 Load Case", type="json")
                if uploaded_file:
                    try:
                        case_data = json.load(uploaded_file)
                        st.session_state.age = case_data['demographics']['age']
                        st.session_state.sex = case_data['demographics']['sex']
                        st.session_state.diabetes = case_data['risk_factors']['diabetes']
                        st.session_state.smoker = case_data['risk_factors']['smoker']
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading case: {str(e)}")
    
    # ============ MAIN CONTENT ============
    tab1, tab2 = st.tabs(["📊 Risk Assessment", "💊 Treatment Optimization"])
    
    with tab1:
        # Calculate baseline risk
        baseline_risk = calculate_smart_risk(
            age, sex, sbp, total_chol, hdl, smoker, diabetes, egfr, crp, vasc_count
        )
        
        if baseline_risk is not None:
            # Apply time horizon
            if horizon == "5yr":
                baseline_risk = baseline_risk * 0.6
            elif horizon == "lifetime":
                baseline_risk = min(baseline_risk * 1.8, 90)
            
            baseline_risk = round(baseline_risk, 1)
            
            # Display risk
            risk_category = "high" if baseline_risk >= 20 else "medium" if baseline_risk >= 10 else "low"
            st.markdown(f"""
            <div class='card risk-{risk_category}'>
                <h3>Baseline {horizon} Risk: {baseline_risk}%</h3>
                <p>Estimated probability of recurrent cardiovascular events</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Risk factors
            with st.expander("🔍 Key Risk Factors"):
                factors = [
                    f"Age: {age}",
                    f"Sex: {sex}",
                    f"LDL-C: {ldl} mmol/L",
                    f"SBP: {sbp} mmHg",
                    f"HDL-C: {hdl} mmol/L"
                ]
                if diabetes:
                    factors.append(f"Diabetes (HbA1c: {hba1c if 'hba1c' in locals() else 'N/A'}%)")
                if smoker:
                    factors.append("Current smoker")
                if vasc_count > 0:
                    factors.append(f"Vascular disease ({vasc_count} territories)")
                
                st.markdown(" • ".join(factors))
        else:
            st.warning("Please complete all patient information")
    
    with tab2:
        st.header("Optimize Treatment Plan", divider='blue')
        
        if baseline_risk is None:
            st.warning("Complete Risk Assessment first")
            st.stop()
        
        # Current Therapy
        with st.expander("📋 Current Lipid Therapy", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                current_statin = st.selectbox(
                    "Current Statin",
                    ["None"] + list(LDL_THERAPIES.keys()),
                    index=0,
                    help="Patient's pre-admission statin regimen"
                )
            with col2:
                current_add_ons = st.multiselect(
                    "Current Add-ons",
                    ["Ezetimibe", "PCSK9 inhibitor", "Bempedoic acid"],
                    help="Other lipid-lowering medications"
                )
        
        # Recommended Therapy
        with st.expander("💊 Recommended Discharge Therapy", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                discharge_statin = st.selectbox(
                    "Recommended Statin",
                    ["None"] + list(LDL_THERAPIES.keys()),
                    index=2,  # Default to moderate intensity
                    help="High-intensity statin recommended for secondary prevention"
                )
            with col2:
                discharge_add_ons = st.multiselect(
                    "Recommended Add-ons",
                    ["Ezetimibe", "PCSK9 inhibitor", "Inclisiran", "Bempedoic acid"],
                    help="Consider if LDL >1.4 mmol/L on maximally tolerated statin"
                )
            
            target_ldl = st.slider("LDL-C Target (mmol/L)", 
                                  min_value=0.5, max_value=3.0, value=1.4, step=0.1,
                                  help="ESC 2021 Guidelines recommend <1.4 mmol/L for very high risk")
            
            # Validate drug classes
            conflicts = validate_drug_classes([discharge_statin] + discharge_add_ons)
            if conflicts:
                for conflict in conflicts:
                    st.error(conflict)
            
            if st.button("Calculate Treatment Impact", type="primary"):
                try:
                    # Calculate LDL effect
                    projected_ldl, total_reduction = calculate_ldl_reduction(
                        ldl, current_statin, discharge_statin, discharge_add_ons
                    )
                    
                    # Calculate risk reduction
                    ldl_effect = calculate_ldl_effect(baseline_risk, ldl, projected_ldl)
                    
                    # Get active interventions
                    active_interventions = []
                    if "Ezetimibe" in discharge_add_ons:
                        active_interventions.append({"arr_5yr": 2, "arr_lifetime": 6})
                    if "PCSK9 inhibitor" in discharge_add_ons:
                        active_interventions.append({"arr_5yr": 3, "arr_lifetime": 8})
                    
                    # Combined effect
                    total_arr = sum(iv["arr_5yr"] for iv in active_interventions)
                    final_risk = max(1, baseline_risk - total_arr)
                    
                    st.session_state.final_risk = final_risk
                    st.session_state.calculated = True
                    st.session_state.ldl_results = {
                        'current': ldl,
                        'projected': projected_ldl,
                        'reduction': total_reduction,
                        'target': target_ldl
                    }
                    st.session_state.recommendations = generate_recommendations(final_risk)
                    st.rerun()
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
        
        # Results Display
        if st.session_state.get('calculated'):
            final_risk = st.session_state.final_risk
            ldl_results = st.session_state.ldl_results
            
            # Risk reduction card
            risk_category = "high" if final_risk >= 20 else "medium" if final_risk >= 10 else "low"
            st.markdown(f"""
            <div class='card risk-{risk_category}'>
                <h3>Post-Intervention {horizon} Risk: {final_risk:.1f}%</h3>
                <p>Absolute reduction: {baseline_risk-final_risk:.1f} percentage points</p>
            </div>
            """, unsafe_allow_html=True)
            
            # LDL results
            with st.expander("📈 Lipid Therapy Impact"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current LDL-C", f"{ldl_results['current']:.1f} mmol/L")
                with col2:
                    st.metric("Projected LDL-C", f"{ldl_results['projected']:.1f} mmol/L",
                             delta=f"{ldl_results['reduction']:.0f}% reduction")
                with col3:
                    st.metric("Target LDL-C", f"{ldl_results['target']:.1f} mmol/L")
                
                # LDL trend visualization
                st.markdown("**LDL-C Projection**")
                fig, ax = plt.subplots()
                ax.bar(["Current", "Projected"], 
                      [ldl_results['current'], ldl_results['projected']],
                      color=["#3b82f6", "#10b981"])
                ax.axhline(y=ldl_results['target'], color='#ef4444', linestyle='--', label='Target')
                ax.set_ylabel("LDL-C (mmol/L)")
                ax.legend()
                st.pyplot(fig)
            
            # Clinical recommendations
            st.markdown("## 📋 Clinical Recommendations")
            if final_risk >= 30:
                st.error(st.session_state.recommendations)
            elif final_risk >= 20:
                st.warning(st.session_state.recommendations)
            else:
                st.success(st.session_state.recommendations)
            
            # PDF Report Generation
            st.markdown("---")
            st.markdown("## 📄 Generate Report")
            
            patient_name = st.text_input("Patient Name for Report", placeholder="Enter patient name")
            
            if st.button("Generate PDF Report", type="primary"):
                if not patient_name:
                    st.warning("Please enter a patient name")
                else:
                    with st.spinner("Generating report..."):
                        # Create sample LDL history (replace with real data)
                        ldl_history = {
                            'dates': [
                                (datetime.now() - pd.Timedelta(days=90)).strftime('%Y-%m-%d'),
                                (datetime.now() - pd.Timedelta(days=60)).strftime('%Y-%m-%d'),
                                (datetime.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                                datetime.now().strftime('%Y-%m-%d')
                            ],
                            'values': [
                                ldl_results['current'] * 1.2,
                                ldl_results['current'] * 1.1,
                                ldl_results['current'],
                                ldl_results['projected']
                            ]
                        }
                        
                        pdf_bytes = create_pdf_report(
                            patient_data={
                                'name': patient_name,
                                'age': age,
                                'sex': sex
                            },
                            risk_data={
                                'baseline_risk': baseline_risk,
                                'final_risk': final_risk,
                                'current_ldl': ldl_results['current'],
                                'ldl_target': ldl_results['target'],
                                'recommendations': st.session_state.recommendations
                            },
                            ldl_history=ldl_history
                        )
                        
                        st.download_button(
                            label="⬇️ Download Full Report",
                            data=pdf_bytes,
                            file_name=f"PRIME_CVD_Report_{patient_name.replace(' ', '_')}_{datetime.now().date()}.pdf",
                            mime="application/pdf"
                        )

# Run the app
if __name__ == "__main__":
    main()
