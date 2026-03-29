import streamlit as st
import requests, time

st.set_page_config(page_title="SAM-Body4D", page_icon="🏃")
st.title("🏃 SAM-Body4D Demo")

url = st.text_input("Paste tunnel URL:", placeholder="https://xxx.trycloudflare.com")
video = st.file_uploader("Upload video", type=["mp4", "avi", "mov"])

if video:
    st.video(video)

if st.button("🚀 Run Model") and video and url:
    base = url.rstrip("/")
    
    # Step 1: Submit job
    with st.spinner("📤 Uploading video..."):
        r = requests.post(
            f"{base}/process",
            files={"file": (video.name, video.getvalue(), "video/mp4")},
            timeout=60  # short timeout just for upload
        )
    
    if r.status_code != 200:
        st.error(f"Upload failed: {r.text}")
        st.stop()
    
    job_id = r.json()["job_id"]
    st.info(f"✅ Job started! ID: `{job_id}`")
    
    # Step 2: Poll status every 15 seconds
    progress = st.progress(0)
    status_box = st.empty()
    elapsed = 0
    
    while True:
        time.sleep(15)
        elapsed += 15
        
        try:
            s = requests.get(f"{base}/status/{job_id}", timeout=10).json()
        except:
            status_box.warning("⏳ Checking status...")
            continue
        
        pct = min(int((elapsed / 600) * 100), 95)
        progress.progress(pct)
        status_box.info(f"⏳ Status: `{s['status']}` — {elapsed}s elapsed")
        
        if s["status"] == "done":
            progress.progress(100)
            status_box.success("✅ Done!")
            
            # Download result
            res = requests.get(f"{base}/result/{job_id}", timeout=30)
            with open("result.mp4", "wb") as f:
                f.write(res.content)
            st.video("result.mp4")
            st.download_button("⬇️ Download", open("result.mp4","rb"), "result.mp4")
            break
        
        elif s["status"] == "error":
            st.error(f"❌ Error: {s.get('log', 'unknown')}")
            break
