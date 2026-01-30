import streamlit as st
import pdfplumber
from fpdf import FPDF
import json, os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="ClauseWise", layout="wide")

AUDIT_FILE = "audit_log.json"
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"
SAMPLE_DIR = "samples"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ================= CSS =================

st.markdown("""
<style>
.main{background:#040b17;color:white;}
.card{background:linear-gradient(135deg,#0d1b2e,#081120);padding:14px;border-radius:16px;border:1px solid #1f2d45;margin-bottom:8px;}
.badge{padding:4px 12px;border-radius:20px;}
.high{background:#ff4b4b;}
.medium{background:#ffb703;}
.low{background:#2ecc71;}
</style>
""", unsafe_allow_html=True)

# ================= HELPERS =================

def load_history():
    if os.path.exists(AUDIT_FILE):
        return json.load(open(AUDIT_FILE))
    return []

def save_history(d):
    json.dump(d, open(AUDIT_FILE,"w"), indent=2)

history = load_history()

# ================= HEADER =================

st.markdown("""
<center style="margin-top:-40px">
<h1 style="color:#5ea3ff">ClauseWise</h1>
<h4 style="color:#9db4d4">AI Contract Intelligence Platform</h4>
<p style="max-width:600px;color:#b4c3dc">
Analyze contracts, detect risks, and generate actionable insights instantly.
</p>
</center>
""", unsafe_allow_html=True)

# ================= TABS =================

tab1, tab2, tab3 = st.tabs(["Analyze Contract", "Dashboard", "History"])

# ======================================================
# ================= ANALYZE TAB ========================
# ======================================================

with tab1:

    sample_files = {
        "Employment": f"{SAMPLE_DIR}/sample_employment.txt",
        "Service": f"{SAMPLE_DIR}/sample_service.txt",
        "Vendor": f"{SAMPLE_DIR}/sample_vendor.txt",
        "Low Risk": f"{SAMPLE_DIR}/sample_low_risk.txt"
    }

    text=""
    upload_path=""

    choice = st.selectbox("Try sample contract", ["None"]+list(sample_files.keys()))

    if choice!="None" and os.path.exists(sample_files[choice]):
        text=open(sample_files[choice]).read()

    uploaded = st.file_uploader("Upload Contract (PDF/TXT)", type=["pdf","txt"])

    if uploaded:
        upload_path=os.path.join(UPLOAD_DIR,uploaded.name)
        open(upload_path,"wb").write(uploaded.getbuffer())

        if uploaded.name.endswith(".pdf"):
            with pdfplumber.open(uploaded) as pdf:
                text="\n".join(p.extract_text() or "" for p in pdf.pages)
        else:
            text=uploaded.read().decode()

    if text:
        st.text_area("Contract Preview",text,height=180)

    if st.button("Analyze") and text:

        keywords={
            "penalty":("Financial","Penalty"),
            "liability":("Legal","Liability"),
            "terminate":("Operational","Termination"),
            "indemnity":("Legal","Indemnity"),
            "jurisdiction":("Legal","Jurisdiction"),
            "arbitration":("Legal","Arbitration"),
            "non-compete":("Operational","Non-compete")
        }

        risks=[]
        categories={}

        for k,(c,l) in keywords.items():
            if k in text.lower():
                risks.append(l)
                categories.setdefault(c,[]).append(l)

        score=min(len(risks)*20,100)
        level="High" if score>=60 else "Medium" if score>=30 else "Low"

        badge="high" if level=="High" else "medium" if level=="Medium" else "low"

        # Highlight
        highlighted=text
        for k in keywords:
            highlighted=highlighted.replace(k,f"**{k.upper()}**")

        st.markdown("### Highlighted Clauses")
        st.markdown(highlighted)

        st.markdown(f"""
<div class="card">
Risk Score: <b>{score}/100</b><br>
Risk Level: <span class="badge {badge}">{level}</span><br>
Detected Clauses: {len(risks)}
</div>
""",unsafe_allow_html=True)

        st.progress(score/100)

        st.markdown("### Category Risks")
        for c,v in categories.items():
            st.write(c,":",", ".join(v))

        st.markdown("### Recommendations")
        st.write("• Cap liabilities\n• Reduce penalties\n• Review jurisdiction\n• Mutual termination")

        # PDF
        pdf_path=f"{REPORT_DIR}/{datetime.now().timestamp()}.pdf"
        pdf=FPDF();pdf.add_page();pdf.set_font("Arial",size=11)
        pdf.multi_cell(0,8,f"Risk Score:{score}\nLevel:{level}\nRisks:{risks}")
        pdf.output(pdf_path)

        history.append({
            "filename": uploaded.name if uploaded else choice,
            "risk":level,
            "score":score,
            "time":datetime.now().strftime("%d %b %Y %H:%M"),
            "report":pdf_path,
            "upload":upload_path
        })

        save_history(history)

        with open(pdf_path,"rb") as f:
            st.download_button("Download Report",f,file_name="ClauseWise_Report.pdf")

