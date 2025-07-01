import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import os
import tempfile
import time
import pygame
import atexit
from openai import OpenAI

client = OpenAI()

st.set_page_config(page_title="Trusted Advisor AI", page_icon="🎙️")
st.image("https://via.placeholder.com/600x100.png?text=Trusted+Advisor+AI", use_column_width=True)
st.title("🎙️ AI Gesprekstraining - The Trusted Advisor")
st.markdown("""
Welkom bij de AI-gesprekscoach gebaseerd op de Trusted Advisor-principes.
Gebruik je microfoon om een gesprek te voeren met een AI-klant en ontvang directe feedback op jouw communicatie.
""")

st.sidebar.title("🔧 Instellingen")
st.sidebar.markdown("""
**Stappenplan:**
1. Beschrijf de klant
2. Start het gesprek
3. Luister naar de reactie
4. Beëindig het gesprek
""")

recognizer = sr.Recognizer()
energy_threshold = st.sidebar.slider("🎚️ Microfoongevoeligheid", 1000, 4000, 2000)
recognizer.energy_threshold = energy_threshold
opname_timeout = st.sidebar.slider("⏱️ Stilte-timeout (seconden)", 1, 30, 15)
audio_pad = os.path.join(tempfile.gettempdir(), "ai_reactie.mp3")

def opruimen_audio():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        time.sleep(0.5)
        for bestand in os.listdir(tempfile.gettempdir()):
            if bestand.endswith(('.mp3', '.wav', '.tmp')):
                os.remove(os.path.join(tempfile.gettempdir(), bestand))
    except: pass
atexit.register(opruimen_audio)

for key in ["klant_beschrijving", "gesprekshistorie", "fase"]:
    if key not in st.session_state:
        st.session_state[key] = ""

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("1. 🎤 Beschrijf de klant"):
        st.session_state["fase"] = "klant"
with col2:
    if st.button("2. 🎤 Start input"):
        st.session_state["fase"] = "input"
with col3:
    if st.button("3. 🛑 Stop gesprek"):
        st.session_state["fase"] = "einde"

def start_opname():
    st.info("🎙️ Microfoon geactiveerd...")
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio_data = recognizer.listen(source, timeout=opname_timeout, phrase_time_limit=60)
    try:
        tekst = recognizer.recognize_google(audio_data, language="nl-NL")
        return tekst
    except sr.UnknownValueError:
        st.error("🛑 Spraak niet herkend.")
    except sr.RequestError as e:
        st.error(f"🛑 Spraakservice fout: {e}")
    return ""

if st.session_state["fase"] == "klant":
    st.subheader("👤 Klantbeschrijving")
    tekst = start_opname()
    st.session_state["klant_beschrijving"] = tekst
    st.write(tekst)
    st.session_state["fase"] = ""

elif st.session_state["fase"] == "input":
    st.subheader("💬 Gesprek")
    tekst = start_opname()
    st.session_state["gesprekshistorie"] += f"\nJij: {tekst}"
    st.write(tekst)

    with st.spinner("🤖 AI denkt na over een reactie..."):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Je speelt een klant in een professioneel gesprek. Reageer realistisch en professioneel. De klantbeschrijving is: '{st.session_state['klant_beschrijving']}'"},
                {"role": "user", "content": st.session_state["gesprekshistorie"]}
            ]
        )
    antwoord = response.choices[0].message.content
    st.session_state["gesprekshistorie"] += f"\nKlant: {antwoord}"

    try:
        tts = gTTS(text=antwoord, lang='nl')
        tts.save(audio_pad)
        pygame.mixer.init()
        pygame.mixer.music.load(audio_pad)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        st.warning(f"🔇 Audio kon niet worden afgespeeld: {e}")

    st.success("✅ Klant heeft gereageerd.")
    st.write(antwoord)
    st.session_state["fase"] = ""

elif st.session_state["fase"] == "einde":
    st.subheader("📋 Feedback op jouw gesprek")
    with st.spinner("🧠 AI analyseert je gesprek..."):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Je bent een coach die feedback geeft op een gesprek volgens de principes van The Trusted Advisor: geloofwaardigheid, betrouwbaarheid, intimiteit en egogerichtheid."},
                {"role": "user", "content": st.session_state["gesprekshistorie"]}
            ]
        )
    feedback = response.choices[0].message.content
    st.write(feedback)
    st.success("✅ Feedback gegenereerd.")
    st.session_state["fase"] = ""
