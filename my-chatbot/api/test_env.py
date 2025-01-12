#!/usr/bin/env python3
# api/test_env.py
import os
from dotenv import load_dotenv

def test_environment():
    load_dotenv()
    
    # Check for required environment variables
    required_vars = {
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY")
    }
    
    print("Environment Variables Check:")
    for var_name, value in required_vars.items():
        if value:
            print(f"✓ {var_name} is set")
            print(f"  Length: {len(value)} characters")
        else:
            print(f"✗ {var_name} is NOT set")
    
    # Test Python packages
    print("\nPython Packages Check:")
    packages = ["pinecone", "sentence_transformers", "groq", "dotenv"]
    
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError as e:
            print(f"✗ {package} is NOT installed: {str(e)}")

if __name__ == "__main__":
    test_environment()