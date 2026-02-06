# Metna: AI-Powered Healthcare Outreach Agent

## 🎯 Inspiration

This project is deeply personal.

My grandmother was diagnosed with breast cancer at the age of 66. During treatment, her doctor told our family something that stayed with me:
if she had gone for regular breast cancer screening, the disease could have been detected early — she might have lived another 10 years, and treatment would have been far less aggressive.

That moment made me realize that the problem isn’t just medicine — it’s missed opportunities.

Breast cancer remains one of the leading causes of cancer-related deaths among women. Early detection through routine mammogram screenings can reduce mortality by up to **40%**, yet thousands of Medicare members miss these screenings every year due to:

- Lack of awareness of free screening benefits
- Confusion about Medicare coverage
- Fear, anxiety, or complex medical language
- Missed reminders and difficulty scheduling appointments

I asked myself:

> *"What if no one ever missed a life-saving screening simply because they didn't understand, forgot, or felt overwhelmed?"*

That question inspired **Metna** — an empathetic, AI-powered voice agent designed to proactively reach Medicare members and guide them through breast cancer screening with care, clarity, and compassion.

## 🏗️ How I Built It

### Architecture Overview

### Real-Time Voice Pipeline

```
┌─────────────────┐     ┌──────────────────────────────────────────────────────┐
│                 │     │                    Pipecat Pipeline                   │
│   Twilio        │     │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌───────┐ │
│   Media Stream  │◀───▶│  │ Google  │──▶│ Gemini  │──▶│ Google  │──▶│ Audio │ │
│   (WebSocket)   │     │  │  STT    │   │   LLM   │   │  TTS    │   │  Out  │ │
│                 │     │  └─────────┘   └─────────┘   └─────────┘   └───────┘ │
└─────────────────┘     └──────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────┐
                        │          Transcript Manager              │
                        │    (Real-time WebSocket to UI)           │
                        └──────────────────────────────────────────┘
                                               │
                        ┌──────────────────────┴───────────────────┐
                        ▼                                          ▼
                ┌───────────────┐                         ┌────────────────┐
                │  Live UI      │                         │  PostgreSQL    │
                │  Dashboard    │                         │  (Call Logs)   │
                └───────────────┘                         └────────────────┘
```

### Evaluation Framework Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐
│  Conversation   │     │   ADK Eval       │     │     Evaluation Metrics      │
│  Scenarios      │────▶│   Runner         │────▶│  ┌─────────────────────────┐│
│  (JSON)         │     │  (User Sim)      │     │  │ • Response Quality      ││
└─────────────────┘     └──────────────────┘     │  │ • Tool Usage Quality    ││
                                                 │  │ • Hallucination Check   ││
                                                 │  │ • Custom Rubrics        ││
                                                 │  └─────────────────────────┘│
                                                 └──────────────┬──────────────┘
                                                                │
                                                                ▼
                        ┌──────────────────┐           ┌─────────────────┐
                        │   PostgreSQL     │◀──────────│  Eval Results   │
                        │   (Eval Data)    │           │  (Scores/Turns) │
                        └──────────────────┘           └─────────────────┘
```

### Agent Tools & Services

```
                        ┌──────────────────┐
                        │  Google ADK      │
                        │  Agent (Rebecca) │
                        └────────┬─────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
   │ send_email()  │    │ end_call()    │    │ transfer_to   │
   │ Enrollment    │    │ Graceful      │    │ _agent()      │
   │ Confirmation  │    │ Termination   │    │ Human Handoff │
   └───────────────┘    └───────────────┘    └───────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| **AI Agent** | Google ADK + Gemini 2.0 Flash |
| **Telephony** | Twilio Voice API |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL |
| **Containerization** | Docker Compose |
| **Evaluation** | ADK Eval Framework + Custom Rubrics |

### The Agent Conversation Flow

The agent follows a carefully designed conversation flow:

```python
# Simplified flow
1. Hook: "Hi {name}! This is Metna calling about your health benefits..."
2. Zip Code Verification: "Can I confirm your zip code is {zip}?"
3. Value Proposition: "Your plan covers FREE mammogram screenings..."
4. Enrollment: "Would you like me to send you the details via email?"
5. Confirmation: send_enrollment_email(member_id, email)
6. Graceful End: "Thank you! Have a wonderful day!"
```

### Evaluation Framework

One of the most critical aspects was building a robust evaluation system. I used Google ADK's **User Simulation** feature to test the agent against 5 different scenarios:

| Scenario | Description | Success Criteria |
|----------|-------------|------------------|
| Happy Path | User interested, enrolls immediately | Email sent, call ended properly |
| Pain Concern | User asks "Does it hurt?" | Agent addresses concern, then enrolls |
| User Busy | User can't talk right now | Agent offers callback, graceful exit |
| Cost Questions | User asks about procedure cost | Agent explains free benefit |
| User Declines | User not interested | Agent respects decision, ends politely |

