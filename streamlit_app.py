import base64
import streamlit as st
import pandas as pd
import csv, io, json, uuid, base64, urllib.request, urllib.error, hashlib, hmac
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="ConvergeX 2026",page_icon="✦",layout="wide",initial_sidebar_state="collapsed")

REPO="Arithmetic-Power-Geometry/ConvergeX"
DATA_PATH="data/registrations.csv"
PROGRAMME_PATH="data/programme.csv"
PROGRAMME_FIELDS=["date","time","title","description","status"]
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

def merge_records(base,incoming):
    base=normalize(base); incoming=normalize(incoming)
    records={}
    order=[]
    for frame in [base,incoming]:
        for _,r in frame.iterrows():
            rid=r["registration_id"].strip()
            if not rid: continue
            if rid not in records:
                records[rid]={c:"" for c in FIELDS}; order.append(rid)
            for c in FIELDS:
                v=str(r[c]).strip()
                if v!="": records[rid][c]=v
    return normalize(pd.DataFrame([records[r] for r in order],columns=FIELDS))

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

def github_read_registrations():
    url="https://api.github.com/repos/"+REPO+"/contents/"+DATA_PATH+"?ref=main"
    token=secret("GITHUB_TOKEN").strip()
    headers={"Accept":"application/vnd.github+json","User-Agent":"ConvergeX-Streamlit","X-GitHub-Api-Version":"2022-11-28"}
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=20) as r:
        obj=json.loads(r.read().decode("utf-8"))
    raw=base64.b64decode(obj.get("content","").replace("\n",""))
    df=normalize(pd.read_csv(io.BytesIO(raw),dtype=str).fillna("")) if raw.strip() else normalize(pd.DataFrame())
    return df,obj.get("sha","")

def github_write_registrations(df,message="Update ConvergeX registrations"):
    token=secret("GITHUB_TOKEN").strip()
    if not token:
        raise RuntimeError("GitHub storage is not configured.")
    clean=normalize(df)
    current,sha=github_read_registrations()
    payload={
        "message":message,
        "content":base64.b64encode(clean.to_csv(index=False).encode("utf-8")).decode("ascii"),
        "branch":"main"
    }
    if sha: payload["sha"]=sha
    url="https://api.github.com/repos/"+REPO+"/contents/"+DATA_PATH
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"ConvergeX-Streamlit","X-GitHub-Api-Version":"2022-11-28"}
    req=urllib.request.Request(url,data=json.dumps(payload).encode("utf-8"),method="PUT",headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8",errors="replace")
        raise RuntimeError("GitHub write failed ("+str(e.code)+"). "+detail[:220])
    return True

def load_data(force_remote=False):
    try:
        df,_=github_read_registrations()
        st.session_state["registrations_master"]=df.copy()
        return df
    except Exception:
        if "registrations_master" in st.session_state:
            return normalize(st.session_state["registrations_master"].copy())
        return normalize(pd.DataFrame())

def csv_blob(df): return normalize(df).to_csv(index=False).encode("utf-8-sig")

def excel_blob(df):
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        normalize(df).to_excel(w,index=False,sheet_name="Registrations")
    return out.getvalue()

def save_data(df,message="Update ConvergeX registrations",deleted_ids=None):
    try:
        clean=normalize(df)
        github_write_registrations(clean,message)
        st.session_state["registrations_master"]=clean.copy()
        st.session_state["last_remote_saved"]=True
        st.session_state["last_remote_error"]=""
        return True
    except Exception as e:
        st.session_state["last_remote_saved"]=False
        st.session_state["last_remote_error"]=str(e)
        return False

def register(row):
    df=load_data(force_remote=True)
    email=str(row["email"]).strip().lower()
    if len(df) and any(df["email"].str.strip().str.lower()==email):
        raise ValueError("This email address is already registered.")
    merged=merge_records(df,pd.DataFrame([row]))
    if not save_data(merged,"New ConvergeX registration "+str(row["registration_id"])):
        raise RuntimeError("Registration could not be stored permanently. Please try again.")
    verify,_=github_read_registrations()
    if not any(verify["registration_id"].astype(str)==str(row["registration_id"])):
        raise RuntimeError("GitHub did not confirm the saved registration.")
    st.session_state["registrations_master"]=verify.copy()
    return True

def github_storage_health(verify_write=False):
    token=secret("GITHUB_TOKEN").strip()
    if not token:
        return False,"GitHub token is not configured."
    try:
        df,sha=github_read_registrations()
        if verify_write:
            github_write_registrations(df,"Verify ConvergeX registration storage")
        return True,""
    except Exception as e:
        return False,str(e)

def public_report_blob(df):
    out=BytesIO()
    public_cols=["name","designation","institution","country","role","theme","talk_title","profile"]
    x=normalize(df)[public_cols].copy()
    x.columns=["Name","Designation","Institution","Country","Role","Theme","Talk title","Profile"]
    sheet="Approved People"
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        x.to_excel(w,index=False,sheet_name=sheet)
        ws=w.sheets[sheet]
        ws.freeze_panes="A2"
        ws.auto_filter.ref=ws.dimensions
        widths={"A":28,"B":24,"C":38,"D":16,"E":24,"F":42,"G":42,"H":55}
        for col,width in widths.items():
            ws.column_dimensions[col].width=width
    return out.getvalue()

def github_read_programme():
    url="https://api.github.com/repos/"+REPO+"/contents/"+PROGRAMME_PATH+"?ref=main"
    token=secret("GITHUB_TOKEN").strip()
    headers={"Accept":"application/vnd.github+json","User-Agent":"ConvergeX-Streamlit","X-GitHub-Api-Version":"2022-11-28"}
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=20) as r:
        obj=json.loads(r.read().decode("utf-8"))
    raw=base64.b64decode(obj.get("content","").replace("\n",""))
    x=pd.read_csv(io.BytesIO(raw),dtype=str).fillna("") if raw.strip() else pd.DataFrame()
    for c in PROGRAMME_FIELDS:
        if c not in x.columns:x[c]=""
    return x[PROGRAMME_FIELDS],obj.get("sha","")

