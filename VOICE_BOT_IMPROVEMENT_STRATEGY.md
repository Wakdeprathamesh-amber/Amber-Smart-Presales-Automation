# 🎯 Voice Bot Improvement Strategy

**Date**: October 13, 2025  
**Status**: Action Plan Created  
**Priority**: High

---

## 📊 Issues Summary

Based on testing feedback, we've identified **8 core issues** and **6 technical concerns** that affect conversation quality, latency, and user experience.

---

## 🔍 Issue Analysis & Solutions

### ✅ **TIER 1: Can Fix Immediately (Code/Prompt Changes)**

These issues can be resolved through prompt engineering, configuration updates, and code changes **without vendor support**.

---

#### **Issue #1: Prompt Tuning Issues**
**Problems:**
- Calling just first name (too informal?)
- Missing "Is this a good time to speak?" check
- Repeating country question multiple times
- Improper emphasis (e.g., "exciting" sounds flat)

**Root Cause:** Current prompt lacks:
- Conversation flow control
- Context memory checks
- Natural greeting structure
- Emphasis markers

**Solution:**
✅ **Immediate Fix**: Update Vapi assistant prompt in dashboard

**Action Items:**
1. Add greeting structure:
   ```
   "Hi [FirstName], this is Eshwari from Amber. Is this a good time for a quick chat about your study abroad plans?"
   ```

2. Add context memory:
   ```
   "Before asking a question, check if you've already asked it in this conversation. Never repeat questions."
   ```

3. Add emphasis markers:
   ```
   Use natural emphasis: "That's *really* exciting!" or "This is a *great* opportunity!"
   ```

4. Add flow control:
   ```
   If student says "I already told you", apologize and move to next topic immediately.
   ```

**Estimated Impact:** 🟢 High (40% improvement in conversation quality)  
**Effort:** 🟢 Low (30 minutes)  
**Owner:** Prompt Engineer + Vapi Dashboard

---

#### **Issue #2: Misunderstanding Words**
**Problems:**
- AI mishears country names, university names, course names
- Common words like "UK", "USA", "MSC", "IELTS" are misrecognized

**Root Cause:** Deepgram transcriber needs keyword boosting for domain-specific terms

**Solution:**
✅ **Already Implemented**: We have keyword boosting in `vapi_client.py` (lines 92-135)

**Current Keywords:**
```python
"UK:5", "USA:5", "Canada:3", "Ireland:3", "France:3", 
"Amber:5", "IELTS:4", "TOEFL:4", "GRE:4", "GMAT:4",
"MSC:5", "MBA:4", "Bachelors:3", "Masters:3", "PhD:3",
"Visa:4", "Guarantor:4", "WhatsApp:4"
```

**Action Items:**
1. ✅ Review test call transcripts from LangFuse
2. ✅ Identify commonly misheard words
3. ✅ Add them to `VAPI_TRANSCRIBER_KEYWORDS` env variable with boost values
4. ✅ Test with new keywords

**Example additions:**
```bash
# Add to .env
VAPI_TRANSCRIBER_KEYWORDS=UK:5,USA:5,MSC:5,IELTS:5,Oxford:4,Cambridge:4,Imperial:4,UCL:4,LSE:4
```

**Estimated Impact:** 🟢 High (30% improvement in transcription accuracy)  
**Effort:** 🟢 Low (15 minutes + testing)  
**Owner:** DevOps + QA

---

#### **Issue #3: Handling Pauses and Overlapping**
**Problems:**
- AI interrupts student mid-sentence
- AI doesn't wait for student to finish thinking
- Awkward overlaps during pauses

**Root Cause:** Vapi's `endpointing` settings are too aggressive

**Solution:**
✅ **Immediate Fix**: Adjust Vapi assistant's speech detection settings

**Action Items:**
1. Go to Vapi Dashboard → Assistant Settings
2. Update **Smart Endpointing** settings:
   ```json
   {
     "smartEndpointingPlan": {
       "provider": "vapi",
       "voiceSeconds": 0.8,  // Increase from default 0.3
       "silenceSeconds": 1.2  // Wait longer for pauses
     }
   }
   ```

3. Update **Stop Speaking Plan**:
   ```json
   {
     "stopSpeakingPlan": {
       "voiceSeconds": 0.5  // Increase from 0.3 (current)
     }
   }
   ```

