import streamlit as st
import requests
import time

st.set_page_config(
    page_title="SAM-Body4D Demo",
    page_icon="🏃",
    layout="wide"
)

# Header
st.markdown("""
    <h1 style='text-align: center;'>🏃 SAM-Body4D — Human Body Segmentation</h1>
    <p style='text-align: center; color: gray;'>Upload a video to generate 4D body mesh segmentation using SAM-Body4D on Colab GPU</p>
    <hr>
""", unsafe_allow_html=True)

# Sidebar config
with st.sidebar:
    st.header("⚙️ Configuration")
    url = st.text_input("🔗 Colab Tunnel URL", placeholder="https://xxx.trycloudflare.com")
    st.caption("Run Cell B in Colab to get this URL")
    st.divider()
    st.markdown("### 📋 How to Use")
    st.markdown("""
    1. Run **Cell A** in Colab (FastAPI)
    2. Run **Cell B** in Colab (Tunnel)
    3. Paste the tunnel URL above
    4. Upload your video
    5. Click **Run Model**
    """)
    st.divider()
    st.markdown("### 🖥️ System")
    st.markdown("- **Model:** SAM-Body4D")
    st.markdown("- **Backend:** Google Colab T4 GPU")
    st.markdown("- **GUI:** Streamlit Cloud (Free)")

# Main layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📤 Input Video")
    video = st.file_uploader("Upload your video", type=["mp4", "avi", "mov"], label_visibility="collapsed")
    if video:
        st.video(video)
        st.success(f"✅ Loaded: `{video.name}` ({round(len(video.getvalue())/1024/1024, 2)} MB)")
    else:
        st.info("👆 Upload a video to get started")

with col2:
    st.markdown("### 🎯 Output Result")
    result_placeholder = st.empty()
    result_placeholder.info("⏳ Output will appear here after processing")

st.divider()

# Run button centered
_, btn_col, _ = st.columns([2, 1, 2])
with btn_col:
    run = st.button("🚀 Run SAM-Body4D", use_container_width=True, type="primary")

# Processing
if run:
    if not video:
        st.error("❌ Please upload a video first!")
        st.stop()
    if not url:
        st.error("❌ Please paste the Colab tunnel URL in the sidebar!")
        st.stop()

    base = url.rstrip("/")

    # Progress section
    st.markdown("### 📊 Processing Status")
    prog_col1, prog_col2 = st.columns([3, 1])

    with prog_col1:
        progress = st.progress(0)
        status_box = st.empty()

    with prog_col2:
        timer_box = st.empty()

    # Upload
    with st.spinner("📤 Uploading video to Colab..."):
        try:
            r = requests.post(
                f"{base}/process",
                files={"file": (video.name, video.getvalue(), "video/mp4")},
                timeout=60
            )
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
            st.stop()

    if r.status_code != 200:
        st.error(f"❌ Upload failed: {r.text}")
        st.stop()

    job_id = r.json()["job_id"]
    status_box.info(f"✅ Job submitted! ID: `{job_id}`")

    # Poll
    elapsed = 0
    for _ in range(40):
        time.sleep(15)
        elapsed += 15
        timer_box.metric("⏱️ Elapsed", f"{elapsed}s")

        try:
            s = requests.get(f"{base}/status/{job_id}", timeout=10).json()
        except:
            status_box.warning("⏳ Checking status...")
            continue

        pct = min(int((elapsed / 600) * 100), 95)
        progress.progress(pct)
        status_box.info(f"⏳ Status: `{s['status']}`")

        if s["status"] == "done":
            progress.progress(100)
            status_box.success("✅ Processing complete!")
            timer_box.metric("⏱️ Total Time", f"{elapsed}s")

            # Show result in right column
            res = requests.get(f"{base}/result/{job_id}", timeout=30)
            with open("result.mp4", "wb") as f:
                f.write(res.content)

            with col2:
                result_placeholder.empty()
                st.video("result.mp4")
                st.download_button(
                    "⬇️ Download Result",
                    open("result.mp4", "rb"),
                    "result.mp4",
                    use_container_width=True
                )
            break

        elif s["status"] == "error":
            st.error(f"❌ Error: {s.get('log', 'unknown')}")
            break

# Footer
st.divider()
st.markdown("""
<p style='text-align: center; color: gray; font-size: 12px;'>
SAM-Body4D Demo · Streamlit Cloud · Colab T4 GPU Backend · UNC Charlotte
</p>
""", unsafe_allow_html=True)
