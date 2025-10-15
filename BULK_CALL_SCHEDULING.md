# 📅 Bulk Call Scheduling Feature - Implementation Plan

**Date**: October 13, 2025  
**Status**: New Feature Required

---

## 🎯 USE CASE

**Scenario**:
1. Upload 100 leads to Google Sheet
2. Select all 100 leads in dashboard
3. Click "Schedule Calls"
4. Choose: "Start calling at 10:00 AM tomorrow"
5. Choose: "Make 5 calls in parallel"
6. System automatically calls them in batches starting at 10 AM

**Benefits**:
- ✅ Control when calls are made (business hours)
- ✅ Parallel calling (faster processing)
- ✅ Don't spam leads (controlled rate)
- ✅ Better resource management

---

## ❌ CURRENT LIMITATION

**Current System**:
- Processes leads as soon as `call_status = 'pending'`
- Calls happen within 60 seconds of upload
- No bulk scheduling option
- No parallel call control
- No time selection

**What's Missing**:
1. Bulk selection in dashboard
2. Schedule time picker
3. Parallel call configuration
4. Batch processing logic

---

## ✅ PROPOSED SOLUTION

### **Feature: Bulk Call Scheduling**

#### **1. Dashboard UI Enhancement**

Add to dashboard:
```
┌─────────────────────────────────────────────────────────┐
│ Leads Table                                             │
├─────────────────────────────────────────────────────────┤
│ [✓] Select All   | [Schedule Calls] [Export CSV]        │
├─────────────────────────────────────────────────────────┤
│ [✓] Prathamesh | +919876543210 | pending               │
│ [✓] Rahul      | +918765432109 | pending               │
│ [ ] Priya      | +919988776655 | completed             │
└─────────────────────────────────────────────────────────┘

When "Schedule Calls" clicked:

┌─────────────────────────────────────────┐
│ Schedule Bulk Calls                     │
├─────────────────────────────────────────┤
│ Selected Leads: 2                       │
│                                         │
│ Start Time:                             │
│ [Date Picker] [Time Picker]             │
│ Example: Oct 14, 2025 at 10:00 AM IST  │
│                                         │
│ Parallel Calls:                         │
│ [Dropdown: 1 / 3 / 5 / 10]              │
│                                         │
│ Call Interval:                          │
│ [Dropdown: 30s / 60s / 120s]            │
│                                         │
│ [Cancel]  [Schedule Calls]              │
└─────────────────────────────────────────┘
```

#### **2. Backend API Endpoint**

**New Endpoint**: `POST /api/schedule-bulk-calls`

**Request**:
```json
{
  "lead_uuids": ["uuid-123", "uuid-456", "uuid-789"],
  "start_time": "2025-10-14T10:00:00+05:30",
  "parallel_calls": 5,
  "call_interval": 60
}
```

**Response**:
```json
{
  "success": true,
  "scheduled_count": 100,
  "start_time": "2025-10-14T10:00:00+05:30",
  "estimated_completion": "2025-10-14T10:20:00+05:30",
  "job_ids": ["bulk_call_batch_1", "bulk_call_batch_2"]
}
```

#### **3. Batch Processing Logic**

**Implementation**:
```python
# src/scheduler.py

def schedule_bulk_calls(lead_uuids, start_time, parallel_calls=5, call_interval=60):
    """
    Schedule bulk calls to multiple leads.
    
    Args:
        lead_uuids: List of lead UUIDs to call
        start_time: When to start calling (datetime)
        parallel_calls: How many calls to make simultaneously
        call_interval: Seconds between batches
    """
    scheduler = get_scheduler()
    
    # Split leads into batches
    batches = [lead_uuids[i:i+parallel_calls] for i in range(0, len(lead_uuids), parallel_calls)]
    
    # Schedule each batch
    for batch_idx, batch in enumerate(batches):
        # Calculate trigger time for this batch
        batch_start = start_time + timedelta(seconds=batch_idx * call_interval)
        
        # Create job ID
        job_id = f"bulk_call_batch_{batch_idx}_{start_time.timestamp()}"
        
        # Schedule the batch
        scheduler.add_job(
            func=execute_call_batch,
            trigger='date',
            run_date=batch_start,
            args=[batch],
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"✅ Scheduled batch {batch_idx+1}/{len(batches)} at {batch_start} ({len(batch)} leads)")
    
    return {
        "scheduled_count": len(lead_uuids),
        "batch_count": len(batches),
        "start_time": start_time.isoformat(),
        "estimated_completion": (start_time + timedelta(seconds=len(batches) * call_interval)).isoformat()
    }


def execute_call_batch(lead_uuids):
    """
    Execute calls for a batch of leads in parallel.
    
    Args:
        lead_uuids: List of lead UUIDs to call
    """
    import threading
    
    logger.info(f"[BulkCall] Executing batch of {len(lead_uuids)} calls")
    
    threads = []
    for lead_uuid in lead_uuids:
        thread = threading.Thread(target=call_single_lead, args=(lead_uuid,))
        thread.start()
        threads.append(thread)
    
    # Wait for all calls to complete (with timeout)
    for thread in threads:
        thread.join(timeout=300)  # 5 minute timeout per call
    
    logger.info(f"[BulkCall] Batch complete ({len(lead_uuids)} calls)")


def call_single_lead(lead_uuid):
    """Execute a single call for bulk calling."""
    try:
        from src.sheets_manager import SheetsManager
        from src.vapi_client import VapiClient
        
        sheets_manager = SheetsManager()
        vapi_client = VapiClient(os.getenv('VAPI_API_KEY'))
        
        # Get lead data
        lead_row = sheets_manager.find_row_by_lead_uuid(lead_uuid)
        if lead_row is None:
            logger.error(f"[BulkCall] Lead not found: {lead_uuid}")
            return
        
        worksheet = sheets_manager.sheet.worksheet("Leads")
        headers = worksheet.row_values(1)
        row_data = worksheet.row_values(lead_row + 2)
        lead = dict(zip(headers, row_data))
        
        # Update status to scheduled_bulk
        sheets_manager.update_lead_fields(lead_row, {
            "call_status": "bulk_calling"
        })
        
        # Initiate call
        result = vapi_client.initiate_outbound_call(
            lead_data=lead,
            assistant_id=os.getenv('VAPI_ASSISTANT_ID'),
            phone_number_id=os.getenv('VAPI_PHONE_NUMBER_ID')
        )
        
        if result.get('error'):
            logger.error(f"[BulkCall] Failed for {lead_uuid}: {result.get('error')}")
            sheets_manager.update_lead_fields(lead_row, {
                "call_status": "failed",
                "last_ended_reason": result.get('error')
            })
        else:
            logger.info(f"[BulkCall] Initiated for {lead_uuid}")
            sheets_manager.update_lead_fields(lead_row, {
                "call_status": "initiated",
                "vapi_call_id": result.get('id'),
                "last_call_time": get_ist_timestamp()
            })
    
    except Exception as e:
        logger.error(f"[BulkCall] Error calling {lead_uuid}: {e}")
```

