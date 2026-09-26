import streamlit as st
from datetime import datetime
import json, uuid, csv, io, base64, urllib.request, urllib.error

st.set_page_config(page_title="ConvergeX", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")

EVENT_DATE = datetime(2026,10,25,9,0,0)
REPO = "Arithmetic-Power-Geometry/ConvergeX"
DATA_PATH = "data/registrations.csv"
FIELDS = ["registration_id","timestamp","name","designation","institution","email","mobile","country","category","theme","bio","status"]

def _token():
    try: return st.secrets["GITHUB_TOKEN"]
    except Exception: return ""

def github_request(method, path, payload=None):
    token=_token()
    if not token: raise RuntimeError("Permanent registration is not configured yet. Add GITHUB_TOKEN in Streamlit app Secrets.")
    url="https://api.github.com/repos/"+REPO+"/"+path
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ConvergeX"})
    with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read().decode())

def read_rows():
    try:
        raw=urllib.request.urlopen("https://raw.githubusercontent.com/"+REPO+"/main/"+DATA_PATH+"?v="+str(uuid.uuid4()),timeout=10).read().decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(raw)))
    except Exception: return []

def write_rows(rows, message):
    token=_token()
    if not token: raise RuntimeError("Permanent registration is not configured yet. Add GITHUB_TOKEN in Streamlit app Secrets.")
    try:
        meta=github_request("GET","contents/"+DATA_PATH+"?ref=main")
        sha=meta.get("sha")
    except Exception:
        sha=None
    out=io.StringIO(); w=csv.DictWriter(out,fieldnames=FIELDS); w.writeheader()
    for row in rows: w.writerow({k:row.get(k,"") for k in FIELDS})
    payload={"message":message,"content":base64.b64encode(out.getvalue().encode()).decode(),"branch":"main"}
    if sha: payload["sha"]=sha
    return github_request("PUT","contents/"+DATA_PATH,payload)

def permanent_register(row):
    for attempt in range(3):
        rows=read_rows()
        if any(x.get("email","").lower()==row["email"].lower() for x in rows):
            raise ValueError("This email is already registered.")
        try:
            write_rows(rows+[row],"Register "+row["registration_id"])
            return
        except urllib.error.HTTPError as e:
            if e.code==409 and attempt<2: continue
            raise