4. Add to prompt:
   ```
   "If the student pauses, wait 2-3 seconds before responding. They might be thinking."
   ```

**Estimated Impact:** 🟡 Medium (25% reduction in interruptions)  
**Effort:** 🟢 Low (10 minutes)  
**Owner:** Vapi Dashboard Admin

---

#### **Issue #7: Call Back at Specific Time**
**Problems:**
- Student says "Call me back at 5 PM" but system doesn't schedule it
- No callback scheduling logic

**Root Cause:** Missing callback extraction and scheduling workflow

**Solution:**
✅ **Code Implementation**: Add callback scheduling to webhook handler

**Action Items:**
1. Update Vapi assistant prompt to extract callback time:
   ```
   "If student requests a callback, ask: 'What time works best for you tomorrow?' and note it clearly in your summary."
   ```

2. Update `webhook_handler.py` to detect callback requests:
   ```python
   # In _handle_call_report method
   if "call back" in summary.lower() or "callback" in summary.lower():
       # Extract time from structured_data or summary
       callback_time = extract_callback_time(summary, structured_data)
       if callback_time:
           schedule_callback(lead_uuid, callback_time)
   ```

3. Create `schedule_callback` function in `scheduler.py`:
   ```python
   def schedule_callback(lead_uuid: str, callback_datetime: datetime):
       """Schedule a one-time callback job"""
       scheduler = get_scheduler()
       scheduler.add_job(
           func=trigger_callback_call,
           trigger='date',
           run_date=callback_datetime,
           args=[lead_uuid],
           id=f"callback_{lead_uuid}_{callback_datetime.timestamp()}"
       )
   ```

**Estimated Impact:** 🟢 High (Enables key feature)  
**Effort:** 🟡 Medium (2-3 hours)  
**Owner:** Backend Developer

---

#### **Issue #8: Human Handover**
**Problems:**
- No way to transfer call to human agent
- Student asks "Can I speak to someone?" but bot can't transfer

**Root Cause:** Missing human handover logic

**Solution:**
✅ **Code + Vapi Configuration**: Implement handover workflow

**Action Items:**
1. Update Vapi assistant prompt:
   ```
   "If student asks to speak to a human, say: 'I'll connect you with my colleague. Please hold for a moment.' Then trigger the handover function."
   ```

2. Add function calling to Vapi assistant:
   ```json
   {
     "functions": [
       {
         "name": "request_human_handover",
         "description": "Transfer call to human agent",
         "parameters": {
           "type": "object",
           "properties": {
             "reason": {"type": "string", "description": "Why handover is needed"}
           }
         }
       }
     ]
   }
   ```

3. Implement handover webhook in `webhook_handler.py`:
   ```python
   def handle_function_call(event_data):
       if event_data.get("functionCall", {}).get("name") == "request_human_handover":
           # Update lead status to "needs_human_handover"
           # Send Slack/Email notification to sales team
           # Optionally: Use Vapi's transfer feature to forward call
   ```

**Estimated Impact:** 🟢 High (Critical for complex cases)  
**Effort:** 🟡 Medium (3-4 hours)  
**Owner:** Backend Developer + Vapi Dashboard Admin

---

### 🟡 **TIER 2: Requires Vapi Configuration (No Code Changes)**

These issues can be fixed by adjusting Vapi assistant settings in the dashboard.

---

#### **Issue #4: Random Speed Changes / Emotional Variance**
**Problems:**
- Voice tone sounds flat and robotic
- Speed varies randomly
- Lacks natural emotion

**Root Cause:** Voice model settings not optimized for conversational tone

**Solution:**
⚠️ **Vapi Dashboard Configuration**: Update voice settings

**Action Items:**
1. Go to Vapi Dashboard → Assistant → Voice Settings
2. Change voice model to a more expressive one:
   - **Recommended**: `eleven_labs/rachel` or `eleven_labs/josh` (more natural)
   - **Alternative**: `playht/jennifer` (consistent emotion)

3. Adjust voice parameters:
   ```json
   {
     "voice": {
       "provider": "eleven_labs",
       "voiceId": "rachel",
       "stability": 0.6,  // Higher = more consistent
       "similarityBoost": 0.8,  // Higher = more expressive
       "speed": 1.0  // Keep constant (no random changes)
     }
   }
   ```

