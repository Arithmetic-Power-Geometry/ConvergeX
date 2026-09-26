import streamlit as st
import pandas as pd
import csv, io, json, uuid, base64, urllib.request, urllib.error, hashlib, hmac
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="ConvergeX 2026",page_icon="✦",layout="wide",initial_sidebar_state="collapsed")

REPO="Arithmetic-Power-Geometry/ConvergeX"
DATA_PATH="data/registrations.csv"
PROGRAMME_PATH="data/programme.csv"
PROGRAMME_FIELDS=["time","title","description","status"]
RAW="https://raw.githubusercontent.com/"+REPO+"/main/"+DATA_PATH
EVENT_DATE=datetime(2026,10,25,9,0)
ROLES=["Delegate","Keynote Speaker","Invited Speaker","Researcher","Industry Professional","Entrepreneur","Student","Organizing Committee","Other"]
THEMES=["Strategic Technology & Innovation Management","Artificial Intelligence & Generative AI","DeepTech & Emerging Technologies","Research, Entrepreneurship & Start-ups","Intellectual Property & Patent Strategy","Future-Ready Leadership & Sustainability"]
FIELDS=["registration_id","timestamp","name","designation","institution","email","mobile","country","role","theme","talk_title","profile","status","payment","accommodation","certificate"]
PUBLIC=["registration_id","name","designation","institution","country","role","theme","talk_title"]

def secret(name,default=""):
    try:return str(st.secrets[name])
    except Exception:return default

def storage_note():
    return "Saved in the app data store. Use organizer Excel/CSV export for backup or repository archival."

def normalize(df):
    if df is None: df=pd.DataFrame()
    df=df.fillna("").astype(str)
    for c in FIELDS:
        if c not in df.columns:df[c]=""
    return df[FIELDS]

def local_path(name):
    import os
    os.makedirs("app_data",exist_ok=True)
    return "app_data/"+name

def load_data():
    p=local_path("registrations.csv")
    try:
        if __import__("os").path.exists(p): return normalize(pd.read_csv(p,dtype=str))
        req=urllib.request.Request(RAW+"?v="+uuid.uuid4().hex,headers={"Cache-Control":"no-cache"})
        with urllib.request.urlopen(req,timeout=15) as r:
            df=normalize(pd.read_csv(io.BytesIO(r.read()),dtype=str)); df.to_csv(p,index=False); return df
    except Exception:return normalize(pd.DataFrame())

def csv_blob(df): return normalize(df).to_csv(index=False).encode("utf-8-sig")

def excel_blob(df):
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w: normalize(df).to_excel(w,index=False,sheet_name="Registrations")
    return out.getvalue()

def save_data(df,message=""):
    p=local_path("registrations.csv"); normalize(df).to_csv(p,index=False); return True

def register(row):
    df=load_data()
    if len(df) and any(df.email.str.lower()==row["email"].lower()): raise ValueError("This email address is already registered.")
    save_data(pd.concat([df,pd.DataFrame([row])],ignore_index=True))
    return True

def load_programme():
    p=local_path("programme.csv")
    try:
        if __import__("os").path.exists(p):
            x=pd.read_csv(p,dtype=str).fillna("")
        else:
            url="https://raw.githubusercontent.com/"+REPO+"/main/"+PROGRAMME_PATH+"?v="+uuid.uuid4().hex
            with urllib.request.urlopen(url,timeout=12) as r:x=pd.read_csv(io.BytesIO(r.read()),dtype=str).fillna("")
            x.to_csv(p,index=False)
        for c in PROGRAMME_FIELDS:
            if c not in x.columns:x[c]=""
        return x[PROGRAMME_FIELDS]
    except Exception:return pd.DataFrame(columns=PROGRAMME_FIELDS)

def save_programme(pdf):
    for c in PROGRAMME_FIELDS:
        if c not in pdf.columns:pdf[c]=""
    pdf[PROGRAMME_FIELDS].fillna("").to_csv(local_path("programme.csv"),index=False)
    return True

def admin_ok(u,p):
    au=secret("ADMIN_USERNAME","ramesh")
    ap=secret("ADMIN_PASSWORD")
    return bool(ap) and hmac.compare_digest(u,au) and hmac.compare_digest(p,ap)

def approved(df):
    return df[df.status.str.lower().isin(["approved","confirmed","active"])].copy()

def safe(s):
    import html
    return html.escape(str(s or ""))

