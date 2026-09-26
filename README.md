# ConvergeX

**ConvergeX — Intelligent Conference Experience Platform**

First deployment: **Strategic Technomanagerial DeepTech Innovation Conclave 2026**  
**25 October 2026 · The Sanihara Hotel & Resort · Wayanad, Kerala, India**

ConvergeX is a reusable, configuration-oriented conference experience platform built with Streamlit and a custom React-inspired visual system.

## Current prototype

- Cinematic dark navy / gold / cyan conference interface
- Living Constellation concept
- Event overview and countdown
- Conference themes
- Featured leadership / speaker cards
- Visual programme timeline
- Venue section
- Registration prototype with generated registration ID
- Responsive layout
- Reusable conference architecture concept
- No public storage of participant personal information

## Run locally

~~~bash
pip install -r requirements.txt
streamlit run streamlit_app.py
~~~

## Deploy on Streamlit Community Cloud

1. Open Streamlit Community Cloud.
2. Choose **Create app**.
3. Select repository `Arithmetic-Power-Geometry/ConvergeX`.
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Deploy.

## Event leadership

**Ramesh Chandra Panda**  
Chairman & Chief Scientist, WEGROW; IPR Head of 12 Universities and 58 Engineering/Management/Law Colleges; Conclave Organiser; Editor of 7 Scopus-indexed journals.

## Platform design & development

**Dr. Mohammad Amir Khusru Akhtar**

## Privacy architecture

The repository should contain application source, public event content, programme data and public speaker information. Production registration records containing email addresses, phone numbers, travel details or other personal information should be stored in a private authenticated datastore rather than committed to public Git history.

## Roadmap

- Data-driven `conference.yaml`
- Speaker JSON and programme JSON
- Admin dashboard
- QR registration cards
- Registration status portal
- Private database integration
- Certificate generation
- Event Digital Twin connecting people, ideas, sessions, technologies and organizations
