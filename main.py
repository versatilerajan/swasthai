import streamlit as st
import requests
import json
from PIL import Image
import io
import os
API_URL = "https://swasthai-5did.onrender.com/analyze"
API_HEALTH_URL = "https://swasthai-5did.onrender.com/health"

st.set_page_config(
    page_title="SwasthAI - Health Report Analyzer",
    page_icon="🩺",
    layout="wide"
)
with st.sidebar:
    st.title("🩺 SwasthAI")
    st.markdown("Upload your health report (PDF or image)")
    
    st.info("""
    Supported formats:
    • PDF
    • PNG / JPG / JPEG
    • (Text extraction + AI analysis)
    """)
    
    st.markdown("---")
    st.caption("Backend powered by your Render service")

# =============================================
# MAIN PAGE
# =============================================
st.title("Health Report Analyzer")
st.markdown("Upload your lab report / blood test PDF or photo → get AI-powered insights, health score & recommendations")

# Check if backend is alive
@st.cache_data(ttl=60)
def check_backend_health():
    try:
        r = requests.get(API_HEALTH_URL, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data.get("status") == "healthy", data.get("models_loaded", False)
        return False, False
    except:
        return False, False

healthy, models_loaded = check_backend_health()

if not healthy:
    st.error("⚠️ Backend service is not responding right now. Please try again in a few minutes.")
    st.stop()

if not models_loaded:
    st.warning("Backend models are loading or not ready yet. Analysis may be limited.")

# File uploader
uploaded_file = st.file_uploader(
    "Upload your health report",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Max size ~50MB (same as backend limit)"
)

if uploaded_file is not None:
    file_name = uploaded_file.name.lower()
    file_ext = os.path.splitext(file_name)[1]
    
    st.subheader("Uploaded file")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if file_ext in [".png", ".jpg", ".jpeg"]:
            try:
                img = Image.open(uploaded_file)
                st.image(img, caption="Preview", use_column_width=True)
            except:
                st.warning("Could not preview image")
        else:
            st.info("PDF uploaded – preview not available")
    
    with col2:
        st.write(f"**File:** {uploaded_file.name}")
        st.write(f"**Size:** {uploaded_file.size / 1024 / 1024:.2f} MB")
    
    analyze_btn = st.button("Analyze Report →", type="primary", use_container_width=True)
    
    if analyze_btn:
        with st.spinner("Sending file to AI backend... (may take 10–40 seconds)"):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/octet-stream")}
                response = requests.post(API_URL, files=files, timeout=90)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    st.success("Analysis complete!")
                    
                    # ────────────────────────────────────────
                    # HEALTH SUMMARY
                    # ────────────────────────────────────────
                    st.markdown("### Health Summary")
                    health = result.get("health_summary", {})
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Health Score", f"{health.get('health_score', '—')}%")
                    col_b.metric("Risk Level", health.get("risk_level", "—"))
                    col_c.metric("Status", health.get("status", "—"), delta_color="normal")
                    
                    # Risk probabilities
                    with st.expander("Risk probabilities"):
                        probs = health.get("risk_probabilities", {})
                        for k, v in probs.items():
                            st.progress(v / 100)
                            st.caption(f"{k}: {v}%")
                    
                    # ────────────────────────────────────────
                    # EXTRACTED VALUES
                    # ────────────────────────────────────────
                    st.markdown("### Extracted Test Values")
                    extracted = result.get("extracted_values", {})
                    if extracted:
                        df_extracted = pd.DataFrame(list(extracted.items()), columns=["Test", "Value"])
                        st.dataframe(df_extracted.style.format({"Value": "{:.2f}"}), hide_index=True)
                    else:
                        st.info("No numeric values could be extracted automatically.")
                    
                    # ────────────────────────────────────────
                    # ABNORMAL TESTS & WARNINGS
                    # ────────────────────────────────────────
                    detailed = result.get("detailed_analysis", {})
                    
                    if detailed.get("abnormal_tests_count", 0) > 0:
                        st.markdown("### Abnormal Findings")
                        abnormals = detailed.get("abnormal_tests", [])
                        for item in abnormals:
                            color = "red" if item["status"] == "High" else "orange"
                            st.markdown(f"**{item['test']}**: {item['value']} ({item['normal_range']}) → **{item['status']}**")
                    
                    if detailed.get("warnings_count", 0) > 0:
                        st.markdown("### Important Warnings")
                        for w in detailed.get("warnings", []):
                            st.warning(f"{w['category']}: {w['message']} ({w['urgency']})")
                    
                    # ────────────────────────────────────────
                    # RECOMMENDATIONS
                    # ────────────────────────────────────────
                    st.markdown("### Recommendations & Next Steps")
                    for rec in result.get("recommendations", []):
                        st.info(f"**{rec['priority']} priority**: {rec['action']}\n\n{rec.get('details', '')}")
                    
                    for step in result.get("next_steps", {}).values():
                        st.caption(step)
                    
                    # Raw JSON (for debugging)
                    with st.expander("Full JSON response (debug)"):
                        st.json(result)
                
                elif response.status_code == 400:
                    err = response.json()
                    st.error(f"Backend error: {err.get('message', 'Bad request')}")
                else:
                    st.error(f"Backend returned status {response.status_code}")
                    st.code(response.text[:1000])
            
            except requests.exceptions.Timeout:
                st.error("Request timed out. The analysis might be taking too long or the server is slow.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend service. Is it running?")
            except Exception as e:
                st.exception(e)

else:
    st.info("Please upload a PDF or image of your health report to begin.")