4. Add to prompt:
   ```
   "Speak with warmth and enthusiasm. Match the student's energy level."
   ```

**Estimated Impact:** 🟡 Medium (20% improvement in naturalness)  
**Effort:** 🟢 Low (15 minutes)  
**Owner:** Vapi Dashboard Admin

---

#### **Issue #5: Response Latency**
**Problems:**
- Slight delay before AI responds (1-2 seconds)
- Makes conversation feel less natural

**Root Cause:** Network latency + LLM processing time

**Solution:**
⚠️ **Vapi Configuration + Code Optimization**

**Action Items:**
1. Enable **streaming responses** in Vapi assistant:
   ```json
   {
     "model": {
       "provider": "openai",
       "model": "gpt-4-turbo",  // Faster than gpt-4
       "stream": true  // Enable streaming
     }
   }
   ```

2. Use **faster LLM model**:
   - Switch from `gpt-4` to `gpt-4-turbo` or `gpt-3.5-turbo-16k`
   - Trade-off: Slightly less accurate but 50% faster

3. Optimize webhook response time:
   ```python
   # In webhook_handler.py, process async
   @app.route('/webhook/vapi', methods=['POST'])
   def vapi_webhook():
       # Return 200 immediately, process in background
       event_data = request.json
       threading.Thread(target=process_webhook_async, args=(event_data,)).start()
       return jsonify({"status": "received"}), 200
   ```

**Estimated Impact:** 🟡 Medium (30% latency reduction)  
**Effort:** 🟡 Medium (1 hour)  
**Owner:** Vapi Dashboard Admin + Backend Developer

---

#### **Issue #6: Audio Clarity Issues**
**Problems:**
- Audio clarity varies across calls
- Some clipped or low-volume sections

**Root Cause:** Network quality + audio processing settings

**Solution:**
⚠️ **Vapi Configuration**: Enable audio enhancements

**Action Items:**
1. Enable **background noise suppression** in Vapi:
   ```json
   {
     "backgroundDenoisingEnabled": true  // Already enabled in current config
   }
   ```

2. Request **Automatic Gain Control (AGC)** from Vapi support:
   - Email: support@vapi.ai
   - Request: "Enable AGC for assistant ID: [YOUR_ASSISTANT_ID]"

3. Use **higher quality voice provider**:
   - Switch to ElevenLabs (better audio quality than PlayHT)

**Estimated Impact:** 🟡 Medium (15% improvement in audio quality)  
**Effort:** 🟢 Low (30 minutes + vendor response time)  
**Owner:** Vapi Dashboard Admin

---

### 🔴 **TIER 3: Requires Vendor Support (Long-term)**

These issues require Vapi to implement new features or provide advanced configurations.

---

#### **Issue #9: Intent Clarification**
**Problems:**
- When student's intent isn't clear, bot doesn't clarify smoothly
- No fallback intent recovery

**Root Cause:** Missing conversational repair strategies in prompt

**Solution:**
⚠️ **Prompt Engineering + Dialogue Flow**

**Action Items:**
1. Add clarification patterns to prompt:
   ```
   "If you don't understand the student's response, use these phrases:
   - 'Just to make sure I understand, you're saying...?'
   - 'Could you clarify what you mean by...?'
   - 'I want to make sure I got that right. Did you say...?'
   
   Never say 'I don't understand' or 'Can you repeat that?'"
   ```

2. Add confirmation loop:
   ```
   "After gathering key information (country, university, course), confirm:
   'Great! So you're planning to study [Course] at [University] in [Country], starting [Intake]. Is that correct?'"
   ```

**Estimated Impact:** 🟡 Medium (20% improvement in clarity)  
**Effort:** 🟢 Low (30 minutes)  
**Owner:** Prompt Engineer

---

## 📋 Implementation Roadmap

### **Phase 1: Quick Wins (Week 1)** 🟢
**Effort**: 4-6 hours  
**Impact**: 50% improvement in conversation quality