CSS="""<style>
:root{--gold:#f3c75f;--cyan:#50e4ff;--text:#f7fbff;--muted:#9fb2c6;--glass:rgba(255,255,255,.06)}
html{scroll-behavior:smooth}.stApp{background:radial-gradient(circle at 15% 5%,rgba(80,228,255,.12),transparent 23%),radial-gradient(circle at 86% 8%,rgba(243,199,95,.11),transparent 22%),linear-gradient(145deg,#030912,#07192b 55%,#04101c);color:var(--text)}
.block-container{max-width:1400px;padding-top:1rem}#MainMenu,footer{visibility:hidden}.stApp header{background:transparent}
.nav{position:sticky;top:.5rem;z-index:99;display:flex;align-items:center;justify-content:space-between;padding:12px 18px;border:1px solid rgba(255,255,255,.09);border-radius:18px;background:rgba(3,10,19,.75);backdrop-filter:blur(18px)}
.logo{font-weight:950;font-size:1.2rem}.logo span{color:var(--cyan)}.navtext{display:flex;gap:7px;flex-wrap:wrap;justify-content:center}.navtext a{color:#d6e4ef;text-decoration:none;padding:8px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.035);font-size:.72rem;font-weight:800;letter-spacing:.04em;transition:.2s}.navtext a:hover{color:#06111f;background:var(--cyan);transform:translateY(-1px)}
.hero{position:relative;overflow:hidden;margin-top:16px;min-height:610px;padding:62px;border:1px solid rgba(255,255,255,.09);border-radius:34px;background:radial-gradient(circle at 80% 45%,rgba(80,228,255,.16),transparent 22%),linear-gradient(110deg,rgba(3,10,18,.97),rgba(5,20,35,.74))}
.hero:after{content:"";position:absolute;width:520px;height:520px;border-radius:50%;right:-120px;top:50px;border:1px solid rgba(80,228,255,.23);box-shadow:0 0 80px rgba(80,228,255,.07);animation:pulse 5s ease-in-out infinite}
@keyframes pulse{50%{transform:scale(1.06);opacity:.62}}@keyframes float{50%{transform:translateY(-9px)}}.k{color:var(--gold);font-size:.78rem;font-weight:900;letter-spacing:.18em}.hero h1{font-size:clamp(3rem,6vw,6.1rem);line-height:.92;margin:.7rem 0 1.1rem;max-width:1000px}.gold{color:var(--gold)}.cyan{color:var(--cyan)}.lead{font-size:1.1rem;line-height:1.65;color:#d4e0eb;max-width:780px}
.metrics,.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}.metric,.card{background:var(--glass);border:1px solid rgba(255,255,255,.085);border-radius:21px;padding:20px;backdrop-filter:blur(8px)}.metric{text-align:center}.metric b{font-size:1.7rem;color:var(--cyan)}.metric span{display:block;color:var(--muted);font-size:.77rem}.card{min-height:145px;transition:.25s}.card:hover{transform:translateY(-4px);border-color:rgba(80,228,255,.32)}.card p{color:#b5c6d6;line-height:1.5}.title{font-size:2rem;font-weight:950;margin:2.5rem 0 .25rem}.sub{color:var(--muted);margin-bottom:1.1rem}
.const{height:475px;position:relative;border:1px solid rgba(255,255,255,.08);border-radius:30px;background:radial-gradient(circle at center,rgba(80,228,255,.13),transparent 35%);overflow:hidden}.core,.orb{position:absolute;border-radius:50%;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:900}.core{width:160px;height:160px;left:calc(50% - 80px);top:158px;border:1px solid var(--gold);background:#0a2033;box-shadow:0 0 50px rgba(243,199,95,.13)}.orb{width:108px;height:108px;border:1px solid rgba(80,228,255,.42);background:#081a2b;animation:float 4s ease-in-out infinite}.o1{left:8%;top:65px}.o2{left:29%;top:25px}.o3{right:29%;top:25px}.o4{right:8%;top:65px}.o5{left:20%;bottom:38px}.o6{right:20%;bottom:38px}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:rgba(243,199,95,.12);color:var(--gold);font-size:.72rem;font-weight:900}.person{font-size:1.15rem;font-weight:900;margin:.5rem 0}.muted{color:var(--muted)}.timeline{border-left:2px solid rgba(80,228,255,.25);padding-left:24px}.slot{position:relative;padding:10px 0 18px}.slot:before{content:"";position:absolute;left:-30px;top:17px;width:10px;height:10px;border-radius:50%;background:var(--gold)}
@media(max-width:900px){.metrics,.cards{grid-template-columns:1fr}.hero{padding:35px 22px;min-height:auto}.navtext{display:none}.const{height:620px}.o1{left:4%;top:45px}.o2{right:4%;left:auto;top:45px}.o3{left:4%;top:410px}.o4{right:4%;top:410px}.o5{left:4%;bottom:15px}.o6{right:4%;bottom:15px}}
</style>"""
st.markdown(CSS,unsafe_allow_html=True)
df=load_data(); programme=load_programme(); pub=approved(df); days=max((EVENT_DATE-datetime.now()).days,0)

