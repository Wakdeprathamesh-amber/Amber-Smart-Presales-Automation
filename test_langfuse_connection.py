#!/usr/bin/env python3
"""
Quick test script to verify LangFuse connection.
Run this after adding LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to .env
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("\n" + "="*60)
print("🔍 LangFuse Connection Test")
print("="*60 + "\n")

# Check if keys are set
public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
secret_key = os.getenv('LANGFUSE_SECRET_KEY')
host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
enabled = os.getenv('ENABLE_OBSERVABILITY', 'true').lower() == 'true'

print("📋 Configuration Check:")
print(f"  ENABLE_OBSERVABILITY: {enabled}")
print(f"  LANGFUSE_HOST: {host}")
print(f"  LANGFUSE_PUBLIC_KEY: {'✅ Set' if public_key else '❌ Missing'}")
print(f"  LANGFUSE_SECRET_KEY: {'✅ Set' if secret_key else '❌ Missing'}")
print()

if not enabled:
    print("⚠️  Observability is disabled (ENABLE_OBSERVABILITY=false)")
    print("   Set to 'true' in .env to enable LangFuse")
    sys.exit(1)

if not public_key or not secret_key:
    print("❌ LangFuse credentials not configured!")
    print("\n📝 To fix:")
    print("   1. Go to https://cloud.langfuse.com")
    print("   2. Create account and project")
    print("   3. Go to Settings → API Keys")
    print("   4. Copy keys and add to .env:")
    print("      LANGFUSE_PUBLIC_KEY=pk-lf-...")
    print("      LANGFUSE_SECRET_KEY=sk-lf-...")
    sys.exit(1)

# Test connection
print("🔌 Testing connection to LangFuse...")

try:
    from src.observability import get_langfuse_client, log_conversation_message
    
    client = get_langfuse_client()
    
    if client is None:
        print("❌ LangFuse client failed to initialize")
        print("   Check your keys are correct")
        sys.exit(1)
    
    print("✅ LangFuse client initialized successfully!\n")
    
    # Create a test trace
    print("📝 Creating test trace...")
    test_trace = client.trace(
        name="connection_test",
        user_id="test-user-001",
        metadata={
            "test": True,
            "source": "test_langfuse_connection.py",
            "timestamp": "2025-10-10"
        },
        tags=["test", "connection_check"]
    )
    print("✅ Test trace created!")
    
    # Create a test message
    print("📝 Logging test message...")
    log_conversation_message(
        lead_uuid="test-user-001",
        channel="test",
        direction="out",
        content="This is a test message from connection script",
        metadata={"test": True, "source": "test_script"}
    )
    print("✅ Test message logged!")
    
    # Flush to ensure data is sent
    print("📤 Flushing events to LangFuse...")
    client.flush()
    print("✅ Events flushed!")
    
    print("\n" + "="*60)
    print("🎉 SUCCESS! LangFuse is fully connected!")
    print("="*60)
    print("\n👉 Next steps:")
    print("   1. Go to https://cloud.langfuse.com")
    print("   2. Select your project")
    print("   3. Click 'Traces' in the left sidebar")
    print("   4. You should see 'connection_test' trace!")
    print("\n✨ Your observability is now active!")
    print("   Every call, webhook, and workflow will be traced.\n")
    
    sys.exit(0)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n📦 Install dependencies:")
    print("   ./venv/bin/pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    print("\n🔧 Troubleshooting:")
    print("   1. Verify keys are correct (no extra spaces)")
    print("   2. Check network connection")
    print("   3. Try setting LANGFUSE_DEBUG=true in .env")
    print("   4. Check LangFuse status: https://status.langfuse.com")
    sys.exit(1)