def load_programme():
    try:
        x,_=github_read_programme()
        return x
    except Exception:
        return pd.DataFrame(columns=PROGRAMME_FIELDS)

def save_programme(pdf):
    token=secret("GITHUB_TOKEN").strip()
    if not token: raise RuntimeError("GitHub storage is not configured.")
    x=pdf.copy().fillna("")
    for c in PROGRAMME_FIELDS:
        if c not in x.columns:x[c]=""
    x=x[PROGRAMME_FIELDS]
    _,sha=github_read_programme()
    payload={"message":"Update ConvergeX programme","content":base64.b64encode(x.to_csv(index=False).encode("utf-8")).decode("ascii"),"branch":"main"}
    if sha: payload["sha"]=sha
    url="https://api.github.com/repos/"+REPO+"/contents/"+PROGRAMME_PATH
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","Content-Type":"application/json","User-Agent":"ConvergeX-Streamlit","X-GitHub-Api-Version":"2022-11-28"}
    req=urllib.request.Request(url,data=json.dumps(payload).encode("utf-8"),method="PUT",headers=headers)
    with urllib.request.urlopen(req,timeout=25) as r:r.read()
    verify,_=github_read_programme()
    return len(verify)==len(x)

def admin_ok(u,p):
    au=secret("ADMIN_USERNAME","ramesh")
    ap=secret("ADMIN_PASSWORD")
    return bool(ap) and hmac.compare_digest(u,au) and hmac.compare_digest(p,ap)

def approved(df):
    df=normalize(df)
    return df[df.status.str.lower().eq("approved")].copy()

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

