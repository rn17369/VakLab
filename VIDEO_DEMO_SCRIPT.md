# Vaklab: 3-Minute Video Demo Script

## 🎬 Total Runtime: 3 minutes

---

## INTRO (0:00 - 0:25) — 25 seconds

**[Screen: Title card with Vaklab logo]**

> "What if no one ever missed a life-saving screening simply because they forgot, felt overwhelmed, or didn't understand their benefits?"

**[Screen: Statistics overlay]**

> "Breast cancer is one of the leading causes of cancer-related deaths among women. Yet early detection through mammogram screenings can reduce mortality by up to 40%."

**[Screen: Show the problem]**

> "Thousands of Medicare members miss these FREE screenings every year — not because they don't care, but because of missed reminders, confusion about coverage, or fear of the unknown."

**[Screen: Vaklab title reveal]**

> "That's why I built **Vaklab** — an AI-powered voice agent that proactively reaches out to Medicare members with empathy, clarity, and care."

---

## ARCHITECTURE DEMO (0:25 - 1:00) — 35 seconds

**[Screen: Architecture diagram]**

> "Let me show you how Vaklab works under the hood."

**[Point to each component as you explain]**

> "When a call is initiated, **Twilio** handles the telephony. The audio stream flows through a real-time **Pipecat pipeline** — a powerful framework for voice AI."

**[Highlight STT → LLM → TTS flow]**

> "**Google Speech-to-Text** transcribes the caller's voice. **Gemini 2.5 Flash** — Google's latest LLM — generates intelligent, empathetic responses. And **Google Text-to-Speech** delivers natural voice output."

**[Show the UI dashboard]**

> "Everything happens in real-time. You can watch the conversation unfold live on our dashboard — seeing exactly what Rebecca, our AI agent, says and what the member responds."

---

## LIVE DEMO (1:00 - 2:00) — 60 seconds

**[Screen: Terminal + UI Dashboard side by side]**

> "Let's make a real call. I'll trigger an outbound call to a test number."

**[Run: `curl -X POST http://localhost:8000/twilio/outbound-call`]**

> "Watch the UI — you'll see the call start and Rebecca begin speaking."

**[Show UI as Rebecca speaks]**

> "Hi! This is Rebecca calling from Vaklab about your Medicare benefits. I have some great news for you!"

**[Show customer responding]**

> "See how the transcription appears in real-time, perfectly synced with the audio."

**[Demo conversation flow]**

> "Rebecca walks through a natural conversation flow — verifying the member's zip code, explaining the free mammogram benefit, addressing any concerns..."

**[Show email being sent - if member enrolls]**

> "When the member expresses interest, Rebecca sends a personalized enrollment email — all automatically, all in real-time."

**[Show call ending gracefully]**

> "And when the call ends, Rebecca thanks them warmly and the dashboard updates to show 'Call Complete.'"

---

## EVALUATION FRAMEWORK (2:00 - 2:35) — 35 seconds

**[Screen: Evaluation diagram + CLI]**

> "Building an AI agent is one thing — but how do you know it actually works? That's where our evaluation framework comes in."

**[Show evaluation scenarios]**

> "We test Vaklab against 5 different scenarios using Google ADK's User Simulation — happy path enrollments, users asking about pain, busy users, cost questions, and polite declines."

**[Show metrics]**

> "Each conversation is evaluated across multiple dimensions:"

- **Response Quality** — Is Rebecca warm, concise, jargon-free?
- **Tool Usage** — Does she send emails only after consent?
- **Hallucination Check** — Is she sticking to accurate information?

**[Show results table]**

> "Our current scores: 85% hallucination safety, 79% response quality, and 100% tool usage accuracy."

---

## CLOSING (2:35 - 3:00) — 25 seconds

**[Screen: Future roadmap]**

> "Looking ahead, we're building:"
> - Turn-key deployment for healthcare organizations
> - Multi-language support — Spanish, Vietnamese, Mandarin
> - Real-time sentiment analysis to detect frustration
> - Callback scheduling integrated with calendar APIs

**[Screen: Personal story / Mission]**

> "This project is personal to me. My grandmother was diagnosed with breast cancer at 66. Her doctor said if she'd had regular screenings, it could have been caught earlier."

**[Screen: Vaklab logo + tagline]**

> "Vaklab exists to make sure no one else misses that chance. Thank you."

**[End card: GitHub link, contact info]**

---

## 📝 Production Notes

### Key Moments to Capture:
1. **Terminal command** running the outbound call
2. **UI Dashboard** showing real-time transcription
3. **Architecture diagram** with animations highlighting the flow
4. **Email** being received in inbox (if time permits)
5. **Evaluation CLI** showing test results

### Suggested B-Roll:
- Code scrolling in VS Code
- Database queries running
- Pipecat pipeline logs streaming

### Voice/Tone:
- Warm but professional
- Conversational, not scripted-feeling
- Genuine passion when sharing personal story

### Technical Requirements:
- Screen recording at 1080p or higher
- Clear audio (use external mic)
- ngrok running for Twilio callbacks
- Database docker container running
- UI dashboard open at localhost:8000/ui

---

## 🎯 Demo Checklist

Before recording:
- [ ] Start Docker containers (`docker-compose up -d`)
- [ ] Start ngrok (`ngrok http 8000`)
- [ ] Update Twilio webhook URL
- [ ] Start FastAPI server (`python main.py`)
- [ ] Open UI dashboard in browser
- [ ] Test call works before recording
- [ ] Clear terminal history
- [ ] Close unnecessary apps/notifications

---

*Script created for GCP Hackathon 2026 submission*