### Custom Evaluation Rubrics

I defined evaluation metrics across two categories:

**Response Quality** \\( (threshold = 0.7) \\)
- `warm_tone`: Maintains friendly, encouraging communication
- `concise_responses`: Uses short, conversational sentences
- `no_jargon`: Avoids confusing medical terminology
- `clear_value_prop`: Explains mammogram benefits clearly

**Tool Usage Quality** \\( (threshold = 0.8) \\)
- `email_after_confirmation`: Only sends email after explicit consent
- `end_call_appropriate`: Ends call at the right moment
- `zip_code_verification`: Verifies member's zip code before proceeding

The overall quality score is computed as:

$$
Q_{overall} = \frac{1}{n} \sum_{i=1}^{n} w_i \cdot R_i
$$

where \\( R_i \\) is the rubric score and \\( w_i \\) is the weight for each rubric.

## 📚 What I Learned

### 1. Prompt Engineering for Empathy

Getting an AI to sound genuinely caring — not robotic — required extensive prompt tuning:

```
❌ "I am calling to inform you about your mammogram screening benefit."
✅ "Hi! I hope I caught you at a good time. I have some great news about your health benefits!"
```

### 2. Handling Edge Cases Gracefully

Real conversations are messy. Users might:
- Say "not now" (agent must offer to call back)
- Ask unexpected questions ("Is this a scam?")
- Give one-word answers ("No", "Maybe")

I learned to design the agent to handle ambiguity without breaking the flow.

### 3. Evaluation-Driven Development

Writing evaluation scenarios *before* finalizing the agent helped me:
- Define clear success criteria
- Catch regressions early
- Quantify improvements objectively

### 4. Database-Backed Observability

Storing every conversation turn in PostgreSQL enabled:

```sql
-- Track agent performance over time
SELECT scenario_name,
       ROUND(AVG(overall_score)::numeric, 3) as avg_score,
       COUNT(*) as total_runs
FROM eval_runs 
GROUP BY scenario_name;
```

## 🚧 Challenges I Faced

### Challenge 1: Conversation Turn Extraction

**Problem:** The ADK CLI outputs evaluation results, but conversation turns weren't being captured in my database.

**Solution:** I discovered ADK stores detailed eval history in JSON files:
```
agents/outbound_agent/.adk/eval_history/*.evalset_result.json
```

I wrote a parser to extract `user_content`, `final_response`, and `tool_calls` from each invocation and store them in PostgreSQL.

### Challenge 2: Vertex AI Credentials for Safety Metrics

**Problem:** The `safety_v1` metric requires Google Cloud credentials:
```
ERROR: Missing project id.
This metric uses Vertex Gen AI Eval SDK...
```

**Workaround:** For local development, I focused on custom rubrics while setting up proper GCP authentication for production.

### Challenge 3: Balancing Conversational Warmth with Efficiency

**Problem:** Too friendly = long calls, annoyed members. Too efficient = cold, robotic.

**Solution:** I tuned the agent to:
- Keep responses under 2-3 sentences
- Use encouraging phrases ("Great question!")
- Pause for natural conversation rhythm

### Challenge 4: Email Timing Logic

**Problem:** The agent would sometimes send emails before the user confirmed interest.

**Solution:** Added explicit rubric checking:
```json
{
  "rubric_id": "email_after_confirmation",
  "criteria": "The agent MUST wait for verbal confirmation before sending the enrollment email"
}
```

## 📈 Results

After multiple iterations, the agent achieved:

| Metric | Score | Threshold |
|--------|-------|-----------|
| Hallucinations | 0.85 | 0.8 ✅ |
| Response Quality | 0.79 | 0.7 ✅ |
| Tool Use Quality | 1.0 | 0.8 ✅ |
| Overall | **0.76** | 0.7 ✅ |

## 🔮 Future Enhancements

1. **Turn Key Solution** — One-click deployment for healthcare organizations
2. **Multi-language Support** — Spanish, Vietnamese, Mandarin
3. **Sentiment Analysis** — Detect frustration and adapt tone
4. **Callback Scheduling** — Integrate with calendar APIs
5. **A/B Testing** — Compare different conversation scripts
6. **Real-time Dashboard** — Live visualization of call outcomes

## 🙏 Acknowledgments

- **Google ADK Team** — For the powerful agent development framework
- **Twilio** — For reliable telephony infrastructure
- **Open Source Community** — For FastAPI, PostgreSQL, and Docker

---

*Built with ❤️ for the GCP Hackathon 2026*
