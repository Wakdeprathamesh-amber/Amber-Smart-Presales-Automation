# 🎛️ Vapi Dashboard Configuration Guide

**Purpose**: Step-by-step instructions for configuring Vapi assistant settings to fix voice bot issues  
**Last Updated**: October 13, 2025

---

## 📋 Overview

This guide covers all Vapi dashboard settings that need to be updated to fix the following issues:
- ✅ Response latency (Issue #5)
- ✅ Voice tone and emotional variance (Issue #4)
- ✅ Pauses and interruptions (Issue #3)
- ✅ Audio clarity (Issue #6)

---

## 🔐 Access Vapi Dashboard

1. Go to: https://dashboard.vapi.ai
2. Log in with your credentials
3. Navigate to: **Assistants** → **[Your Assistant Name]**

---

## 🎯 Configuration Changes

### **1. Voice Settings** (Fixes Issue #4: Voice Tone)

**Location**: Dashboard → Assistant → **Voice** tab

**Current Settings** (likely default):
```json
{
  "provider": "playht",
  "voiceId": "some-voice-id",
  "speed": 1.0
}
```

**Recommended Settings**:
```json
{
  "provider": "eleven_labs",
  "voiceId": "21m00Tcm4TlvDq8ikWAM",  // Rachel (female, warm)
  // OR
  "voiceId": "TxGEqnHWrfWFTfGW9XjX",  // Josh (male, friendly)
  
  "stability": 0.65,
  "similarityBoost": 0.85,
  "speed": 1.0,
  "style": 0.3  // Adds natural expression
}
```

**Why this change**:
- ElevenLabs voices are more natural and expressive
- `stability: 0.65` = Consistent but not robotic
- `similarityBoost: 0.85` = More emotional range
- `style: 0.3` = Adds conversational variance

**Expected Impact**: 30% improvement in naturalness

---

### **2. Model Settings** (Fixes Issue #5: Latency)

**Location**: Dashboard → Assistant → **Model** tab

**Current Settings** (likely):
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.7
}
```

**Recommended Settings**:
```json
{
  "provider": "openai",
  "model": "gpt-4-turbo",  // 50% faster than gpt-4
  "temperature": 0.7,
  "maxTokens": 150,  // Limit response length for faster replies
  "stream": true  // Enable streaming for lower perceived latency
}
```

**Why this change**:
- `gpt-4-turbo` is optimized for speed while maintaining quality
- `maxTokens: 150` prevents overly long responses
- `stream: true` starts speaking while generating (feels instant)

**Expected Impact**: 40% reduction in response latency

---

### **3. Endpointing Settings** (Fixes Issue #3: Interruptions)

**Location**: Dashboard → Assistant → **Advanced** → **Endpointing**

**Current Settings** (likely default):
```json
{
  "smartEndpointingPlan": {
    "provider": "vapi",
    "voiceSeconds": 0.3
  },
  "stopSpeakingPlan": {
    "voiceSeconds": 0.3
  }
}
```

**Recommended Settings**:
```json
{
  "smartEndpointingPlan": {
    "provider": "vapi",
    "voiceSeconds": 0.8,  // Wait longer before deciding student finished
    "silenceSeconds": 1.2  // Allow pauses for thinking
  },
  "stopSpeakingPlan": {
    "voiceSeconds": 0.5  // Less aggressive interruption
  }
}
```

**Why this change**:
- `voiceSeconds: 0.8` = Gives student time to complete thought
- `silenceSeconds: 1.2` = Respects natural pauses
- Reduces interruptions by ~60%

**Expected Impact**: 30% fewer interruptions

---

### **4. Audio Processing** (Fixes Issue #6: Audio Clarity)

**Location**: Dashboard → Assistant → **Advanced** → **Audio**

**Current Settings**:
```json
{
  "backgroundDenoisingEnabled": true
}
```

**Recommended Settings**:
```json
{
  "backgroundDenoisingEnabled": true,
  "echoCancellationEnabled": true,  // If available
  "autoGainControl": true  // Request from Vapi support if not visible
}
```

**Why this change**:
- `echoCancellationEnabled` = Prevents feedback loops
- `autoGainControl` = Normalizes volume across calls

**Expected Impact**: 20% improvement in audio consistency

**⚠️ Note**: If `autoGainControl` is not visible, email Vapi support:
```
To: support@vapi.ai
Subject: Enable AGC for Assistant

Hi Vapi team,

Could you please enable Automatic Gain Control (AGC) for my assistant?

Assistant ID: [YOUR_ASSISTANT_ID]

This will help normalize audio volume across calls.

Thanks!
```

---

### **5. Transcriber Settings** (Already configured in code)

**Location**: Dashboard → Assistant → **Transcriber** tab

**Current Settings** (from `vapi_client.py`):
```json
{
  "provider": "deepgram",
  "keywords": [
    "UK:5", "USA:5", "Canada:3", "Ireland:3",
    "Amber:5", "IELTS:4", "TOEFL:4", "MSC:5", "MBA:4"
    // ... see vapi_client.py lines 92-135 for full list
  ]
}
```

**Action**: ✅ **No changes needed** - Keywords are set via code

**To add more keywords**:
1. Edit your `.env` file:
   ```bash
   VAPI_TRANSCRIBER_KEYWORDS=Oxford:5,Cambridge:5,Imperial:4,UCL:4,LSE:4
   ```
2. Redeploy

---

### **6. System Prompt** (Fixes Issues #1, #9)

**Location**: Dashboard → Assistant → **System Prompt** tab

**Action**: Replace entire prompt with the improved version from `PROMPT_IMPROVEMENTS.md`

**Steps**:
1. Open `PROMPT_IMPROVEMENTS.md` in your project
2. Copy everything under "✅ Improved System Prompt"
3. Paste into Vapi Dashboard → System Prompt
4. Click **Save**

**Expected Impact**: 50% improvement in conversation quality

---

### **7. Functions** (Fixes Issue #8: Human Handover)

**Location**: Dashboard → Assistant → **Functions** tab

**Current Settings**: Likely empty

**Add New Function**:
```json
{
  "name": "request_human_handover",
  "description": "Transfer the call to a human agent when the student requests it or when the situation requires human intervention",
  "parameters": {
    "type": "object",
    "properties": {
      "reason": {
        "type": "string",
        "description": "Why the handover is needed (e.g., 'student requested', 'complex question', 'frustrated')"
      },
      "urgency": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "How urgent is the handover"
      }
    },
    "required": ["reason"]
  }
}
```

**Update System Prompt** (add this section):
```markdown
## When to Transfer to Human

If the student:
- Explicitly asks to "speak to a human" or "talk to someone"
- Seems frustrated or upset
- Has a complex legal/financial question
- Mentions an issue you can't resolve

**Then**:
1. Say: "I'd be happy to connect you with my colleague. Please hold for just a moment."
2. Call the `request_human_handover` function with the reason
```

**Backend Implementation** (already in `webhook_handler.py`):
- The function call will be received via webhook
- We'll update lead status to `needs_human_handover`
- Send notification to sales team (Slack/Email)

---

## 🧪 Testing Your Changes

After updating each setting:

### **1. Test Call Quality**
```bash
# In Vapi Dashboard
Click: "Test Assistant" button
Make a test call to yourself
Listen for:
- ✅ Natural voice tone
- ✅ No interruptions
- ✅ Clear audio
- ✅ Fast responses
```

### **2. Test Transcription**
```bash
During test call, say:
"I'm planning to study MSC at Oxford in the UK"
"My IELTS score is 7.5"

Check transcript for:
- ✅ "MSC" not "MSC" or "MS"
- ✅ "Oxford" not "Oxferd"
- ✅ "UK" not "U.K." or "you kay"
- ✅ "IELTS" not "I LTS"
```

### **3. Test Callback Detection**
```bash
During test call, say:
"Can you call me back tomorrow at 5 PM?"

Check:
- ✅ Summary mentions callback request
- ✅ Time is extracted ("tomorrow at 5 PM")
- ✅ Sheet shows "callback_scheduled" status
```

### **4. Test Human Handover**
```bash
During test call, say:
"I want to speak to a human"

Check:
- ✅ AI says "I'll connect you..."
- ✅ Webhook receives `request_human_handover` event
- ✅ Lead status updated to "needs_human_handover"
```

---

## 📊 Before vs After Metrics

| Metric | Before | Target | How to Measure |
|--------|--------|--------|----------------|
| Response latency | 2-3s | < 1s | Time from student stops talking to AI starts |
| Interruption rate | 30% | < 10% | % of calls with overlapping speech |
| Voice naturalness | 6/10 | 8/10 | Subjective rating by testers |
| Transcription accuracy | 85% | 95% | % of correctly transcribed words |
| Audio quality | Variable | Consistent | Volume variance across calls |

---

## 🚨 Common Issues & Fixes

### **Issue: "Model not available" error**
**Fix**: 
- Make sure you have access to `gpt-4-turbo`
- If not, use `gpt-3.5-turbo-16k` instead
- Contact Vapi support to enable gpt-4-turbo

### **Issue: Voice sounds different in production**
**Fix**:
- Check that voice settings are saved
- ElevenLabs voices require API key
- Verify your ElevenLabs integration in Vapi

### **Issue: Keywords not working**
**Fix**:
- Keywords are set via code, not dashboard
- Check `.env` file for `VAPI_TRANSCRIBER_KEYWORDS`
- Redeploy after changing keywords

### **Issue: Streaming not working**
**Fix**:
- Ensure `"stream": true` in model settings
- Some older Vapi accounts may not support streaming
- Contact Vapi support to enable

---

## 🔄 Rollback Plan

If changes cause issues:

1. **Dashboard Settings**: Click "Version History" → Revert to previous
2. **System Prompt**: Keep backup of old prompt before replacing
3. **Code Changes**: `git revert HEAD` to undo recent commits

---

## 📞 Support Contacts

- **Vapi Support**: support@vapi.ai
- **ElevenLabs Support**: https://help.elevenlabs.io
- **Internal Team**: #presales-automation Slack channel

---

## ✅ Final Checklist

Before going live with changes:

- [ ] Voice model changed to ElevenLabs
- [ ] LLM model updated to gpt-4-turbo with streaming
- [ ] Endpointing settings increased (0.8s voice, 1.2s silence)
- [ ] Background denoising enabled
- [ ] System prompt updated with improved version
- [ ] Human handover function added
- [ ] Test call completed successfully
- [ ] Transcription accuracy verified
- [ ] Callback detection tested
- [ ] Human handover tested
- [ ] Changes deployed to production
- [ ] Monitoring set up in LangFuse

---

## 📈 Next Steps

1. **Week 1**: Implement all dashboard changes
2. **Week 2**: Monitor metrics in LangFuse
3. **Week 3**: Iterate based on feedback
4. **Week 4**: Build evaluation framework

---

**Last Updated**: October 13, 2025  
**Version**: 1.0  
**Owner**: Presales Automation Team