---

## 🎯 IMPLEMENTATION PLAN

### **Phase 1: Backend API** (1 hour)
1. Add `schedule_bulk_calls()` function to `src/scheduler.py`
2. Add `execute_call_batch()` function
3. Add `call_single_lead()` function
4. Add `POST /api/schedule-bulk-calls` endpoint to `src/app.py`

### **Phase 2: Dashboard UI** (1 hour)
1. Add checkboxes to lead table
2. Add "Select All" button
3. Add "Schedule Calls" button
4. Create scheduling modal with:
   - Date/time picker
   - Parallel calls selector (1, 3, 5, 10)
   - Call interval selector (30s, 60s, 120s)

### **Phase 3: Testing** (30 min)
1. Upload 10 test leads
2. Select all
3. Schedule for 5 minutes from now
4. Verify calls happen at scheduled time
5. Check parallel execution works

---

## 📊 EXAMPLE SCENARIOS

### **Scenario 1: Morning Batch**
```
Upload: 100 leads at 9:00 PM (night before)
Schedule: Start at 10:00 AM next day
Parallel: 5 calls at a time
Interval: 60 seconds between batches

Result:
- 10:00 AM - Calls 1-5
- 10:01 AM - Calls 6-10
- 10:02 AM - Calls 11-15
- ...
- 10:20 AM - Calls 96-100 (done!)
```

### **Scenario 2: Immediate Parallel**
```
Upload: 50 leads
Schedule: Start immediately
Parallel: 10 calls at a time
Interval: 30 seconds

Result:
- Now - Calls 1-10
- +30s - Calls 11-20
- +60s - Calls 21-30
- ...
- +2.5min - All 50 done
```

### **Scenario 3: Afternoon Wave**
```
Upload: 200 leads in morning
Schedule: Start at 2:00 PM
Parallel: 3 calls (conservative)
Interval: 120 seconds

Result:
- 2:00 PM - Calls 1-3
- 2:02 PM - Calls 4-6
- 2:04 PM - Calls 7-9
- ...
- 3:20 PM - All 200 done
```

---

## ⚠️ IMPORTANT CONSIDERATIONS

### **Vapi Rate Limits**
- Check your Vapi plan for concurrent call limits
- Most plans: 5-10 concurrent calls
- Don't set `parallel_calls` higher than your limit!

### **Cost Management**
- Each call costs ~$0.09/minute
- 100 calls × 3 minutes avg = $27
- Parallel calling doesn't reduce cost, just time

### **Business Hours**
- Schedule calls between 9 AM - 9 PM IST
- Avoid calling too early/late
- Weekend calling depends on your audience

---

## 🚀 DO YOU WANT ME TO IMPLEMENT THIS?

I can add this feature right now! It will include:

1. ✅ Backend API for bulk scheduling
2. ✅ Batch processing with parallel calls
3. ✅ Dashboard UI with:
   - Checkboxes for lead selection
   - "Schedule Calls" button
   - Time picker modal
   - Parallel calls configurator
4. ✅ Monitoring for scheduled batches
5. ✅ Cancel/modify scheduled batches

**Estimated Time**: 2-3 hours total  
**Complexity**: Medium  
**Value**: High (major productivity boost)

---

## 💡 ALTERNATIVE (Quick Workaround)

If you need this NOW without waiting for full UI:

**Manual Bulk Scheduling**:
1. Update Google Sheet:
   - Set `call_status = 'scheduled_bulk'` for leads you want
   - Add new column: `scheduled_time` = "2025-10-14T10:00:00+05:30"
2. Modify orchestrator to check for `scheduled_bulk` status
3. At scheduled time, change status to `pending`
4. Orchestrator picks them up automatically

**Pro**: Quick to implement (15 minutes)  
**Con**: No parallel control, no UI

---

**Should I implement the full bulk scheduling feature with UI and parallel call control?** 🚀