def heading(a,b="",anchor=""):
    marker=f'<div id="{anchor}" style="scroll-margin-top:85px"></div>' if anchor else ""
    st.markdown(marker+f'<div class="title">{a}</div>'+ (f'<div class="sub">{b}</div>' if b else ""),unsafe_allow_html=True)

st.markdown('<div class="nav"><div class="logo">Converge<span>X</span></div><div class="navtext"><a href="#home">Home</a><a href="#experience">Experience</a><a href="#people">People</a><a href="#programme">Programme</a><a href="#venue">Venue</a><a href="#register">Register</a><a href="#status">Status</a><a href="#admin">Organizer</a></div><div class="badge">2026</div></div>',unsafe_allow_html=True)
st.markdown('<div id="home" style="scroll-margin-top:85px"></div>',unsafe_allow_html=True)
st.markdown(f"""<section class="hero"><div class="k">INTELLIGENT CONFERENCE EXPERIENCE PLATFORM</div><h1>STRATEGIC <span class="gold">TECHNOMANAGERIAL</span><br><span class="cyan">DEEPTECH INNOVATION</span><br>CONCLAVE 2026</h1><div class="lead">Where Strategy Meets Innovation to Shape Tomorrow.<br><b>25 October 2026 · The Sanihara Hotel & Resort · Wayanad, Kerala, India</b></div><div class="metrics"><div class="metric"><b>{days}</b><span>DAYS TO CONCLAVE</span></div><div class="metric"><b>{len(df)}</b><span>REGISTRATIONS</span></div><div class="metric"><b>{len(pub[pub.role=="Keynote Speaker"])}</b><span>APPROVED KEYNOTES</span></div><div class="metric"><b>{len(pub)}</b><span>PUBLIC PARTICIPANTS</span></div></div></section>""",unsafe_allow_html=True)

heading("Living Constellation","Six connected pathways through one conference experience.","experience")
st.markdown("""<div class="const"><div class="core">CONCLAVE<br>2026</div><div class="orb o1">AI</div><div class="orb o2">DeepTech</div><div class="orb o3">Research</div><div class="orb o4">Enterprise</div><div class="orb o5">IP Strategy</div><div class="orb o6">Leadership</div></div>""",unsafe_allow_html=True)

heading("Focus Areas","Explore the conference once; participant and speaker views below are generated from the same master record.")
short=["Strategy","AI & GenAI","DeepTech","Research & Start-ups","IP & Patents","Leadership"]
st.markdown('<div class="cards">'+"".join(f'<div class="card"><span class="badge">{i+1:02}</span><h3>{safe(a)}</h3><p>{safe(b)}</p></div>' for i,(a,b) in enumerate(zip(short,THEMES)))+'</div>',unsafe_allow_html=True)

heading("Conference Leadership")
st.markdown("""<div class="card"><span class="badge">CONCLAVE ORGANISER</span><div class="person">Ramesh Chandra Panda</div><p>Chairman & Chief Scientist, WEGROW · IPR Head of 12 Universities and 58 Engineering/Management/Law Colleges · Conclave Organiser · Editor of 7 Scopus-indexed journals</p></div>""",unsafe_allow_html=True)

heading("People","Organizer-approved registrations automatically populate the appropriate role view.","people")
role_tabs=st.tabs(["Keynotes","Invited Speakers","Delegates & Participants"])
for tab,roles in zip(role_tabs,[["Keynote Speaker"],["Invited Speaker"],[x for x in ROLES if x not in ["Keynote Speaker","Invited Speaker"]]]):
    with tab:
        people=pub[pub.role.isin(roles)]
        if people.empty:st.info("No organizer-approved entries in this category yet.")
        else:
            cols=st.columns(3)
            for i,(_,r) in enumerate(people.iterrows()):
                with cols[i%3]:
                    talk=f'<p><b>{safe(r.talk_title)}</b></p>' if r.talk_title else ""
                    st.markdown(f'<div class="card"><span class="badge">{safe(r.role).upper()}</span><div class="person">{safe(r["name"])}</div><div class="muted">{safe(r.designation)}<br>{safe(r.institution)} · {safe(r.country)}</div>{talk}<p>{safe(r.profile)}</p></div>',unsafe_allow_html=True)