.becoming{position:relative;min-height:520px;overflow:hidden;border:1px solid rgba(255,255,255,.09);border-radius:32px;background:radial-gradient(circle at 50% 50%,rgba(80,228,255,.12),transparent 24%),linear-gradient(145deg,rgba(2,9,18,.98),rgba(7,26,43,.92));isolation:isolate}
.becoming:before{content:"";position:absolute;inset:-45%;background:conic-gradient(from 0deg,transparent,rgba(80,228,255,.08),transparent 25%,rgba(243,199,95,.07),transparent 55%);animation:genomeSpin 18s linear infinite;z-index:-2}
.becoming:after{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(80,228,255,.17) 1px,transparent 1px);background-size:30px 30px;mask-image:radial-gradient(circle at center,#000,transparent 78%);z-index:-1}
.genome-title{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:min(560px,72%);text-align:center;z-index:8}
.genome-title .eyebrow{font-size:.74rem;letter-spacing:.3em;color:var(--gold);font-weight:900}.genome-title h2{font-size:clamp(2rem,4vw,4.4rem);line-height:.95;margin:.55rem 0;background:linear-gradient(90deg,#fff,var(--cyan),var(--gold),#fff);background-size:240% auto;color:transparent;background-clip:text;-webkit-background-clip:text;animation:genomeText 6s linear infinite}.genome-title p{color:#b8cad9}
.helix{position:absolute;left:7%;right:7%;top:50%;height:150px;transform:translateY(-50%);opacity:.92}
.helix-line{position:absolute;left:0;right:0;top:74px;height:2px;background:linear-gradient(90deg,transparent,var(--cyan),var(--gold),var(--cyan),transparent);box-shadow:0 0 18px rgba(80,228,255,.55);animation:breatheLine 4s ease-in-out infinite}
.gene{position:absolute;width:12px;height:12px;border-radius:50%;background:var(--cyan);box-shadow:0 0 16px var(--cyan),0 0 34px rgba(80,228,255,.5);animation:geneTravel var(--dur) linear infinite;animation-delay:var(--delay)}
.gene:nth-child(even){background:var(--gold);box-shadow:0 0 16px var(--gold),0 0 34px rgba(243,199,95,.45);animation-direction:reverse}
.gene:after{content:"";position:absolute;width:1px;height:var(--stem);left:6px;top:6px;background:linear-gradient(var(--cyan),transparent);transform-origin:top;transform:rotate(var(--angle));opacity:.55}
.genome-stat{position:absolute;padding:10px 14px;border:1px solid rgba(255,255,255,.1);border-radius:16px;background:rgba(4,16,29,.72);backdrop-filter:blur(10px);font-size:.72rem;color:var(--muted);z-index:9}.genome-stat b{display:block;color:#fff;font-size:1.25rem}.gs1{left:4%;top:7%}.gs2{right:4%;top:7%}.gs3{left:4%;bottom:7%}.gs4{right:4%;bottom:7%}
@keyframes genomeSpin{to{transform:rotate(360deg)}}@keyframes genomeText{to{background-position:240% center}}@keyframes breatheLine{50%{filter:brightness(1.8);transform:scaleX(.94)}}@keyframes geneTravel{0%{left:-2%;transform:translateY(0) scale(.6);opacity:0}8%{opacity:1}25%{transform:translateY(-62px) scale(1)}50%{transform:translateY(0) scale(.75)}75%{transform:translateY(62px) scale(1)}92%{opacity:1}100%{left:102%;transform:translateY(0) scale(.6);opacity:0}}
@media(max-width:800px){.becoming{min-height:460px}.genome-title{width:80%}.genome-stat{font-size:.62rem;padding:8px 10px}.genome-stat b{font-size:1rem}}
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

heading("ConvergeX Living Genome","Every approved participant changes the structure of the conference.","becoming")
genome_people=len(pub)
genome_inst=int(pub.institution[pub.institution.str.strip()!=""].nunique()) if len(pub) else 0
genome_talks=int((pub.talk_title.str.strip()!="").sum()) if len(pub) else 0
genome_themes=sum(1 for t in THEMES if int((pub.theme==t).sum())>0)
gene_count=max(10,min(28,genome_people+10))
genes="".join(
    f'<i class="gene" style="--dur:{6+(i%7)}s;--delay:-{(i*0.73)%9:.2f}s;--stem:{32+(i%5)*12}px;--angle:{-65+(i%6)*26}deg"></i>'
    for i in range(gene_count)
)
st.markdown(f'''<div class="becoming">
<div class="genome-stat gs1"><b>{genome_people}</b>PEOPLE</div>
<div class="genome-stat gs2"><b>{genome_inst}</b>INSTITUTIONS</div>
<div class="genome-stat gs3"><b>{genome_themes}/{len(THEMES)}</b>PATHWAYS</div>
<div class="genome-stat gs4"><b>{genome_talks}</b>TALKS</div>
<div class="helix"><div class="helix-line"></div>{genes}</div>
<div class="genome-title"><div class="eyebrow">LIVING CONFERENCE GENOME</div><h2>CONVERGEX<br>IS BECOMING</h2><p>People enter. Connections form. The conference evolves.</p></div>
</div>''',unsafe_allow_html=True)

heading("Conclave Pulse","A live snapshot of the conference as participation grows.","experience")
pulse_themes=sum(1 for t in THEMES if int((pub.theme==t).sum())>0)
pulse_institutions=int(pub.institution[pub.institution.str.strip()!=""].nunique()) if len(pub) else 0
pulse_countries=int(pub.country[pub.country.str.strip()!=""].nunique()) if len(pub) else 0
pulse_roles=int(pub.role[pub.role.str.strip()!=""].nunique()) if len(pub) else 0
st.markdown(f'''<div class="cards">
<div class="card"><span class="badge">PEOPLE</span><h2>{len(pub)}</h2><p>approved participants</p></div>
<div class="card"><span class="badge">INSTITUTIONS</span><h2>{pulse_institutions}</h2><p>organizations represented</p></div>
<div class="card"><span class="badge">COUNTRIES</span><h2>{pulse_countries}</h2><p>countries represented</p></div>
<div class="card"><span class="badge">PATHWAYS</span><h2>{pulse_themes}/{len(THEMES)}</h2><p>active focus areas</p></div>
</div>''',unsafe_allow_html=True)

heading("Focus Areas","Explore the conference once; participant and speaker views below are generated from the same master record.")
short=["Strategy","AI & GenAI","DeepTech","Research & Start-ups","IP & Patents","Leadership"]
st.markdown('<div class="cards">'+"".join(f'<div class="card"><span class="badge">{i+1:02}</span><h3>{safe(a)}</h3><p>{safe(b)}</p></div>' for i,(a,b) in enumerate(zip(short,THEMES)))+'</div>',unsafe_allow_html=True)

heading("Conference Leadership")
st.markdown("""<div class="card"><span class="badge">CONCLAVE ORGANISER</span><div class="person">Ramesh Chandra Panda</div><p>Chairman & Chief Scientist, WEGROW · IPR Head of 12 Universities and 58 Engineering/Management/Law Colleges · Conclave Organiser · Editor of 7 Scopus-indexed journals</p></div>""",unsafe_allow_html=True)

heading("People","Browse organizer-approved participants without turning the main page into a long directory.","people")
keynote_roles=[x for x in ROLES if "keynote" in x.lower()]
invited_roles=[x for x in ROLES if "invited" in x.lower() and "keynote" not in x.lower()]
other_roles=[x for x in ROLES if x not in keynote_roles+invited_roles]
people_groups=[
    ("Keynotes",pub[pub.role.isin(keynote_roles)]),
    ("Invited Speakers",pub[pub.role.isin(invited_roles)]),
    ("Delegates & Participants",pub[pub.role.isin(other_roles)])
]
pc1,pc2,pc3=st.columns(3)
for col,(label,group) in zip([pc1,pc2,pc3],people_groups):
    with col:
        st.markdown(f'<div class="card"><span class="badge">{safe(label).upper()}</span><h2>{len(group)}</h2><p>approved records</p></div>',unsafe_allow_html=True)

@st.dialog("Approved People Directory",width="large")
def people_directory():
    category=st.selectbox("Category",["All approved people","Keynotes","Invited Speakers","Delegates & Participants"],key="people_directory_category")
    search=st.text_input("Search",placeholder="Name, institution, country, role or theme",key="people_directory_search")
    if category=="Keynotes": view=people_groups[0][1].copy()
    elif category=="Invited Speakers": view=people_groups[1][1].copy()
    elif category=="Delegates & Participants": view=people_groups[2][1].copy()
    else: view=pub.copy()
    q=search.strip().lower()
    if q and len(view):
        mask=view[["name","designation","institution","country","role","theme","talk_title"]].fillna("").astype(str).apply(lambda c:c.str.lower().str.contains(q,regex=False)).any(axis=1)
        view=view[mask]
    st.caption(f"{len(view)} approved people shown")
    show_cols=["name","designation","institution","country","role","theme","talk_title"]
    st.dataframe(view[show_cols],use_container_width=True,hide_index=True,height=430)
    st.download_button("Download directory report",public_report_blob(view),"ConvergeX_Approved_People.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

if st.button(f"Open People Directory · {len(pub)} approved",use_container_width=True,type="primary"):
    people_directory()
st.download_button("Download approved people report",public_report_blob(pub),"ConvergeX_Approved_People.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

heading("Conference Digital Twin","A live intelligence layer showing how approved people connect institutions, themes, roles and talks.","twin")
twin_people=pub.copy()
theme_counts={t:int((twin_people.theme==t).sum()) for t in THEMES}
inst_count=int(twin_people.institution[twin_people.institution.str.strip()!=""].nunique()) if len(twin_people) else 0
role_count=int(twin_people.role[twin_people.role.str.strip()!=""].nunique()) if len(twin_people) else 0
talk_count=int((twin_people.talk_title.str.strip()!="").sum()) if len(twin_people) else 0
active_themes=sum(1 for v in theme_counts.values() if v>0)
top_theme=max(theme_counts,key=theme_counts.get) if theme_counts and max(theme_counts.values(),default=0)>0 else "Awaiting approved registrations"
t1,t2,t3,t4=st.columns(4)
t1.metric("Approved people",len(twin_people))
t2.metric("Institutions",inst_count)
t3.metric("Active pathways",f"{active_themes}/{len(THEMES)}")
t4.metric("Connected talks",talk_count)
if len(twin_people):
    st.markdown("#### Theme signal")
    max_count=max(theme_counts.values(),default=1) or 1
    signal_html='<div class="card">'
    for theme in THEMES:
        n=theme_counts.get(theme,0); pct=max(2,int(100*n/max_count)) if n else 0
        signal_html+=f'<div style="display:grid;grid-template-columns:minmax(210px,2fr) 6fr 50px;gap:12px;align-items:center;margin:12px 0"><span>{safe(theme)}</span><div style="height:10px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden"><div style="width:{pct}%;height:100%;background:linear-gradient(90deg,var(--cyan),var(--gold));border-radius:99px"></div></div><b class="cyan">{n}</b></div>'
    st.markdown(signal_html+'</div>',unsafe_allow_html=True)
    st.caption("Largest represented theme: "+top_theme)

if twin_people.empty:
    st.info("The Digital Twin will activate automatically as the organizer approves registrations.")
else:
    twin_tabs=st.tabs(["Explore connections","Theme intelligence","Institution network"])
    with twin_tabs[0]:
        person_options=["All approved participants"]+sorted(twin_people["name"].tolist())
        who=st.selectbox("Explore a participant",person_options,key="twin_person")
        if who=="All approved participants":
            st.info("Select a participant to reveal their live connections across people, institutions, themes, and ideas.")
        else:
            r=twin_people[twin_people["name"]==who].iloc[0]
            a,b,c=st.columns(3)
            a.metric("Role",r.role);b.metric("Institution",r.institution or "—");c.metric("Theme",r.theme or "—")
            if r.talk_title: st.success("Connected talk: "+r.talk_title)
            related=twin_people[(twin_people.theme==r.theme)&(twin_people["name"]!=who)]
            if len(related): st.caption("Theme connections: "+", ".join(related["name"].tolist()))
            else: st.caption("No other approved participant currently shares this theme.")
    with twin_tabs[1]:
        intelligence=pd.DataFrame({"Theme":THEMES,"Approved people":[theme_counts.get(t,0) for t in THEMES]}).sort_values("Approved people",ascending=False)
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
        visible=visible.copy()
        visible["date"]=visible["date"].replace("",EVENT_DATE.strftime("%Y-%m-%d"))
        for d,day in visible.groupby("date",sort=False):
            try: day_label=datetime.strptime(str(d),"%Y-%m-%d").strftime("%A · %d %B %Y")
            except Exception: day_label=str(d)
            st.markdown(f'<div class="badge">{safe(day_label)}</div>',unsafe_allow_html=True)
            html='<div class="timeline">'
            for _,r in day.iterrows():
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
        st.warning("Registration was not committed to the conference master.")

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
    storage_ok,storage_error=github_storage_health(verify_write=True)
    if not storage_ok:
        st.error("Registration is temporarily unavailable because permanent GitHub storage cannot write. Please contact the organizer.")
        submitted=False
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
        except Exception:
            st.error("Registration could not be completed. Please try again or contact the organizer.")

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
            storage_ok,storage_error=github_storage_health(verify_write=True)
            if storage_ok:
                st.success("Registration storage: GitHub read/write verified.")
            else:
                st.error("Registration storage cannot write to GitHub. Check GITHUB_TOKEN → ConvergeX → Contents: Read and write.")
                if storage_error:
                    st.caption("Storage check: "+storage_error[:260])
            regtab,approvedtab,progtab,optiontab=st.tabs(["Pending / Review","Approved","Programme editor","Registration options"])
            with regtab:
                st.caption("Review new registrations here. Set Publication status to Approved and save; approved records move to the Approved tab.")
                st.caption("GitHub is the permanent registration master. Excel backup remains available for offline records.")
                review=load_data().copy()
                review=normalize(review)
                review=review[~review["status"].str.lower().eq("approved")].copy()
                review["delete"]=False
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
                            "delete":st.column_config.CheckboxColumn("Delete permanently",help="Last column. Select only if this registration should be permanently removed."),
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
                                deleted_ids=review.loc[review["delete"].fillna(False).astype(bool),"registration_id"].astype(str).tolist()
                                kept=review[~review["delete"].fillna(False).astype(bool)].drop(columns=["delete"],errors="ignore")
                                invalid=kept[(kept["registration_id"].fillna("").str.strip()=="") | (kept["name"].fillna("").str.strip()=="") | (kept["email"].fillna("").str.strip()=="")]
                                if len(invalid):
                                    st.error("A registration cannot be saved without Registration ID, Name and Email.")
                                else:
                                    existing_approved=approved(load_data())
                                    combined=merge_records(existing_approved,normalize(kept))
                                    remote_saved=save_data(combined,"Update registration master",deleted_ids=deleted_ids)
                                    if not remote_saved:
                                        raise RuntimeError(st.session_state.get("last_remote_error","Repository write did not complete."))
                                    confirmed,_=github_read_registrations()
                                    st.session_state["registrations_master"]=confirmed.copy()
                                    st.success("Changes saved and verified in GitHub. Approved registrations are now published.")
                                    st.rerun()
                            except Exception as e:st.error("Could not save the registration sheet. "+str(e))
                    with c2:
                        st.download_button("Download Excel backup",excel_blob(review),"ConvergeX_Registrations.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                    st.markdown("#### Backup & restore")
                    upload=st.file_uploader("Upload registration backup",type=["xlsx","csv"],key="registration_backup_upload",help="Uploaded rows are merged by Registration ID. Existing populated data is preserved unless the uploaded file provides a replacement value.")
                    if upload is not None:
                        if st.button("Validate & merge backup",use_container_width=True):
                            try:
                                if upload.name.lower().endswith(".xlsx"):
                                    incoming=pd.read_excel(upload,dtype=str).fillna("")
                                else:
                                    incoming=pd.read_csv(upload,dtype=str).fillna("")
                                missing_cols=[c for c in ["registration_id","name","email"] if c not in incoming.columns]
                                if missing_cols: raise ValueError("Backup is missing required columns: "+", ".join(missing_cols))
                                incoming=normalize(incoming)
                                if incoming.empty: raise ValueError("No valid registrations were found in the uploaded backup.")
                                merged=merge_records(df,incoming)
                                remote_saved=save_data(merged,"Merge registration backup")
                                if not remote_saved: raise RuntimeError(st.session_state.get("last_remote_error","Repository write did not complete."))
                                st.success(f"Backup merged successfully. {len(incoming)} valid uploaded registration(s) processed.")
                                st.rerun()
                            except Exception as e:
                                st.error("Backup was not imported. "+str(e))
                    st.caption("Approve publishes a row; Hidden removes it from the public site without deleting it. For a permanent removal, tick Delete in that row and then Save all changes.")
            with approvedtab:
                st.caption("Approved registrations are published across People, Digital Twin and conference counts. Edit them here and save.")
                approved_review=approved(load_data()).copy()
                if approved_review.empty:
                    st.info("No approved registrations yet.")
                else:
                    approved_review["delete"]=False
                    approved_edit=st.data_editor(
                        approved_review,
                        num_rows="fixed",
                        use_container_width=True,
                        hide_index=True,
                        key="approved_registration_sheet",
                        column_config={
                            "delete":st.column_config.CheckboxColumn("Delete permanently",help="Last column. Select only if this approved registration should be permanently removed."),
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
                            "status":st.column_config.SelectboxColumn("Publication status",options=["Approved","Pending","Hidden","Rejected"],required=True),
                            "payment":st.column_config.SelectboxColumn("Payment",options=["Pending","Paid","Waived","Not applicable"]),
                            "accommodation":st.column_config.SelectboxColumn("Accommodation",options=["","Pending","Confirmed","Not required"]),
                            "certificate":st.column_config.SelectboxColumn("Certificate",options=["","Pending","Ready","Issued"])
                        }
                    )
                    if st.button("Save approved changes",type="primary",use_container_width=True):
                        try:
                            delete_ids=set(approved_edit.loc[approved_edit["delete"].fillna(False).astype(bool),"registration_id"].astype(str))
                            changed=normalize(approved_edit[~approved_edit["delete"].fillna(False).astype(bool)].drop(columns=["delete"],errors="ignore"))
                            master=load_data()
                            master=master[~master["registration_id"].isin(set(approved_review["registration_id"].astype(str)))].copy()
                            merged=merge_records(master,changed)
                            if not save_data(merged,deleted_ids=list(delete_ids)):
                                raise RuntimeError(st.session_state.get("last_remote_error","Save failed."))
                            confirmed,_=github_read_registrations()
                            st.session_state["registrations_master"]=confirmed.copy()
                            st.success("Approved registrations updated and verified in GitHub.")
                            st.rerun()
                        except Exception as e:
                            st.error("Could not save approved registrations. "+str(e))
                st.caption("Approved records remain editable. Changing status away from Approved removes them from public views and returns them to review/private status.")

            with progtab:
                st.caption("Add the programme hour by hour. Use status Published to make a row visible publicly; Draft remains private.")
                ped=programme.copy()
                if ped.empty: ped=pd.DataFrame([{"date":EVENT_DATE.strftime("%Y-%m-%d"),"time":"","title":"","description":"","status":"Draft"}],columns=PROGRAMME_FIELDS)
                ped=st.data_editor(ped,num_rows="dynamic",use_container_width=True,hide_index=True,column_config={"date":st.column_config.TextColumn("Date",help="YYYY-MM-DD, for example 2026-10-25"),"time":st.column_config.TextColumn("Time",help="Example: 09:30 AM"),"title":st.column_config.TextColumn("Session title"),"description":st.column_config.TextColumn("Description"),"status":st.column_config.SelectboxColumn("Status",options=["Draft","Published"])},key="programme_editor")
                if st.button("Save programme",type="primary",use_container_width=True):
                    try:
                        if save_programme(ped): st.success("Programme saved permanently to GitHub. Published rows will appear publicly after refresh.")
                        else: st.error("Programme save could not be verified.")
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