CSS = r"""
<style>
:root{
 --bg:#06111f; --panel:#0b1b2e; --glass:rgba(255,255,255,.07);
 --gold:#f1c75b; --cyan:#4fe4ff; --text:#f7fbff; --muted:#a7b7c8;
}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.stApp{
 background:
 radial-gradient(circle at 20% 15%, rgba(79,228,255,.13), transparent 25%),
 radial-gradient(circle at 82% 18%, rgba(241,199,91,.13), transparent 22%),
 linear-gradient(135deg,#040b14 0%,#071728 48%,#05111d 100%);
 color:var(--text);
}
.block-container{padding-top:1.1rem;max-width:1380px}
#MainMenu,footer,header{visibility:hidden}
.nav{position:sticky;top:0;z-index:99;display:flex;align-items:center;justify-content:space-between;
background:rgba(4,11,20,.72);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.08);
border-radius:18px;padding:12px 18px;margin-bottom:18px}
.brand{font-weight:900;letter-spacing:.04em}.brand span{color:var(--cyan)}
.navlinks{font-size:.9rem;color:#c8d7e5;word-spacing:16px}
.hero{min-height:650px;border-radius:34px;padding:70px 64px;position:relative;overflow:hidden;
border:1px solid rgba(255,255,255,.10);background:
linear-gradient(110deg,rgba(3,11,20,.96) 0%,rgba(4,16,31,.88) 48%,rgba(4,20,33,.56) 100%),
radial-gradient(circle at 80% 55%,rgba(79,228,255,.20),transparent 18%);}
.hero:before,.hero:after{content:"";position:absolute;border:1px solid rgba(79,228,255,.18);border-radius:50%}
.hero:before{width:540px;height:540px;right:-130px;top:40px;box-shadow:0 0 70px rgba(79,228,255,.08)}
.hero:after{width:330px;height:330px;right:-25px;top:145px;border-color:rgba(241,199,91,.25)}
.kicker{color:var(--gold);font-weight:800;letter-spacing:.18em;text-transform:uppercase;font-size:.82rem}
.hero h1{font-size:clamp(3rem,6vw,6.4rem);line-height:.92;margin:.5rem 0 1rem;max-width:900px}
.hero h1 .cyan{color:var(--cyan)}.hero h1 .gold{color:var(--gold)}
.sub{font-size:1.15rem;color:#d3dfeb;max-width:760px;line-height:1.6}
.pills{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.pill{border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);padding:9px 13px;border-radius:999px;color:#dbe8f5}
.cta{display:inline-block;margin-top:28px;margin-right:12px;padding:13px 20px;border-radius:13px;font-weight:800;text-decoration:none}
.cta.primary{background:linear-gradient(90deg,var(--gold),#ffe7a6);color:#08111d}
.cta.ghost{border:1px solid rgba(255,255,255,.18);color:#fff}
.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:18px}
.metric{background:var(--glass);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:18px;text-align:center}
.metric b{font-size:1.7rem;color:var(--cyan)}.metric small{display:block;color:var(--muted);margin-top:3px}
.section-title{font-size:2.1rem;font-weight:900;margin:2.2rem 0 .4rem}.section-sub{color:var(--muted);margin-bottom:1.2rem}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border:1px solid rgba(255,255,255,.09);border-radius:22px;padding:22px;min-height:175px}
.card h3{margin:.2rem 0 .6rem}.card p{color:#b9c9d8;line-height:1.55}.icon{font-size:1.6rem}
.constellation{position:relative;height:520px;border-radius:28px;border:1px solid rgba(255,255,255,.08);overflow:hidden;
background:radial-gradient(circle at center,rgba(79,228,255,.11),transparent 35%),rgba(255,255,255,.025)}
.center-node,.node{position:absolute;border-radius:50%;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:800}
.center-node{width:160px;height:160px;left:calc(50% - 80px);top:180px;background:radial-gradient(circle,#163b5a,#081523);
border:1px solid var(--gold);box-shadow:0 0 45px rgba(241,199,91,.18)}
.node{width:110px;height:110px;background:rgba(6,25,42,.92);border:1px solid rgba(79,228,255,.45);box-shadow:0 0 24px rgba(79,228,255,.08);font-size:.9rem}
.n1{left:11%;top:65px}.n2{left:31%;top:25px}.n3{right:31%;top:25px}.n4{right:11%;top:65px}.n5{left:20%;bottom:40px}.n6{right:20%;bottom:40px}
.line{position:absolute;height:1px;background:linear-gradient(90deg,transparent,rgba(79,228,255,.33),transparent);transform-origin:left center}
.speaker{display:flex;gap:16px;align-items:center}.avatar{width:72px;height:72px;border-radius:18px;background:linear-gradient(135deg,#12324f,#0a1726);display:flex;align-items:center;justify-content:center;font-size:1.7rem;border:1px solid rgba(241,199,91,.35)}
.timeline{border-left:2px solid rgba(79,228,255,.25);padding-left:22px}.slot{padding:13px 0 19px;position:relative}.slot:before{content:"";width:11px;height:11px;border-radius:50%;background:var(--gold);position:absolute;left:-28px;top:20px}.slot b{color:var(--cyan)}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:rgba(241,199,91,.12);color:var(--gold);font-size:.75rem;font-weight:800}
.footer{margin:2.4rem 0 .5rem;padding:24px;border-top:1px solid rgba(255,255,255,.08);color:#8ca0b4;text-align:center}
@media(max-width:900px){.metric-grid,.grid3{grid-template-columns:1fr}.hero{padding:42px 24px;min-height:auto}.navlinks{display:none}.constellation{height:620px}.n1{left:4%;top:80px}.n2{left:55%;top:38px}.n3{left:5%;top:420px}.n4{right:4%;top:420px}.n5{left:4%;bottom:20px}.n6{right:4%;bottom:20px}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def nav():
    st.markdown('<div class="nav"><div class="brand">Converge<span>X</span></div><div class="navlinks">HOME EXPERIENCE SPEAKERS PROGRAMME THEMES AWARDS VENUE REGISTER</div><div class="badge">2026</div></div>', unsafe_allow_html=True)

def hero():
    now=datetime.now()
    d=max(EVENT_DATE-now, datetime.min-now)
    days=max((EVENT_DATE-now).days,0)
    st.markdown(f'''
    <section class="hero">
      <div class="kicker">ConvergeX · Intelligent Conference Experience Platform</div>
      <h1>STRATEGIC<br><span class="gold">TECHNOMANAGERIAL</span><br><span class="cyan">DEEPTECH INNOVATION</span><br>CONCLAVE 2026</h1>
      <div class="sub">Where Strategy Meets Innovation to Shape Tomorrow.<br><b>25 October 2026 · The Sanihara Hotel & Resort · Wayanad, Kerala, India</b></div>
      <div class="pills"><span class="pill">Artificial Intelligence</span><span class="pill">DeepTech</span><span class="pill">Research</span><span class="pill">Entrepreneurship</span><span class="pill">Intellectual Property</span><span class="pill">Leadership</span></div>
      <a class="cta primary" href="#register">REGISTER NOW</a><a class="cta ghost" href="#experience">EXPLORE CONCLAVE</a>
      <div class="metric-grid"><div class="metric"><b>{days}</b><small>Days to Conclave</small></div><div class="metric"><b>10</b><small>Featured Speakers</small></div><div class="metric"><b>6</b><small>Core Themes</small></div><div class="metric"><b>1</b><small>Immersive Experience</small></div></div>
    </section>''', unsafe_allow_html=True)

def section_title(title, subtitle, anchor=None):
    if anchor: st.markdown(f'<div id="{anchor}"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div><div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)

nav(); hero()
section_title("The ConvergeX Experience","A conference interface designed as a living network of people, ideas, technologies and opportunity.","experience")
st.markdown('''<div class="constellation">
<div class="center-node">CONCLAVE<br>2026</div>
<div class="node n1">AI</div><div class="node n2">DeepTech</div><div class="node n3">Research</div>
<div class="node n4">Entrepreneurship</div><div class="node n5">IP Strategy</div><div class="node n6">Leadership</div>
</div>''',unsafe_allow_html=True)

section_title("Why Attend","Built for meaningful exchange rather than passive attendance.")
st.markdown('''<div class="grid3">
<div class="card"><div class="icon">✦</div><h3>Frontier Ideas</h3><p>Explore AI, generative AI, emerging technologies, research translation and strategic technology management.</p></div>
<div class="card"><div class="icon">⌘</div><h3>Innovation Networks</h3><p>Connect academicians, researchers, innovators, entrepreneurs, technocrats and industry professionals.</p></div>
<div class="card"><div class="icon">◇</div><h3>IP & Commercialization</h3><p>Discuss patent strategy, technology commercialization, innovation ecosystems and industry collaboration.</p></div>
</div>''',unsafe_allow_html=True)

section_title("Featured Leadership","Conference leadership and speaker profiles can be expanded from data files.","speakers")
st.markdown('''<div class="grid3">
<div class="card"><div class="speaker"><div class="avatar">RP</div><div><span class="badge">Conclave Organiser</span><h3>Ramesh Chandra Panda</h3></div></div><p>Chairman & Chief Scientist, WEGROW; IPR Head of 12 Universities and 58 Engineering/Management/Law Colleges; Conclave Organiser; Editor of 7 Scopus-indexed journals.</p></div>
<div class="card"><div class="speaker"><div class="avatar">🎙</div><div><span class="badge">Keynote</span><h3>Speaker Profile</h3></div></div><p>Add confirmed keynote speakers, profile photographs, affiliations, talk titles and abstracts from the data layer.</p></div>
<div class="card"><div class="speaker"><div class="avatar">＋</div><div><span class="badge">Dynamic</span><h3>More Speakers</h3></div></div><p>The platform is reusable: update a JSON file and the speaker cards, programme links and theme graph can change automatically.</p></div>
</div>''',unsafe_allow_html=True)

section_title("Programme","A visual event journey. Replace placeholders as sessions are finalized.","programme")
st.markdown('''<div class="timeline">
<div class="slot"><b>08:30</b><h3>Registration & Welcome</h3><p>Arrival, delegate check-in and networking.</p></div>
<div class="slot"><b>09:30</b><h3>Opening Plenary</h3><p>Strategic technology, innovation and the future of DeepTech ecosystems.</p></div>
<div class="slot"><b>11:00</b><h3>AI & Generative AI</h3><p>Research, applications, governance and commercialization.</p></div>
<div class="slot"><b>14:00</b><h3>IP, Patents & Technology Strategy</h3><p>Patent inventive steps, intellectual property strategy and technology transfer.</p></div>
<div class="slot"><b>16:00</b><h3>Leadership, Start-ups & Collaboration</h3><p>Future-ready leadership and interdisciplinary innovation networks.</p></div>
</div>''',unsafe_allow_html=True)

section_title("Conference Themes","Six connected pathways through the programme.","themes")
themes=[
("Strategic Technology & Innovation Management","Align technology portfolios with institutional and industrial strategy."),
("Artificial Intelligence & Generative AI","From foundation models to responsible deployment and new research opportunities."),
("DeepTech & Emerging Technologies","Scientific and engineering advances with transformative commercialization potential."),
("Research, Entrepreneurship & Start-ups","Translation pathways from research insight to scalable ventures."),
("Intellectual Property & Patent Strategy","Inventive step, portfolio strategy, protection and commercialization."),
("Future-Ready Leadership & Sustainability","Leadership approaches for complex, technology-intensive futures.")]
cols=st.columns(3)
for i,(a,b) in enumerate(themes):
    with cols[i%3]:
        st.markdown(f'<div class="card"><span class="badge">0{i+1}</span><h3>{a}</h3><p>{b}</p></div>',unsafe_allow_html=True)

section_title("Venue","Wayanad provides a distinctive setting for focused exchange and collaboration.","venue")
st.markdown('''<div class="grid3">
<div class="card"><span class="badge">VENUE</span><h3>The Sanihara Hotel & Resort</h3><p>Wayanad, Kerala, India</p></div>
<div class="card"><span class="badge">DATE</span><h3>25 October 2026</h3><p>One immersive day of strategy, science, innovation and networking.</p></div>
<div class="card"><span class="badge">EXPERIENCE</span><h3>Conference + Destination</h3><p>Venue, travel guidance, accommodation and local experience modules can be published from the platform.</p></div>
</div>''',unsafe_allow_html=True)

section_title("Register","Complete your registration. A successful submission is permanently recorded in the conference master dataset.","register")
with st.form("registration_form", clear_on_submit=False):
    c1,c2=st.columns(2)
    with c1:
        name=st.text_input("Full name *")
        designation=st.text_input("Designation")
        institution=st.text_input("Institution / Organization *")
        email=st.text_input("Email *")
    with c2:
        phone=st.text_input("Mobile")
        country=st.text_input("Country", value="India")
        category=st.selectbox("Participation type",["Delegate","Keynote Speaker","Invited Speaker","Researcher","Industry Professional","Entrepreneur","Student","Other"])
        theme=st.selectbox("Primary interest",["Artificial Intelligence & Generative AI","DeepTech & Emerging Technologies","Strategic Technology Management","Research & Entrepreneurship","Intellectual Property & Patent Strategy","Leadership & Sustainability"])
    bio=st.text_area("Professional profile / note", height=100)
    consent=st.checkbox("I confirm that the information provided is correct and may be used for conference administration.")
    submitted=st.form_submit_button("Complete Registration", use_container_width=True)
    if submitted:
        if not name.strip() or not institution.strip() or not email.strip() or "@" not in email or not consent:
            st.error("Please complete the required fields, enter a valid email, and confirm consent.")
        else:
            reg=f"STDI-2026-{uuid.uuid4().hex[:6].upper()}"
            row={"registration_id":reg,"timestamp":datetime.now().isoformat(timespec="seconds"),"name":name.strip(),"designation":designation.strip(),"institution":institution.strip(),"email":email.strip(),"mobile":phone.strip(),"country":country.strip(),"category":category,"theme":theme,"bio":bio.strip(),"status":"Registered"}
            try:
                permanent_register(row)
                st.success(f"Registration complete. Your permanent Registration ID is {reg}.")
                st.caption("Your registration has been saved to the conference master dataset.")
            except ValueError as e: st.warning(str(e))
            except Exception as e: st.error(str(e))

section_title("Platform Architecture","ConvergeX is reusable beyond this conference.")
st.markdown('''<div class="grid3">
<div class="card"><h3>Config-driven</h3><p>Event title, venue, themes, speakers and programme can be separated from the interface.</p></div>
<div class="card"><h3>Streamlit-powered</h3><p>Python application logic with a custom React-inspired visual language and interactive forms.</p></div>
<div class="card"><h3>Digital Twin Ready</h3><p>Future versions can connect people, ideas, sessions, technologies and organizations in an explorable graph.</p></div>
</div>''',unsafe_allow_html=True)

st.markdown('''<div class="footer"><b>ConvergeX — Intelligent Conference Experience Platform</b><br>
Strategic Technomanagerial DeepTech Innovation Conclave 2026 · Wayanad, Kerala, India<br><br>
Conference leadership: Ramesh Chandra Panda · Platform design & development: Dr. Mohammad Amir Khusru Akhtar<br>
<small>Registrations are permanently maintained in the conference master dataset. Administrative credentials are kept outside the public source code.</small></div>''',unsafe_allow_html=True)
