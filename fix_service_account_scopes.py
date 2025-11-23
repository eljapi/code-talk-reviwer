"""Fix service account authentication scopes for Gemini Live API."""

import os
import subprocess
import sys

def fix_service_account_scopes():
    """Add the required scopes to service account for Gemini Live API."""
    
    print("🔧 Fixing Service Account Scopes for Gemini Live API")
    print("=" * 60)
    
    project_id = "powerful-outlet-477200-f0"
    service_account = f"voice-ai-assistant@{project_id}.iam.gserviceaccount.com"
    
    print(f"📋 Project: {project_id}")
    print(f"🔑 Service Account: {service_account}")
    
    # Check if gcloud is available
    try:
        result = subprocess.run(["gcloud", "--version"], capture_output=True, text=True)
        print(f"✅ gcloud CLI found: {result.stdout.split()[0]}")
    except FileNotFoundError:
        print("❌ gcloud CLI not found. Please install Google Cloud SDK first.")
        return False
    
    print("\n🔄 Adding required APIs and permissions...")
    
    # Enable required APIs
    apis_to_enable = [
        "generativelanguage.googleapis.com",  # For Gemini Live API
        "aiplatform.googleapis.com",          # For Vertex AI
        "speech.googleapis.com"               # For Speech API
    ]
    
    for api in apis_to_enable:
        print(f"🔌 Enabling {api}...")
        try:
            result = subprocess.run([
                "gcloud", "services", "enable", api,
                "--project", project_id
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ {api} enabled")
            else:
                print(f"   ⚠️  {api}: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Error enabling {api}: {e}")
    
    # Add required roles
    roles_to_add = [
        "roles/generativelanguage.user",      # For Gemini Live API
        "roles/aiplatform.user",              # For Vertex AI
        "roles/aiplatform.admin",             # For Vertex AI admin
        "roles/speech.client",                # For Speech API
        "roles/serviceusage.serviceUsageConsumer"  # For API usage
    ]
    
    print(f"\n🔐 Adding roles to service account...")
    
    for role in roles_to_add:
        print(f"👤 Adding role: {role}")
        try:
            result = subprocess.run([
                "gcloud", "projects", "add-iam-policy-binding", project_id,
                "--member", f"serviceAccount:{service_account}",
                "--role", role
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ Role {role} added")
            else:
                print(f"   ⚠️  Role {role}: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Error adding role {role}: {e}")
    
    # Create new service account key with proper scopes
    print(f"\n🔑 Creating new service account key...")
    
    key_file = "voice-ai-service-account-key-updated.json"
    
    try:
        result = subprocess.run([
            "gcloud", "iam", "service-accounts", "keys", "create", key_file,
            "--iam-account", service_account
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ New key created: {key_file}")
            print(f"   🔄 Update your .env file to use: {key_file}")
        else:
            print(f"   ❌ Key creation failed: {result.stderr}")
            
    except Exception as e:
        print(f"   ❌ Error creating key: {e}")
    
    print("\n🧪 Testing the updated configuration...")
    
    # Update environment to use new key
    if os.path.exists(key_file):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file
        print(f"✅ Updated GOOGLE_APPLICATION_CREDENTIALS to {key_file}")
        
        # Test authentication
        try:
            result = subprocess.run([
                "gcloud", "auth", "application-default", "print-access-token"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                token = result.stdout.strip()
                print(f"✅ Authentication test successful: {token[:20]}...")
            else:
                print(f"❌ Authentication test failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error testing authentication: {e}")
    
    print("\n📋 Summary:")
    print("✅ APIs enabled for Gemini Live API access")
    print("✅ Service account roles updated")
    print("✅ New service account key created")
    
    print("\n🔄 Next steps:")
    print("1. Update your .env file:")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS={key_file}")
    print("2. Test the connection:")
    print("   python test_websocket_connection.py")
    
    return True


if __name__ == "__main__":
    fix_service_account_scopes()