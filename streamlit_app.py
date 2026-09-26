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
DEFAULT_ROLES=["Delegate","Keynote Speaker","Invited Speaker","Researcher","Industry Professional","Entrepreneur","Student","Organizing Committee","Other"]
DEFAULT_THEMES=["Strategic Technology & Innovation Management","Artificial Intelligence & Generative AI","DeepTech & Emerging Technologies","Research, Entrepreneurship & Start-ups","Intellectual Property & Patent Strategy","Future-Ready Leadership & Sustainability"]
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
    df=df[FIELDS]
    if len(df):
        valid=(df["registration_id"].str.strip()!="") & (df["name"].str.strip()!="") & (df["email"].str.strip()!="")
        df=df[valid].copy()
        df=df.drop_duplicates(subset=["registration_id"],keep="last")
    return df.reset_index(drop=True)

def local_path(name):
    import os
    os.makedirs("app_data",exist_ok=True)
    return "app_data/"+name

def clean_options(values):
    out=[]
    for v in values:
        v=str(v).strip()
        if v and v not in out: out.append(v)
    return out

def load_taxonomy():
    p=local_path("taxonomy.json")
    try:
        if __import__("os").path.exists(p):
            with open(p,"r",encoding="utf-8") as fh: cfg=json.load(fh)
        else: cfg={}
    except Exception: cfg={}
    roles=clean_options(cfg.get("roles",DEFAULT_ROLES)) or DEFAULT_ROLES.copy()
    themes=clean_options(cfg.get("themes",DEFAULT_THEMES)) or DEFAULT_THEMES.copy()
    return roles,themes

def save_taxonomy(roles,themes):
    roles=clean_options(roles); themes=clean_options(themes)
    if not roles or not themes: raise ValueError("Keep at least one participation role and one primary focus.")
    with open(local_path("taxonomy.json"),"w",encoding="utf-8") as fh:
        json.dump({"roles":roles,"themes":themes},fh,ensure_ascii=False,indent=2)
    return True

ROLES,THEMES=load_taxonomy()

def github_token():
    return secret("GITHUB_TOKEN")

def github_read_csv(path=DATA_PATH):
    url="https://api.github.com/repos/"+REPO+"/contents/"+path+"?ref=main"
    headers={"Accept":"application/vnd.github+json","User-Agent":"ConvergeX"}
    if github_token(): headers["Authorization"]="Bearer "+github_token()
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=15) as r:
        obj=json.loads(r.read().decode("utf-8"))
    raw=base64.b64decode(obj.get("content",""))
    return normalize(pd.read_csv(io.BytesIO(raw),dtype=str)),obj.get("sha","")

