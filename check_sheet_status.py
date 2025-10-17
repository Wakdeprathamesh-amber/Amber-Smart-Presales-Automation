#!/usr/bin/env python3
"""Check sheet status and test data reading."""

import os
from src.sheets_manager import SheetsManager
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*80)
print("🔍 CHECKING SHEET STATUS")
print("="*80)

try:
    manager = SheetsManager(
        os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
        os.getenv('LEADS_SHEET_ID')
    )
    
    worksheet = manager.sheet.worksheet("Leads")
    
    # Get all values
    print("\n1️⃣ Reading sheet data...")
    all_values = worksheet.get_all_values()
    print(f"   Total rows: {len(all_values)}")
    
    if len(all_values) <= 1:
        print("   ❌ Sheet is empty or has only headers")
        print("\n💡 Solution: Paste your data into the sheet now, then run this script again")
        exit(0)
    
    # Check headers
    print("\n2️⃣ Checking headers...")
    headers = all_values[0]
    print(f"   Columns: {len(headers)}")
    print(f"   First 10: {headers[:10]}")
    
    empty_headers = [i for i, h in enumerate(headers) if not h or h.strip() == '']
    if empty_headers:
        print(f"   ❌ Empty header cells at positions: {empty_headers}")
        print(f"   This causes: 'header row contains multiple empty cells' error")
    else:
        print(f"   ✅ All headers populated")
    
    # Try get_all_records (what dashboard uses)
    print("\n3️⃣ Testing get_all_records() (dashboard method)...")
    try:
        leads = worksheet.get_all_records()
        print(f"   ✅ SUCCESS! Read {len(leads)} leads")
        
        if len(leads) > 0:
            print(f"\n   Sample lead:")
            lead = leads[0]
            print(f"   - Name: {lead.get('name', 'N/A')}")
            print(f"   - Number: {lead.get('number', 'N/A')}")
            print(f"   - Status: {lead.get('call_status', 'N/A')}")
        
        print("\n✅ Dashboard should be able to read this data!")
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        print(f"\n   This is why dashboard shows 'No leads found'")
        print(f"\n   Error details:")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