heading("Programme","The organizer publishes the schedule from the programme editor.","programme")
if programme.empty or not any(programme.title.str.strip()):
    st.markdown('<div class="card"><span class="badge">PROGRAMME</span><h3>Coming soon</h3><p>The detailed hour-wise programme will be published here by the organizer.</p></div>',unsafe_allow_html=True)
else:
    visible=programme[programme.status.str.lower().isin(["published","active","confirmed"])]
    if visible.empty: st.markdown('<div class="card"><span class="badge">PROGRAMME</span><h3>Coming soon</h3><p>The detailed hour-wise programme will be published here by the organizer.</p></div>',unsafe_allow_html=True)
    else:
        html='<div class="timeline">'
        for _,r in visible.iterrows():
            html+=f'<div class="slot"><b>{safe(r["time"])}</b><h3>{safe(r["title"])}</h3><p>{safe(r["description"])}</p></div>'
        st.markdown(html+'</div>',unsafe_allow_html=True)

heading("Venue","A single destination for the conclave.","venue")
st.markdown("""<div class="cards"><div class="card"><span class="badge">LOCATION</span><h3>The Sanihara Hotel & Resort</h3><p>Wayanad, Kerala, India</p></div><div class="card"><span class="badge">DATE</span><h3>25 October 2026</h3><p>Strategic technology, research, innovation and collaboration.</p></div><div class="card"><span class="badge">FORMAT</span><h3>In-person Conclave</h3><p>Plenary exchange, thematic sessions and professional networking.</p></div><div class="card"><span class="badge">AUDIENCE</span><h3>Cross-disciplinary</h3><p>Academia · Research · Industry · Entrepreneurship · Technology · IP</p></div></div>""",unsafe_allow_html=True)

heading("Register","Submit once. Your role determines the directory in which you appear after approval.","register")
with st.form("registration",clear_on_submit=True):
    a,b=st.columns(2)
    with a:
        name=st.text_input("Full name *"); designation=st.text_input("Designation"); institution=st.text_input("Institution / organization *"); email=st.text_input("Email *"); mobile=st.text_input("Mobile")
    with b:
        country=st.text_input("Country",value="India"); role=st.selectbox("Participation role *",ROLES); theme=st.selectbox("Primary focus",THEMES); talk=st.text_input("Proposed talk title (speaker roles)"); profile=st.text_area("Short professional profile")
    consent=st.checkbox("I confirm the information is correct and consent to its use for conference administration.")
    submitted=st.form_submit_button("Complete Registration",use_container_width=True)
if submitted:
    missing=[]
    if not name.strip(): missing.append("Full name")
    if not institution.strip(): missing.append("Institution / organization")
    if not email.strip(): missing.append("Email")
    elif "@" not in email or "." not in email.split("@")[-1]: missing.append("a valid email address")
    if not consent: missing.append("the consent checkbox")
    if missing: st.warning("Please complete: "+", ".join(missing)+".")
    else:
        rid="STDI-2026-"+uuid.uuid4().hex[:6].upper()
        row={c:"" for c in FIELDS};row.update({"registration_id":rid,"timestamp":datetime.now().isoformat(timespec="seconds"),"name":name.strip(),"designation":designation.strip(),"institution":institution.strip(),"email":email.strip(),"mobile":mobile.strip(),"country":country.strip(),"role":role,"theme":theme,"talk_title":talk.strip(),"profile":profile.strip(),"status":"Pending","payment":"Pending","accommodation":"","certificate":""})
        try:
            register(row);st.success(f"Registration complete. Your Registration ID is {rid}.");st.info("Registration received. The organizer will review it before publication in the conference directory.")
        except ValueError as e:st.warning(str(e))
        except Exception as e:st.error(str(e))

heading("Registration Status","Check administrative progress without exposing contact information.","status")
q=st.text_input("Registration ID",placeholder="STDI-2026-XXXXXX")
if q:
    hit=df[df.registration_id.str.upper()==q.strip().upper()]
    if hit.empty:st.warning("Registration ID not found.")
    else:
        r=hit.iloc[0]
        c1,c2,c3,c4=st.columns(4);c1.metric("Status",r.status or "Pending");c2.metric("Payment",r.payment or "Pending");c3.metric("Accommodation",r.accommodation or "—");c4.metric("Certificate",r.certificate or "—")
        st.caption(f"{r['name']} · {r.role} · {r.institution}")