# ======================================================
# ================= DASHBOARD TAB ======================
# ======================================================

with tab2:

    if history:
        df=pd.DataFrame(history)

        st.metric("Total Contracts",len(df))
        st.metric("Avg Risk Score",round(df["score"].mean(),1))

        st.markdown("### Risk Trend")

        fig,ax=plt.subplots()
        scores=df["score"].astype(int).tolist()

        if len(scores)>1:
            ax.plot(range(len(scores)),scores,marker="o")
        else:
            ax.bar(["Current"],scores)

        ax.set_ylim(0,100)
        ax.set_ylabel("Risk Score")

        st.pyplot(fig)

        st.markdown("### Risk Distribution")
        st.bar_chart(df["risk"].value_counts().to_frame())

    else:
        st.info("No data yet.")

# ======================================================
# ================= HISTORY TAB ========================
# ======================================================

with tab3:

    if history:
        search=st.text_input("Search filename")
        filtered=[h for h in history if search.lower() in h["filename"].lower()]

        df=pd.DataFrame(filtered)
        st.dataframe(df[["filename","risk","score","time"]])

        st.download_button("Export CSV",df.to_csv(index=False),"history.csv")

        for i,h in enumerate(reversed(filtered)):
            st.markdown(f"**{h['filename']}** — {h['risk']} ({h['score']})")

            if os.path.exists(h["report"]):
                st.download_button("Report",open(h["report"],"rb"),key=f"r{i}")

            if h["upload"] and os.path.exists(h["upload"]):
                st.download_button("Contract",open(h["upload"],"rb"),key=f"u{i}")

            if st.button("Delete",key=f"d{i}"):
                history.remove(h)
                save_history(history)
                st.rerun()

        if st.button("Clear All"):
            history.clear()
            save_history(history)
            st.rerun()

    else:
        st.info("No uploads.")

# ================= FOOTER =================

st.markdown("<center style='color:#6c7a91'>ClauseWise © 2026</center>",unsafe_allow_html=True)
# ================= SIDEBAR =================

with st.sidebar:

    st.markdown("## ClauseWise")

    with st.expander("About ClauseWise", expanded=True):
        st.write("""
ClauseWise is an AI-powered contract intelligence platform helping
individuals and SMEs detect risky clauses and generate legal insights.
""")

    with st.expander("How it works"):
        st.write("""
1. Upload or select sample contract  
2. AI scans clauses  
3. Risk score generated  
4. Download report  
""")

    with st.expander("Key Capabilities"):
        st.write("""
• Risk scoring  
• Clause highlighting  
• Dashboard analytics  
• PDF reports  
• History management  
""")

    st.markdown("---")
    st.subheader("Quick Tips")
    st.write("• Use sample contracts for demo\n• Upload PDF/TXT\n• Review dashboard")

    st.markdown("---")
    st.caption("ClauseWise © 2026")
