import streamlit as st
from datetime import date

# Initialize all session state variables
def init_session_state():
    defaults = {
        # Patient characteristics
        'age': 65,
        'sex': "Male",
        'diabetes': False,
        'smoker': False,
        'egfr': 90,
        'ldl': 3.5,
        'sbp': 140,
        'cad': False,
        'stroke': False,
        'pad': False,
        
        # Therapies
        'statin': "None",
        'ezetimibe': False,
        'pcsk9i': False,
        'bp_target': 130,
        'med_diet': False,
        'exercise': False,
        'smoking_cessation': False,
        
        # Calculated values
        'baseline_risk': None,
        'projected_risk': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# SMART-2 Risk Calculation
def calculate_smart2_risk():
    try:
        # Convert inputs safely
        age = float(st.session_state.age)
        ldl = float(st.session_state.ldl)
        sbp = float(st.session_state.sbp)
        egfr = float(st.session_state.egfr)
        vasc_count = sum([st.session_state.cad, st.session_state.stroke, st.session_state.pad])
        
        # SMART-2 Coefficients
        coefficients = {
            'intercept': -8.1937,
            'age': 0.0635 * (age - 60),
            'female': -0.3372 if st.session_state.sex == "Female" else 0,
            'diabetes': 0.5034 if st.session_state.diabetes else 0,
            'smoker': 0.7862 if st.session_state.smoker else 0,
            'egfr<30': 0.9235 if egfr < 30 else 0,
            'egfr30-60': 0.5539 if 30 <= egfr < 60 else 0,
            'polyvascular': 0.5434 if vasc_count >= 2 else 0,
            'ldl': 0.2436 * (ldl - 2.5),
            'sbp': 0.0083 * (sbp - 120)
        }
        
        # Calculate risk
        lp = sum(coefficients.values())
        risk_percent = 100 * (1 - 2.71828**(-2.71828**lp * 10))  # Using e≈2.71828
        return max(1.0, min(99.0, round(risk_percent, 1)))
    except:
        return None

# Treatment effects with realistic stacking
def calculate_treatment_effects():
    # Evidence-based relative risk reductions
    therapy_effects = {
        "statin": {
            "None": 0,
            "Moderate": 0.25,  # 25% RRR
            "High": 0.35       # 35% RRR
        },
        "ezetimibe": 0.06,     # 6% additional RRR
        "pcsk9i": 0.15,        # 15% additional RRR
        "bp_control": {
            "standard": 0.10,  # 10% RRR for SBP <140
            "intensive": 0.25  # 25% RRR for SBP <130
        },
        "lifestyle": {
            "med_diet": 0.15,  # 15% RRR
            "exercise": 0.10,  # 10% RRR
            "smoking_cessation": 0.30 if st.session_state.smoker else 0  # 30% RRR
        }
    }
    
    total_rrr = 0
    
    # Add statin effect
    total_rrr += therapy_effects["statin"][st.session_state.statin]
    
    # Add combination therapies
    if st.session_state.ezetimibe:
        total_rrr += therapy_effects["ezetimibe"]
    if st.session_state.pcsk9i and st.session_state.ldl >= 1.8:
        total_rrr += therapy_effects["pcsk9i"]
    
    # Add BP control effect
    bp_effect = "intensive" if st.session_state.bp_target < 130 else "standard"
    total_rrr += therapy_effects["bp_control"][bp_effect]
    
    # Add lifestyle effects
    if st.session_state.med_diet:
        total_rrr += therapy_effects["lifestyle"]["med_diet"]
    if st.session_state.exercise:
        total_rrr += therapy_effects["lifestyle"]["exercise"]
    if st.session_state.smoking_cessation:
        total_rrr += therapy_effects["lifestyle"]["smoking_cessation"]
    
    # Apply diminishing returns (1 - e^(-x*1.2))
    effective_rrr = 1 - 2.71828**(-1.2 * total_rrr)
    
    # Cap at 75% RRR (clinical maximum)
    final_rrr = min(0.75, effective_rrr)
    
    # Calculate projected risk
    if st.session_state.baseline_risk:
        projected_risk = st.session_state.baseline_risk * (1 - final_rrr)
        return {
            "rrr": final_rrr,
            "projected_risk": max(1.0, round(projected_risk, 1)),
            "arr": st.session_state.baseline_risk - projected_risk,
            "therapies": [
                f"{st.session_state.statin} statin" if st.session_state.statin != "None" else None,
                "Ezetimibe" if st.session_state.ezetimibe else None,
                "PCSK9i" if st.session_state.pcsk9i else None,
                f"BP<{st.session_state.bp_target}",
                "Mediterranean diet" if st.session_state.med_diet else None,
                "Exercise" if st.session_state.exercise else None,
                "Smoking cessation" if st.session_state.smoking_cessation else None
            ]
        }
    return None

def main():
    st.set_page_config(
        page_title="PRIME CVD Risk Calculator",
        layout="wide",
        page_icon="❤️"
    )
    
    # Initialize session state
    init_session_state()
    
    # Custom CSS
    st.markdown("""
    <style>
        .risk-high { border-left: 5px solid #d9534f; padding: 1rem; background-color: #fdf7f7; margin: 1rem 0; }
        .risk-medium { border-left: 5px solid #f0ad4e; padding: 1rem; background-color: #fffbf5; margin: 1rem 0; }
        .risk-low { border-left: 5px solid #5cb85c; padding: 1rem; background-color: #f8fdf8; margin: 1rem 0; }
        .therapy-card { border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .header-box { background-color: #f0f2f6; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; }
        .footer { font-size: 0.8rem; color: #666; margin-top: 2rem; border-top: 1px solid #eee; padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="header-box">
        <h1 style="margin:0;">PRIME SMART-2 CVD Risk Calculator</h1>
        <p style="margin:0;color:#666;">Evidence-based cardiovascular risk assessment and treatment optimization</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Patient Profile
    with st.sidebar:
        st.header("Patient Profile")
        
        # Demographics
        st.session_state.age = st.slider("Age (years)", 30, 90, st.session_state.age, key='age')
        st.session_state.sex = st.radio("Sex", ["Male", "Female"], index=0 if st.session_state.sex == "Male" else 1, key='sex')
        
        # Risk Factors
        st.session_state.diabetes = st.checkbox("Diabetes mellitus", st.session_state.diabetes, key='diabetes')
        st.session_state.smoker = st.checkbox("Current smoker", st.session_state.smoker, key='smoker')
        
        # Vascular Disease
        st.subheader("Vascular Disease")
        st.session_state.cad = st.checkbox("Coronary artery disease", st.session_state.cad, key='cad')
        st.session_state.stroke = st.checkbox("Prior stroke/TIA", st.session_state.stroke, key='stroke')
        st.session_state.pad = st.checkbox("Peripheral artery disease", st.session_state.pad, key='pad')
        
        # Biomarkers
        st.subheader("Biomarkers")
        st.session_state.egfr = st.slider("eGFR (mL/min/1.73m²)", 15, 120, st.session_state.egfr, key='egfr')
        st.session_state.ldl = st.number_input("LDL-C (mmol/L)", 1.0, 10.0, st.session_state.ldl, step=0.1, key='ldl')
        st.session_state.sbp = st.number_input("SBP (mmHg)", 90, 220, st.session_state.sbp, key='sbp')
    
    # Main Content
    tab1, tab2 = st.tabs(["Risk Assessment", "Treatment Optimization"])
    
    with tab1:
        # Calculate baseline risk
        st.session_state.baseline_risk = calculate_smart2_risk()
        
        if st.session_state.baseline_risk:
            st.subheader("Baseline Risk Estimation")
            
            # Display risk category
            if st.session_state.baseline_risk >= 30:
                st.markdown(f'<div class="risk-high"><h3>🔴 Very High Risk: {st.session_state.baseline_risk}%</h3></div>', unsafe_allow_html=True)
            elif st.session_state.baseline_risk >= 20:
                st.markdown(f'<div class="risk-medium"><h3>🟠 High Risk: {st.session_state.baseline_risk}%</h3></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="risk-low"><h3>🟢 Moderate Risk: {st.session_state.baseline_risk}%</h3></div>', unsafe_allow_html=True)
            
            # Risk factor summary
            with st.expander("Key Risk Factors"):
                factors = [
                    f"Age: {st.session_state.age}",
                    f"Sex: {st.session_state.sex}",
                    f"LDL-C: {st.session_state.ldl} mmol/L",
                    f"SBP: {st.session_state.sbp} mmHg",
                    f"eGFR: {st.session_state.egfr} mL/min"
                ]
                if st.session_state.diabetes:
                    factors.append("Diabetes: Yes")
                if st.session_state.smoker:
                    factors.append("Smoker: Yes")
                
                vasc_count = sum([st.session_state.cad, st.session_state.stroke, st.session_state.pad])
                if vasc_count > 0:
                    factors.append(f"Vascular Disease: {vasc_count} territories")
                
                st.markdown(" • ".join(factors))
        else:
            st.warning("Complete all patient information to calculate baseline risk")
    
    with tab2:
        st.header("Treatment Optimization")
        
        if st.session_state.baseline_risk:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="therapy-card"><h3>Pharmacotherapy</h3>', unsafe_allow_html=True)
                
                # Statin selection
                st.session_state.statin = st.selectbox(
                    "Statin Intensity",
                    ["None", "Moderate", "High"],
                    index=["None", "Moderate", "High"].index(st.session_state.statin),
                    key='statin_select'
                )
                
                # Combination therapies
                st.session_state.ezetimibe = st.checkbox(
                    "Add Ezetimibe",
                    st.session_state.ezetimibe,
                    key='ezetimibe_check'
                )
                
                if st.session_state.ldl >= 1.8:
                    st.session_state.pcsk9i = st.checkbox(
                        "Add PCSK9 Inhibitor (if LDL ≥1.8 mmol/L)",
                        st.session_state.pcsk9i,
                        key='pcsk9i_check'
                    )
                else:
                    st.info("PCSK9i requires LDL ≥1.8 mmol/L")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Blood pressure management
                st.markdown('<div class="therapy-card"><h3>Blood Pressure</h3>', unsafe_allow_html=True)
                st.session_state.bp_target = st.slider(
                    "Target SBP (mmHg)",
                    110, 150, st.session_state.bp_target,
                    key='bp_slider'
                )
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                # Lifestyle interventions
                st.markdown('<div class="therapy-card"><h3>Lifestyle</h3>', unsafe_allow_html=True)
                st.session_state.med_diet = st.checkbox(
                    "Mediterranean Diet",
                    st.session_state.med_diet,
                    key='med_diet_check'
                )
                st.session_state.exercise = st.checkbox(
                    "Regular Exercise (≥150 min/week)",
                    st.session_state.exercise,
                    key='exercise_check'
                )
                if st.session_state.smoker:
                    st.session_state.smoking_cessation = st.checkbox(
                        "Smoking Cessation Program",
                        st.session_state.smoking_cessation,
                        key='smoking_cessation_check'
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Calculate treatment effects
            treatment_results = calculate_treatment_effects()
            
            if treatment_results:
                st.subheader("Projected Outcomes")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Projected 10-Year Risk",
                        f"{treatment_results['projected_risk']}%",
                        delta=f"-{treatment_results['arr']:.1f}% ARR",
                        delta_color="inverse"
                    )
                
                with col2:
                    st.metric(
                        "Relative Risk Reduction",
                        f"{treatment_results['rrr']*100:.0f}%",
                        help="Includes diminishing returns from combination therapies"
                    )
                
                # Display selected therapies
                with st.expander("Selected Therapies"):
                    active_therapies = [t for t in treatment_results["therapies"] if t]
                    if active_therapies:
                        for therapy in active_therapies:
                            st.success(f"✓ {therapy}")
                    else:
                        st.info("No therapies selected")
                
                # Clinical recommendations
                st.subheader("Clinical Guidance")
                if treatment_results["projected_risk"] >= 30:
                    st.markdown("""
                    <div class="risk-high">
                    <h4>🔴 Very High Risk Management</h4>
                    <ul>
                        <li>High-intensity statin (atorvastatin 40-80mg or rosuvastatin 20-40mg)</li>
                        <li>Consider PCSK9 inhibitor if LDL ≥1.8 mmol/L after statin</li>
                        <li>Target SBP <130 mmHg if tolerated</li>
                        <li>Multidisciplinary risk factor management</li>
                        <li>Consider low-dose colchicine for inflammation</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                elif treatment_results["projected_risk"] >= 20:
                    st.markdown("""
                    <div class="risk-medium">
                    <h4>🟠 High Risk Management</h4>
                    <ul>
                        <li>Moderate-high intensity statin</li>
                        <li>Target SBP <130 mmHg</li>
                        <li>Address all modifiable risk factors</li>
                        <li>Consider ezetimibe if LDL >1.8 mmol/L</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="risk-low">
                    <h4>🟢 Moderate Risk Management</h4>
                    <ul>
                        <li>Maintain adherence to current therapies</li>
                        <li>Focus on lifestyle interventions</li>
                        <li>Annual risk reassessment</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Complete the Risk Assessment tab first")
    
    # Footer
    st.markdown(f"""
    <div class="footer">
        PRIME Cardiology • King's College Hospital • {date.today().strftime('%Y-%m-%d')} • v2.1
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