heading("Administration","Organizer-only control for registrations and the hour-wise programme.","admin")
with st.expander("Organizer console"):
    u=st.text_input("Admin username",key="admin_u")
    p=st.text_input("Admin password",type="password",key="admin_p")
    if u or p:
        if not secret("ADMIN_PASSWORD"):
            st.warning("Organizer access is not configured yet. Add ADMIN_PASSWORD in Streamlit Secrets.")
        elif admin_ok(u,p):
            st.success("Organizer access granted.")
            regtab,progtab=st.tabs(["Registration master","Programme editor"])
            with regtab:
                st.caption("Review pending registrations first. Approve publishes the person automatically in the correct People section; Reject keeps the record private.")
                pending=df[df.status.str.lower()=="pending"].copy()
                if pending.empty:
                    st.info("No registrations are waiting for approval.")
                else:
                    for idx,r in pending.iterrows():
                        with st.container(border=True):
                            left,right=st.columns([4,1])
                            with left:
                                st.markdown(f"**{safe(r['name'])}**  ·  {safe(r['role'])}")
                                st.caption(f"{safe(r['designation'])} · {safe(r['institution'])} · {safe(r['country'])} · {safe(r['email'])}")
                                if r["talk_title"]: st.write("Proposed talk:",r["talk_title"])
                                if r["profile"]: st.write(r["profile"])
                            with right:
                                if st.button("✓ Approve",key=f"approve_{r['registration_id']}",type="primary",use_container_width=True):
                                    fresh=load_data(); fresh.loc[fresh.registration_id==r["registration_id"],"status"]="Approved"; save_data(fresh); st.success("Approved and published."); st.rerun()
                                if st.button("Reject",key=f"reject_{r['registration_id']}",use_container_width=True):
                                    fresh=load_data(); fresh.loc[fresh.registration_id==r["registration_id"],"status"]="Rejected"; save_data(fresh); st.warning("Registration rejected."); st.rerun()
                st.markdown("#### Master registration sheet")
                st.caption("You can also correct any field directly below. Approved/Confirmed/Active records are public; Pending/Rejected/Hidden records remain private.")
                edited=normalize(st.data_editor(df,num_rows="dynamic",use_container_width=True,hide_index=True,key="master_editor"))
                c1,c2,c3=st.columns(3)
                with c1:
                    if st.button("Save master",type="primary",use_container_width=True):
                        try: save_data(edited,"Organizer update registrations"); st.success("Registration master saved.")
                        except Exception as e: st.error(str(e))
                with c2:
                    st.download_button("Download Excel",excel_blob(edited),"ConvergeX_Registrations.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                with c3:
                    st.download_button("Download CSV",csv_blob(edited),"registrations.csv","text/csv",use_container_width=True)
                upload=st.file_uploader("Upload a corrected Excel or CSV master",type=["xlsx","csv"],key="master_upload")
                if upload:
                    try:
                        incoming=normalize(pd.read_excel(upload,dtype=str) if upload.name.lower().endswith(".xlsx") else pd.read_csv(upload,dtype=str))
                        st.dataframe(incoming,use_container_width=True,hide_index=True)
                        if st.button("Replace master with uploaded file"):
                            save_data(incoming); st.success("Corrected master saved.")
                    except Exception as e: st.error("Please check the workbook format. "+str(e))
                a,b,c,d=st.columns(4);a.metric("Total",len(df));b.metric("Pending",sum(df.status.str.lower()=="pending"));c.metric("Approved",len(pub));d.metric("Keynotes",sum(df.role=="Keynote Speaker"))
            with progtab:
                st.caption("Add the programme hour by hour. Use status Published to make a row visible publicly; Draft remains private.")
                ped=programme.copy()
                if ped.empty: ped=pd.DataFrame([{"time":"","title":"","description":"","status":"Draft"}],columns=PROGRAMME_FIELDS)
                ped=st.data_editor(ped,num_rows="dynamic",use_container_width=True,hide_index=True,column_config={"time":st.column_config.TextColumn("Time",help="Example: 09:30 AM"),"title":st.column_config.TextColumn("Session title"),"description":st.column_config.TextColumn("Description"),"status":st.column_config.SelectboxColumn("Status",options=["Draft","Published"])},key="programme_editor")
                if st.button("Save programme",type="primary",use_container_width=True):
                    try: save_programme(ped); st.success("Programme saved. Published rows will appear in the Programme section after refresh.")
                    except Exception as e: st.error(str(e))
        else:
            st.error("Invalid organizer credentials.")

st.markdown("<hr><center><b>ConvergeX — Intelligent Conference Experience Platform</b><br>Platform design & development: Dr. Mohammad Amir Khusru Akhtar</center>",unsafe_allow_html=True)