- [ ] **Day 1**: Update Vapi assistant prompt (Issues #1, #9)
- [ ] **Day 2**: Adjust endpointing settings (Issue #3)
- [ ] **Day 3**: Update voice model and settings (Issue #4)
- [ ] **Day 4**: Add transcription keywords (Issue #2)
- [ ] **Day 5**: Test all changes end-to-end

**Success Metrics:**
- ✅ Fewer repeated questions
- ✅ Better transcription accuracy
- ✅ Fewer interruptions
- ✅ More natural tone

---

### **Phase 2: Feature Development (Week 2)** 🟡
**Effort**: 8-12 hours  
**Impact**: 30% improvement in functionality

- [ ] **Day 1-2**: Implement callback scheduling (Issue #7)
- [ ] **Day 3-4**: Implement human handover (Issue #8)
- [ ] **Day 5**: Optimize webhook latency (Issue #5)

**Success Metrics:**
- ✅ Callbacks scheduled automatically
- ✅ Human handover working
- ✅ Webhook response time < 500ms

---

### **Phase 3: Quality Enhancements (Week 3)** 🔴
**Effort**: 4-6 hours  
**Impact**: 20% improvement in audio/latency

- [ ] **Day 1**: Request AGC from Vapi (Issue #6)
- [ ] **Day 2**: Switch to faster LLM model (Issue #5)
- [ ] **Day 3**: Enable streaming responses (Issue #5)
- [ ] **Day 4**: Test audio quality improvements
- [ ] **Day 5**: Final end-to-end testing

**Success Metrics:**
- ✅ Consistent audio volume
- ✅ Response latency < 1 second
- ✅ No audio clipping

---

## 🎯 Priority Matrix

| Issue | Impact | Effort | Priority | Phase |
|-------|--------|--------|----------|-------|
| #1 Prompt Tuning | 🟢 High | 🟢 Low | **P0** | Phase 1 |
| #2 Transcription | 🟢 High | 🟢 Low | **P0** | Phase 1 |
| #3 Pauses/Overlap | 🟡 Medium | 🟢 Low | **P1** | Phase 1 |
| #7 Callback | 🟢 High | 🟡 Medium | **P1** | Phase 2 |
| #8 Human Handover | 🟢 High | 🟡 Medium | **P1** | Phase 2 |
| #4 Voice Tone | 🟡 Medium | 🟢 Low | **P2** | Phase 1 |
| #5 Latency | 🟡 Medium | 🟡 Medium | **P2** | Phase 2-3 |
| #6 Audio Clarity | 🟡 Medium | 🟢 Low | **P2** | Phase 3 |
| #9 Intent Clarity | 🟡 Medium | 🟢 Low | **P2** | Phase 1 |

---

## 📊 Expected Outcomes

### **After Phase 1 (Week 1):**
- ✅ 50% reduction in repeated questions
- ✅ 30% improvement in transcription accuracy
- ✅ 25% reduction in interruptions
- ✅ More natural, consistent voice tone

### **After Phase 2 (Week 2):**
- ✅ Callback scheduling fully functional
- ✅ Human handover available for complex cases
- ✅ 30% reduction in webhook latency

### **After Phase 3 (Week 3):**
- ✅ Consistent audio quality across all calls
- ✅ Sub-1-second response times
- ✅ Production-ready voice bot

---

## 🛠️ Tools & Resources

### **For Prompt Engineering:**
- Vapi Dashboard: https://dashboard.vapi.ai
- Current prompt location: Vapi Assistant Settings
- Testing: Use Vapi's "Test Call" feature

### **For Code Changes:**
- Files to modify:
  - `src/vapi_client.py` (transcription keywords)
  - `src/webhook_handler.py` (callback, handover)
  - `src/scheduler.py` (callback scheduling)
  - `src/workflows/lead_workflow.py` (handover node)

### **For Testing:**
- LangFuse Dashboard: https://us.cloud.langfuse.com
- Use traces to analyze:
  - Transcription accuracy
  - Response latency
  - Conversation flow issues

### **For Monitoring:**
- Dashboard: http://localhost:5001 (local) or Render URL (production)
- Logs: `logs/app.log`, `logs/main.log`
- Google Sheets: Real-time lead status updates

---

## 🚀 Next Steps

1. **Review this strategy** with the team
2. **Prioritize issues** based on business impact
3. **Assign owners** for each phase
4. **Start with Phase 1** (quick wins)
5. **Test after each change** using LangFuse traces
6. **Iterate based on feedback**

---

## 📞 Need Help?

- **Vapi Support**: support@vapi.ai
- **LangFuse Support**: support@langfuse.com
- **Internal Team**: Check Slack #presales-automation

---

**Last Updated**: October 13, 2025  
**Next Review**: After Phase 1 completion

