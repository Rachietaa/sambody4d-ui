import streamlit as st
import requests
import time

st.set_page_config(page_title="SAM-Body4D Demo", page_icon="🏃", layout="wide")

st.markdown("""
    <h1 style='text-align: center;'>🏃 SAM-Body4D — Human Body Segmentation</h1>
    <p style='text-align: center; color: gray;'>Upload a video · Add point prompts · Generate Mask · Generate 4D</p>
    <hr>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    url = st.text_input("🔗 Colab Tunnel URL", placeholder="https://xxx.trycloudflare.com")
    st.caption("Run Cell B in Colab to get this URL")
    st.divider()
    st.markdown("### 📋 Workflow")
    st.markdown("""
    1. Run **Cell A** in Colab (FastAPI)
    2. Run **Cell B** in Colab (Tunnel)
    3. Paste tunnel URL above
    4. Upload video
    5. Add point prompts (positive/negative)
    6. Click **Mask Generation**
    7. Click **4D Generation**
    """)
    st.divider()
    st.markdown("### 🖥️ System")
    st.markdown("- **Model:** SAM-Body4D")
    st.markdown("- **Backend:** Google Colab T4 GPU")
    st.markdown("- **GUI:** Streamlit Cloud (Free)")

# Session state init
if "history" not in st.session_state:
    st.session_state.history = []
if "points" not in st.session_state:
    st.session_state.points = []  # list of {x, y, type}
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "mask_done" not in st.session_state:
    st.session_state.mask_done = False

# Main layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📤 Input Video")
    video = st.file_uploader("Upload video", type=["mp4", "avi", "mov"], label_visibility="collapsed")
    if video:
        st.video(video)
        st.success(f"✅ `{video.name}` — {round(len(video.getvalue())/1024/1024, 2)} MB")
    else:
        st.info("👆 Upload a video to get started")

    # Point Prompt Section
    st.markdown("### 🎯 Point Prompts")
    st.caption("Manually enter pixel coordinates to annotate targets on the first frame")

    pt_col1, pt_col2, pt_col3 = st.columns([2, 2, 2])
    with pt_col1:
        px = st.number_input("X (pixel)", min_value=0, value=100, step=10)
    with pt_col2:
        py = st.number_input("Y (pixel)", min_value=0, value=100, step=10)
    with pt_col3:
        pt_type = st.selectbox("Type", ["positive", "negative"])

    if st.button("➕ Add Point", use_container_width=True):
        st.session_state.points.append({"x": px, "y": py, "type": pt_type})
        st.success(f"Added {pt_type} point at ({px}, {py})")

    if st.session_state.points:
        st.markdown("**Current Points:**")
        for i, p in enumerate(st.session_state.points):
            color = "🟢" if p["type"] == "positive" else "🔴"
            st.write(f"{color} Point {i+1}: ({p['x']}, {p['y']}) — {p['type']}")
        if st.button("🗑️ Clear All Points", use_container_width=True):
            st.session_state.points = []
            st.session_state.mask_done = False
            st.rerun()

with col2:
    st.markdown("### 🎬 Output")
    mask_placeholder = st.empty()
    fourd_placeholder = st.empty()
    mask_placeholder.info("⏳ Mask output will appear here")
    fourd_placeholder.info("⏳ 4D output will appear here")

st.divider()

# Action Buttons
btn1, btn2, btn3 = st.columns(3)
with btn1:
    mask_btn = st.button("🧠 Mask Generation", use_container_width=True, type="primary")
with btn2:
    fourd_btn = st.button("🌐 4D Generation", use_container_width=True, type="primary",
                          disabled=not st.session_state.mask_done)
with btn3:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.points = []
        st.session_state.job_id = None
        st.session_state.mask_done = False
        st.rerun()

# ── Mask Generation ──
if mask_btn:
    if not video:
        st.error("❌ Please upload a video first!")
        st.stop()
    if not url:
        st.error("❌ Please paste the Colab tunnel URL in the sidebar!")
        st.stop()

    base = url.rstrip("/")
    points_payload = st.session_state.points  # send points to backend

    st.markdown("### 📊 Mask Processing")
    progress = st.progress(0)
    status_box = st.empty()
    timer_box = st.empty()

    with st.spinner("📤 Uploading video + prompts..."):
        try:
            r = requests.post(
                f"{base}/process",
                files={"file": (video.name, video.getvalue(), "video/mp4")},
                data={"points": str(points_payload)},
                timeout=60
            )
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
            st.stop()

    if r.status_code != 200:
        st.error(f"❌ Upload failed: {r.text}")
        st.stop()

    job_id = r.json()["job_id"]
    st.session_state.job_id = job_id
    status_box.info(f"✅ Job submitted! ID: `{job_id}`")

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
            status_box.success("✅ Mask generation complete!")
            timer_box.metric("⏱️ Total Time", f"{elapsed}s")

            res = requests.get(f"{base}/result/{job_id}", timeout=30)
            with open("mask_result.mp4", "wb") as f:
                f.write(res.content)

            with col2:
                mask_placeholder.empty()
                st.markdown("#### 🧠 Mask Result")
                st.video("mask_result.mp4")
                st.download_button("⬇️ Download Mask", open("mask_result.mp4", "rb"),
                                   "mask_result.mp4", use_container_width=True)

            st.session_state.mask_done = True
            st.session_state.history.append({
                "name": video.name, "type": "mask",
                "time": elapsed, "data": res.content
            })
            break

        elif s["status"] == "error":
            st.error(f"❌ Error: {s.get('log', 'unknown')}")
            break

# ── 4D Generation ──
if fourd_btn:
    if not url:
        st.error("❌ Please paste the Colab tunnel URL in the sidebar!")
        st.stop()

    base = url.rstrip("/")
    job_id = st.session_state.job_id

    st.markdown("### 📊 4D Processing")
    progress2 = st.progress(0)
    status_box2 = st.empty()
    timer_box2 = st.empty()

    with st.spinner("🌐 Starting 4D generation..."):
        try:
            r = requests.post(f"{base}/generate4d", json={"job_id": job_id}, timeout=60)
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
            st.stop()

    if r.status_code != 200:
        st.error(f"❌ 4D request failed: {r.text}")
        st.stop()

    new_job_id = r.json().get("job_id", job_id)
    elapsed = 0
    for _ in range(60):
        time.sleep(15)
        elapsed += 15
        timer_box2.metric("⏱️ Elapsed", f"{elapsed}s")
        try:
            s = requests.get(f"{base}/status/{new_job_id}", timeout=10).json()
        except:
            status_box2.warning("⏳ Checking 4D status...")
            continue

        pct = min(int((elapsed / 900) * 100), 95)
        progress2.progress(pct)
        status_box2.info(f"⏳ Status: `{s['status']}`")

        if s["status"] == "done":
            progress2.progress(100)
            status_box2.success("✅ 4D generation complete!")
            timer_box2.metric("⏱️ Total Time", f"{elapsed}s")

            res = requests.get(f"{base}/result/{new_job_id}", timeout=30)
            with open("4d_result.mp4", "wb") as f:
                f.write(res.content)

            with col2:
                fourd_placeholder.empty()
                st.markdown("#### 🌐 4D Result")
                st.video("4d_result.mp4")
                st.download_button("⬇️ Download 4D", open("4d_result.mp4", "rb"),
                                   "4d_result.mp4", use_container_width=True)

            st.session_state.history.append({
                "name": video.name if video else "video", "type": "4d",
                "time": elapsed, "data": res.content
            })
            break

        elif s["status"] == "error":
            st.error(f"❌ Error: {s.get('log', 'unknown')}")
            break

# ── Session History ──
if st.session_state.history:
    st.divider()
    st.markdown("### 🗂️ Session History")
    for i, item in enumerate(st.session_state.history):
        label = "🧠 Mask" if item["type"] == "mask" else "🌐 4D"
        with st.expander(f"{label} — {item['name']} ({item['time']}s)"):
            st.download_button(
                f"⬇️ Download",
                item["data"],
                f"result_{i+1}_{item['type']}.mp4",
                key=f"dl_{i}"
            )

# Footer
st.divider()
st.markdown("""
<p style='text-align: center; color: gray; font-size: 12px;'>
SAM-Body4D Demo · Streamlit Cloud · Colab T4 GPU Backend · UNC Charlotte
</p>
""", unsafe_allow_html=True)
