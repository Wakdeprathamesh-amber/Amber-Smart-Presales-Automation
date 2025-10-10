# 🔧 LangFuse Connection Troubleshooting

## ❌ Error: "Invalid credentials. Confirm that you've configured the correct host."

This error means LangFuse can't authenticate with your keys.

---

## 🎯 **Quick Fix (5 minutes)**

### **Step 1: Get Fresh Keys from LangFuse**

1. Go to https://cloud.langfuse.com
2. Log in (or sign up if you haven't yet)
3. Select your project (or create one: "Smart Presales Production")
4. Click **Settings** (left sidebar) → **API Keys**
5. You'll see two keys:

```
Public Key:  pk-lf-1234567890abcdef...
Secret Key:  sk-lf-0987654321fedcba...
```

**Copy both keys** (click the copy icon)

---

### **Step 2: Add Keys to Render (CAREFULLY)**

Go to Render dashboard → Your service → **Environment** tab

#### ⚠️ **IMPORTANT: Common Mistakes to Avoid**

❌ **DON'T**:
- Add quotes around keys: `"pk-lf-123"` ← WRONG
- Add spaces: `pk-lf-123 ` ← WRONG
- Use wrong key in wrong field ← WRONG
- Copy partial key ← WRONG

✅ **DO**:
- Copy the ENTIRE key
- No quotes, no spaces
- Paste exactly as-is
- Double-check you copied the right key to the right field

---

### **Step 3: Add These 4 Environment Variables**

Click **"Add Environment Variable"** for each:

#### Variable 1: Enable Observability
```
Key:   ENABLE_OBSERVABILITY
Value: true
```
*(Type "true" - no quotes)*

---

#### Variable 2: Public Key
```
Key:   LANGFUSE_PUBLIC_KEY
Value: pk-lf-1234567890abcdef...
```
*(Paste your ACTUAL public key - starts with pk-lf-)*

**⚠️ Make sure**:
- Starts with `pk-lf-`
- No spaces before or after
- No quotes
- Complete key (usually 30-40 characters)

---

#### Variable 3: Secret Key
```
Key:   LANGFUSE_SECRET_KEY
Value: sk-lf-0987654321fedcba...
```
*(Paste your ACTUAL secret key - starts with sk-lf-)*

**⚠️ Make sure**:
- Starts with `sk-lf-`
- No spaces before or after
- No quotes
- Complete key (usually 30-40 characters)

---

#### Variable 4: Host
```
Key:   LANGFUSE_HOST
Value: https://cloud.langfuse.com
```
*(Type exactly as shown - no trailing slash)*

---

### **Step 4: Save and Redeploy**

1. Click **"Save Changes"** button (bottom of page)
2. Render will automatically redeploy (~3 minutes)
3. Watch the **Logs** tab

---

### **Step 5: Verify in Logs**

**Look for this SUCCESS message**:
```
✅ LangFuse client initialized (host: https://cloud.langfuse.com)
```

**Should NOT see**:
```
❌ langfuse - ERROR - received error response: {'error': 'UnauthorizedError'...
```

---

## 🔍 **Still Getting Errors? Debug Checklist**

### Check 1: Keys Are Correct Format

**Public key should look like**:
```
pk-lf-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t
```
- Starts with `pk-lf-`
- Followed by random alphanumeric string
- Usually 30-50 characters total

**Secret key should look like**:
```
sk-lf-9s8r7q6p5o4n3m2l1k0j9i8h7g6f5e4d3c2b1a
```
- Starts with `sk-lf-`
- Followed by random alphanumeric string
- Usually 30-50 characters total

---

### Check 2: Keys Are From Correct Project

1. Go to LangFuse dashboard
2. **Top left**: Check which project is selected
3. Make sure it's "Smart Presales Production" (or your project name)
4. Go to Settings → API Keys
5. Copy keys from THIS project

**Common mistake**: Copying keys from a different project!

---

### Check 3: No Extra Characters

In Render environment variables, check for:
- ❌ Leading/trailing spaces: ` pk-lf-123` or `pk-lf-123 `
- ❌ Quotes: `"pk-lf-123"` or `'pk-lf-123'`
- ❌ Line breaks in the middle
- ❌ Partial key (copied only part of it)

**How to check**:
1. In Render → Environment
2. Click on the variable
3. Look at the value carefully
4. If suspicious, delete and re-add

---

### Check 4: Host URL is Correct

```
✅ Correct:   https://cloud.langfuse.com
❌ Wrong:     https://cloud.langfuse.com/
❌ Wrong:     http://cloud.langfuse.com
❌ Wrong:     cloud.langfuse.com
```

**Must be**:
- `https://` (with s)
- No trailing slash
- Exact domain: `cloud.langfuse.com`

---

### Check 5: LangFuse Account is Active

1. Go to https://cloud.langfuse.com
2. Make sure you can log in
3. Make sure your project exists
4. Try creating a test trace manually in their UI

---

## 🆘 **Emergency Fallback: Disable LangFuse**

If you need the system working RIGHT NOW without LangFuse:

### In Render Environment:
```
ENABLE_OBSERVABILITY=false
```

**Or remove these variables entirely**:
- LANGFUSE_PUBLIC_KEY
- LANGFUSE_SECRET_KEY
- LANGFUSE_HOST

**Result**:
- ✅ App will work perfectly
- ⚠️ No traces in LangFuse
- ✅ Logs will show: "LangFuse not configured, observability disabled"

**You can add LangFuse later** when you have correct keys.

---

## ✅ **Correct Configuration Example**

Here's what it should look like in Render:

```
Environment Variables:

ENABLE_OBSERVABILITY              true
LANGFUSE_PUBLIC_KEY               pk-lf-1a2b3c4d5e6f7g8h9i0j
LANGFUSE_SECRET_KEY               sk-lf-9s8r7q6p5o4n3m2l1k0j
LANGFUSE_HOST                     https://cloud.langfuse.com
GOOGLE_SHEETS_CREDENTIALS_FILE    config/amber-sheets-credentials.json
LEADS_SHEET_ID                    1_igPqrjG7-78grDcZkROHRqbtV...
VAPI_API_KEY                      5c226757-c...
VAPI_ASSISTANT_ID                 13d76c87-3df2-481b-817e...
VAPI_PHONE_NUMBER_ID              1ff83ff6-11c9-4d73-8d0b...
```

---

## 🎓 **How to Get New Keys (If Needed)**

### Option A: Use Existing Project
1. https://cloud.langfuse.com → Login
2. Select your project
3. Settings → API Keys
4. Copy keys (they don't change unless you regenerate)

### Option B: Create New Project
1. https://cloud.langfuse.com → Login
2. Click "New Project" (top right)
3. Name: "Smart Presales Production"
4. Settings → API Keys
5. Copy keys

### Option C: Regenerate Keys
1. https://cloud.langfuse.com → Login
2. Settings → API Keys
3. Click "Regenerate" (⚠️ old keys stop working!)
4. Copy new keys
5. Update in Render

---

## 📞 **Test After Fixing**

### 1. Check Render Logs
After saving environment variables and redeploying:

**Look for**:
```
✅ LangFuse client initialized (host: https://cloud.langfuse.com)
🚀 Background scheduler started successfully
```

**Should NOT see**:
```
❌ langfuse - ERROR - received error response: {'error': 'UnauthorizedError'
```

### 2. Make a Test Call
- Open dashboard: https://amber-smart-presales-automation.onrender.com
- Click on any lead
- Click "Initiate Call"

### 3. Check LangFuse Dashboard
- Go to https://cloud.langfuse.com
- Click "Traces" (left sidebar)
- **You should see a new trace!**

---

## 🎯 **Quick Verification Command**

After fixing, run this to verify:

```bash
# Check if observability is working
curl https://amber-smart-presales-automation.onrender.com/api/jobs

# Should return 3 jobs without errors
```

Then check Render logs - should see:
```
✅ LangFuse client initialized
```

---

## 💡 **Pro Tips**

### Tip 1: Use .env File Format
When copying keys, they should look like this in your notes:
```
LANGFUSE_PUBLIC_KEY=pk-lf-1a2b3c4d5e6f7g8h9i0j
LANGFUSE_SECRET_KEY=sk-lf-9s8r7q6p5o4n3m2l1k0j
```
No `=` in the key itself, no quotes.

### Tip 2: Test Locally First
Before adding to Render, test locally:
```bash
# Add to your local .env
LANGFUSE_PUBLIC_KEY=pk-lf-your-key
LANGFUSE_SECRET_KEY=sk-lf-your-key

# Test
./venv/bin/python test_langfuse_connection.py
```

If it works locally, same keys will work in Render.

### Tip 3: Check LangFuse Status
If nothing works, check: https://status.langfuse.com
(Rare, but LangFuse could be down)

---

## 📧 **Still Stuck?**

### Option 1: Disable for Now
```
ENABLE_OBSERVABILITY=false
```
Your app works perfectly without LangFuse. Add it later when you have time.

### Option 2: Self-Host LangFuse
If cloud keys aren't working, you can self-host:
```bash
docker run -d -p 3000:3000 langfuse/langfuse
```
Then use: `LANGFUSE_HOST=http://your-server:3000`

### Option 3: Contact LangFuse Support
- Discord: https://langfuse.com/discord
- Docs: https://langfuse.com/docs/troubleshooting

---

## ✅ **Success Looks Like**

### Render Logs:
```
2025-10-10 10:30:00 - src.observability - INFO - ✅ LangFuse client initialized (host: https://cloud.langfuse.com)
2025-10-10 10:30:05 - src.vapi_client - INFO - Calling API with payload: {...}
2025-10-10 10:30:06 - langfuse - INFO - Successfully sent trace to LangFuse
```

### LangFuse Dashboard:
- Traces appearing in real-time
- Click on trace → See full call lifecycle
- No error messages

---

**Fix the keys in Render and you'll be golden!** 🚀