def github_write_csv(df,path=DATA_PATH,message="Update ConvergeX registrations"):
    token=github_token()
    if not token: return False
    current,sha=github_read_csv(path)
    content=normalize(df).to_csv(index=False).encode("utf-8")
    payload={"message":message,"content":base64.b64encode(content).decode("ascii"),"branch":"main"}
    if sha: payload["sha"]=sha
    url="https://api.github.com/repos/"+REPO+"/contents/"+path
    req=urllib.request.Request(url,data=json.dumps(payload).encode("utf-8"),method="PUT",headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"User-Agent":"ConvergeX","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=20): pass
    return True

def load_data():
    p=local_path("registrations.csv")
    local_df=normalize(pd.DataFrame())
    try:
        if __import__("os").path.exists(p): local_df=normalize(pd.read_csv(p,dtype=str))
    except Exception: pass
    remote_df=normalize(pd.DataFrame())
    try:
        remote_df,_=github_read_csv()
    except Exception:
        try:
            req=urllib.request.Request(RAW+"?v="+uuid.uuid4().hex,headers={"Cache-Control":"no-cache"})
            with urllib.request.urlopen(req,timeout=15) as r: remote_df=normalize(pd.read_csv(io.BytesIO(r.read()),dtype=str))
        except Exception: pass
    if len(local_df) and len(remote_df):
        df=normalize(pd.concat([remote_df,local_df],ignore_index=True))
    elif len(local_df): df=local_df
    else: df=remote_df
    try: df.to_csv(p,index=False)
    except Exception: pass
    return df

def csv_blob(df): return normalize(df).to_csv(index=False).encode("utf-8-sig")

def excel_blob(df):
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w: normalize(df).to_excel(w,index=False,sheet_name="Registrations")
    return out.getvalue()

def save_data(df,message="Update ConvergeX registrations"):
    clean=normalize(df)
    clean.to_csv(local_path("registrations.csv"),index=False)
    remote_saved=False
    remote_error=""
    if github_token():
        try:
            remote_saved=github_write_csv(clean,DATA_PATH,message)
        except Exception as e:
            remote_error=str(e)
    st.session_state["last_remote_saved"]=remote_saved
    st.session_state["last_remote_error"]=remote_error
    return remote_saved

def register(row):
    df=load_data()
    if len(df) and any(df.email.str.lower()==row["email"].lower()): raise ValueError("This email address is already registered.")
    merged=normalize(pd.concat([df,pd.DataFrame([row])],ignore_index=True))
    if not any(merged.registration_id==row["registration_id"]):
        raise ValueError("Registration could not be added to the master record.")
    remote_saved=save_data(merged,"Add conference registration "+row["registration_id"])
    return remote_saved

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
    df=normalize(df)
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
.twin-shell{position:relative;min-height:620px;border:1px solid rgba(255,255,255,.09);border-radius:30px;overflow:hidden;background:radial-gradient(circle at 50% 48%,rgba(80,228,255,.12),transparent 30%),linear-gradient(145deg,rgba(4,16,28,.95),rgba(6,23,39,.72));padding:22px}.twin-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:16px}.twin-map{position:relative;min-height:520px;border-radius:24px;background-image:radial-gradient(rgba(80,228,255,.16) 1px,transparent 1px);background-size:26px 26px;border:1px solid rgba(255,255,255,.06)}.twin-core{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:150px;height:150px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:950;background:radial-gradient(circle,#173d5b,#081625 68%);border:1px solid var(--gold);box-shadow:0 0 55px rgba(243,199,95,.2);z-index:3}.twin-node{position:absolute;width:105px;height:105px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-align:center;padding:8px;font-size:.78rem;font-weight:850;background:#0a2033;border:1px solid rgba(80,228,255,.4);box-shadow:0 0 28px rgba(80,228,255,.08);animation:float 5s ease-in-out infinite}.tn1{left:8%;top:10%}.tn2{left:39%;top:5%}.tn3{right:8%;top:12%}.tn4{left:8%;bottom:10%}.tn5{left:39%;bottom:5%}.tn6{right:8%;bottom:12%}.twin-side{display:flex;flex-direction:column;gap:12px}.insight{padding:18px;border-radius:18px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.07)}.insight b{font-size:1.45rem;color:var(--cyan);display:block}.insight small{color:var(--muted)}@media(max-width:900px){.twin-grid{grid-template-columns:1fr}.twin-map{min-height:560px}.twin-node{width:90px;height:90px}.tn1{left:3%}.tn3{right:3%}.tn4{left:3%}.tn6{right:3%}}@media(max-width:900px){.metrics,.cards{grid-template-columns:1fr}.hero{padding:35px 22px;min-height:auto}.navtext{display:none}.const{height:620px}.o1{left:4%;top:45px}.o2{right:4%;left:auto;top:45px}.o3{left:4%;top:410px}.o4{right:4%;top:410px}.o5{left:4%;bottom:15px}.o6{right:4%;bottom:15px}}
</style>"""
st.markdown(CSS,unsafe_allow_html=True)
df=load_data(); programme=load_programme(); pub=approved(df); days=max((EVENT_DATE-datetime.now()).days,0)
df=normalize(df)
registration_count=int(df["registration_id"].nunique()) if len(df) else 0

def heading(a,b="",anchor=""):
    marker=f'<div id="{anchor}" style="scroll-margin-top:85px"></div>' if anchor else ""
    st.markdown(marker+f'<div class="title">{a}</div>'+ (f'<div class="sub">{b}</div>' if b else ""),unsafe_allow_html=True)

st.markdown('<div class="nav"><div class="logo">Converge<span>X</span></div><div class="navtext"><a href="#home">Home</a><a href="#experience">Experience</a><a href="#people">People</a><a href="#twin">Digital Twin</a><a href="#programme">Programme</a><a href="#venue">Venue</a><a href="#register">Register</a><a href="#status">Status</a><a href="#admin">Organizer</a></div><div class="badge">2026</div></div>',unsafe_allow_html=True)
st.markdown('<div id="home" style="scroll-margin-top:85px"></div>',unsafe_allow_html=True)
st.markdown(f"""<section class="hero"><div class="k">INTELLIGENT CONFERENCE EXPERIENCE PLATFORM</div><h1>STRATEGIC <span class="gold">TECHNOMANAGERIAL</span><br><span class="cyan">DEEPTECH INNOVATION</span><br>CONCLAVE 2026</h1><div class="lead">Where Strategy Meets Innovation to Shape Tomorrow.<br><b>25 October 2026 · The Sanihara Hotel & Resort · Wayanad, Kerala, India</b></div><div class="metrics"><div class="metric"><b>{days}</b><span>DAYS TO CONCLAVE</span></div><div class="metric"><b>{registration_count}</b><span>REGISTRATIONS</span></div><div class="metric"><b>{len(pub[pub.role.str.lower().str.contains("keynote",na=False)])}</b><span>APPROVED KEYNOTES</span></div><div class="metric"><b>{len(pub)}</b><span>PUBLIC PARTICIPANTS</span></div></div></section>""",unsafe_allow_html=True)

heading("Living Constellation","Six connected pathways through one conference experience.","experience")
st.markdown("""<div class="const"><div class="core">CONCLAVE<br>2026</div><div class="orb o1">AI</div><div class="orb o2">DeepTech</div><div class="orb o3">Research</div><div class="orb o4">Enterprise</div><div class="orb o5">IP Strategy</div><div class="orb o6">Leadership</div></div>""",unsafe_allow_html=True)

heading("Focus Areas","Explore the conference once; participant and speaker views below are generated from the same master record.")
short=["Strategy","AI & GenAI","DeepTech","Research & Start-ups","IP & Patents","Leadership"]
st.markdown('<div class="cards">'+"".join(f'<div class="card"><span class="badge">{i+1:02}</span><h3>{safe(a)}</h3><p>{safe(b)}</p></div>' for i,(a,b) in enumerate(zip(short,THEMES)))+'</div>',unsafe_allow_html=True)

heading("Conference Leadership")
st.markdown("""<div class="card"><span class="badge">CONCLAVE ORGANISER</span><div class="person">Ramesh Chandra Panda</div><p>Chairman & Chief Scientist, WEGROW · IPR Head of 12 Universities and 58 Engineering/Management/Law Colleges · Conclave Organiser · Editor of 7 Scopus-indexed journals</p></div>""",unsafe_allow_html=True)

heading("People","Organizer-approved registrations automatically populate the appropriate role view.","people")
role_tabs=st.tabs(["Keynotes","Invited Speakers","Delegates & Participants"])
keynote_roles=[x for x in ROLES if "keynote" in x.lower()]
invited_roles=[x for x in ROLES if "invited" in x.lower() and "keynote" not in x.lower()]
other_roles=[x for x in ROLES if x not in keynote_roles+invited_roles]
for tab,roles in zip(role_tabs,[keynote_roles,invited_roles,other_roles]):
    with tab:
        people=pub[pub.role.isin(roles)]
        if people.empty:st.info("No organizer-approved entries in this category yet.")
        else:
            cols=st.columns(3)
            for i,(_,r) in enumerate(people.iterrows()):
                with cols[i%3]:
                    talk=f'<p><b>{safe(r.talk_title)}</b></p>' if r.talk_title else ""
                    st.markdown(f'<div class="card"><span class="badge">{safe(r.role).upper()}</span><div class="person">{safe(r["name"])}</div><div class="muted">{safe(r.designation)}<br>{safe(r.institution)} · {safe(r.country)}</div>{talk}<p>{safe(r.profile)}</p></div>',unsafe_allow_html=True)

heading("Conference Digital Twin","Explore the living connections across people, institutions, ideas, talks and the conference programme.","twin")
twin_people=pub.copy()
theme_counts={t:int((twin_people.theme==t).sum()) for t in THEMES}
inst_count=int(twin_people.institution[twin_people.institution.str.strip()!=""].nunique()) if len(twin_people) else 0
role_count=int(twin_people.role[twin_people.role.str.strip()!=""].nunique()) if len(twin_people) else 0
talk_count=int((twin_people.talk_title.str.strip()!="").sum()) if len(twin_people) else 0
active_themes=sum(1 for v in theme_counts.values() if v>0)
top_theme=max(theme_counts,key=theme_counts.get) if theme_counts and max(theme_counts.values(),default=0)>0 else "Awaiting approved registrations"
labels=["Strategy","AI & GenAI","DeepTech","Research","IP Strategy","Leadership"]
display_themes=(THEMES+["","","","","",""])[:6]
counts=[theme_counts.get(t,0) if t else 0 for t in display_themes]
node_labels=[labels[i] if i>=len(THEMES) else (THEMES[i][:22]+"…" if len(THEMES[i])>22 else THEMES[i]) for i in range(6)]
nodes="".join(f'<div class="twin-node tn{i+1}">{safe(node_labels[i])}<br><span class="cyan">{counts[i]}</span></div>' for i in range(6))
st.markdown(f'''<div class="twin-shell"><div class="twin-grid"><div class="twin-map"><div class="twin-core">CONVERGEX<br>DIGITAL TWIN<br><span class="cyan">{len(twin_people)} PEOPLE</span></div>{nodes}</div><div class="twin-side"><div class="insight"><b>{len(twin_people)}</b><small>approved people represented</small></div><div class="insight"><b>{inst_count}</b><small>institutions connected</small></div><div class="insight"><b>{active_themes}/{len(THEMES)}</b><small>active thematic pathways</small></div><div class="insight"><b>{talk_count}</b><small>proposed talks connected</small></div><div class="insight"><b>{safe(top_theme)}</b><small>largest represented theme</small></div></div></div></div>''',unsafe_allow_html=True)

if twin_people.empty:
    st.info("The Digital Twin will activate automatically as the organizer approves registrations.")
else:
    twin_tabs=st.tabs(["Explore connections","Theme intelligence","Institution network"])
    with twin_tabs[0]:
        person_options=["All approved participants"]+sorted(twin_people["name"].tolist())
        who=st.selectbox("Explore a participant",person_options,key="twin_person")
        if who=="All approved participants":
            st.dataframe(twin_people[["name","role","institution","theme","talk_title"]],use_container_width=True,hide_index=True)
        else:
            r=twin_people[twin_people["name"]==who].iloc[0]
            a,b,c=st.columns(3)
            a.metric("Role",r.role);b.metric("Institution",r.institution or "—");c.metric("Theme",r.theme or "—")
            if r.talk_title: st.success("Connected talk: "+r.talk_title)
            related=twin_people[(twin_people.theme==r.theme)&(twin_people["name"]!=who)]
            if len(related): st.caption("Theme connections: "+", ".join(related["name"].tolist()))
            else: st.caption("No other approved participant currently shares this theme.")
    with twin_tabs[1]:
        intelligence=pd.DataFrame({"Theme":THEMES,"Approved people":counts}).sort_values("Approved people",ascending=False)
        st.dataframe(intelligence,use_container_width=True,hide_index=True)
        gaps=intelligence[intelligence["Approved people"]==0]["Theme"].tolist()
        if gaps: st.info("Currently unrepresented pathways: "+", ".join(gaps))
        else: st.success("All configured conference pathways currently have approved representation.")
    with twin_tabs[2]:
        inst=twin_people[twin_people.institution.str.strip()!=""].groupby("institution").agg(People=("name","count"),Themes=("theme","nunique"),Roles=("role","nunique")).reset_index().sort_values(["People","Themes"],ascending=False)
        st.dataframe(inst,use_container_width=True,hide_index=True)
        if len(inst): st.caption("Institutions with participation across more themes form stronger cross-theme bridges in the live twin.")

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

receipt=st.session_state.pop("registration_receipt",None)
if receipt:
    st.success("Registration complete. Your Registration ID is "+receipt["id"]+".")
    if receipt["remote"]:
        st.info("Registration saved to the conference master. The organizer can now review it.")
    else:
        st.warning("Registration is saved in this app session, but repository persistence did not complete. Please inform the organizer before closing the app.")

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
            remote_saved=register(row)
            st.session_state["registration_receipt"]={"id":rid,"remote":remote_saved}
            st.rerun()
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
            if github_token():
                try:
                    _remote_check,_remote_sha=github_read_csv()
                    st.caption("Data store: repository connected with local cache.")
                except Exception:
                    st.warning("Repository token is configured, but the registration master cannot currently be read. Registrations will remain in local cache until repository access is fixed.")
            else:
                st.caption("Data store: local app storage. Add GITHUB_TOKEN in Streamlit Secrets for repository persistence across redeployments.")
            regtab,progtab,optiontab=st.tabs(["Registration master","Programme editor","Registration options"])
            with regtab:
                st.caption("One professional review sheet: inspect, correct and change publication status in the same row, then save once.")
                if st.button("Refresh registration master",use_container_width=False):
                    st.rerun()
                review=df.copy()
                review=normalize(review)
                review.insert(0,"delete",False)
                if review.empty:
                    st.info("No registrations have been received yet.")
                else:
                    review=st.data_editor(
                        review,
                        num_rows="fixed",
                        use_container_width=True,
                        hide_index=True,
                        key="registration_review_sheet",
                        column_config={
                            "delete":st.column_config.CheckboxColumn("Delete",help="Select only if this registration should be permanently removed."),
                            "registration_id":st.column_config.TextColumn("Registration ID",disabled=True),
                            "timestamp":st.column_config.TextColumn("Received",disabled=True),
                            "name":st.column_config.TextColumn("Name",required=True),
                            "designation":st.column_config.TextColumn("Designation"),
                            "institution":st.column_config.TextColumn("Institution",required=True),
                            "email":st.column_config.TextColumn("Email",required=True),
                            "mobile":st.column_config.TextColumn("Mobile"),
                            "country":st.column_config.TextColumn("Country"),
                            "role":st.column_config.SelectboxColumn("Role",options=ROLES,required=True),
                            "theme":st.column_config.SelectboxColumn("Theme",options=THEMES),
                            "talk_title":st.column_config.TextColumn("Talk title"),
                            "profile":st.column_config.TextColumn("Profile"),
                            "status":st.column_config.SelectboxColumn("Publication status",options=["Pending","Approved","Hidden","Rejected"],required=True,help="Approved publishes the record. Hidden/Rejected/Pending keep it private."),
                            "payment":st.column_config.SelectboxColumn("Payment",options=["Pending","Paid","Waived","Not applicable"]),
                            "accommodation":st.column_config.SelectboxColumn("Accommodation",options=["","Pending","Confirmed","Not required"]),
                            "certificate":st.column_config.SelectboxColumn("Certificate",options=["","Pending","Ready","Issued"])
                        }
                    )
                    valid_review=review[(review["registration_id"].fillna("").str.strip()!="") & (review["name"].fillna("").str.strip()!="") & (review["email"].fillna("").str.strip()!="")].copy()
                    pending_n=int((valid_review.status.str.lower()=="pending").sum())
                    approved_n=int(valid_review.status.str.lower().isin(["approved","confirmed","active"]).sum())
                    hidden_n=int(valid_review.status.str.lower().isin(["hidden","rejected"]).sum())
                    delete_n=int(valid_review["delete"].fillna(False).astype(bool).sum())
                    m1,m2,m3,m4=st.columns(4)
                    actual_review=valid_review
                    m1.metric("Registrations",int(actual_review["registration_id"].nunique()));m2.metric("Awaiting review",pending_n);m3.metric("Published",approved_n);m4.metric("Private",hidden_n)
                    c1,c2=st.columns([2,1])
                    with c1:
                        if st.button("Save all changes",type="primary",use_container_width=True):
                            try:
                                kept=review[~review["delete"].fillna(False).astype(bool)].drop(columns=["delete"],errors="ignore")
                                invalid=kept[(kept["registration_id"].fillna("").str.strip()=="") | (kept["name"].fillna("").str.strip()=="") | (kept["email"].fillna("").str.strip()=="")]
                                if len(invalid):
                                    st.error("A registration cannot be saved without Registration ID, Name and Email.")
                                else:
                                    save_data(normalize(kept))
                                    st.success("Changes saved. Approved registrations are now published.")
                                    st.rerun()
                            except Exception as e:st.error("Could not save the registration sheet. "+str(e))
                    with c2:
                        st.download_button("Download Excel backup",excel_blob(review),"ConvergeX_Registrations.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                    st.caption("Approve publishes a row; Hidden removes it from the public site without deleting it. For a permanent removal, tick Delete in that row and then Save all changes.")
            with progtab:
                st.caption("Add the programme hour by hour. Use status Published to make a row visible publicly; Draft remains private.")
                ped=programme.copy()
                if ped.empty: ped=pd.DataFrame([{"time":"","title":"","description":"","status":"Draft"}],columns=PROGRAMME_FIELDS)
                ped=st.data_editor(ped,num_rows="dynamic",use_container_width=True,hide_index=True,column_config={"time":st.column_config.TextColumn("Time",help="Example: 09:30 AM"),"title":st.column_config.TextColumn("Session title"),"description":st.column_config.TextColumn("Description"),"status":st.column_config.SelectboxColumn("Status",options=["Draft","Published"])},key="programme_editor")
                if st.button("Save programme",type="primary",use_container_width=True):
                    try: save_programme(ped); st.success("Programme saved. Published rows will appear in the Programme section after refresh.")
                    except Exception as e: st.error(str(e))
            with optiontab:
                st.caption("Edit the choices shown in the public registration form. Saving here updates Participation role and Primary focus across the app.")
                st.markdown("#### Participation roles")
                role_df=pd.DataFrame({"Participation role":ROLES})
                role_edit=st.data_editor(role_df,num_rows="dynamic",use_container_width=True,hide_index=True,key="role_options_editor",column_config={"Participation role":st.column_config.TextColumn("Participation role",required=True)})
                st.markdown("#### Primary focus areas")
                theme_df=pd.DataFrame({"Primary focus":THEMES})
                theme_edit=st.data_editor(theme_df,num_rows="dynamic",use_container_width=True,hide_index=True,key="theme_options_editor",column_config={"Primary focus":st.column_config.TextColumn("Primary focus",required=True)})
                if st.button("Save registration options",type="primary",use_container_width=True):
                    try:
                        new_roles=clean_options(role_edit["Participation role"].tolist())
                        new_themes=clean_options(theme_edit["Primary focus"].tolist())
                        save_taxonomy(new_roles,new_themes)
                        st.success("Registration options saved. The registration form and connected views now use the updated choices.")
                        st.rerun()
                    except Exception as e: st.error("Could not save registration options. "+str(e))
        else:
            st.error("Invalid organizer credentials.")

st.markdown("""<hr><center><b>ConvergeX — Intelligent Conference Experience Platform</b><br>Platform design & development: <a href="https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=10902268" target="_blank" rel="noopener noreferrer">Dr. Mohammad Amir Khusru Akhtar</a></center>""",unsafe_allow_html=True)
