#!/usr/bin/env python3
"""
Test Route Import - Check if the agent route can be imported
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        print("Testing route import...")
        
        # Test importing the agent routes
        from app.routes.agent import agent_bp
        print("✅ Agent blueprint imported successfully")
        
        # Test importing the app
        from app import create_app
        print("✅ App factory imported successfully")
        
        # Test creating the app
        app = create_app()
        print("✅ App created successfully")
        
        # Check if the route is registered
        with app.app_context():
            print("✅ App context created successfully")
            
            # Check registered routes
            for rule in app.url_map.iter_rules():
                if 'agent' in rule.rule:
                    print(f"Found agent route: {rule.rule} -> {rule.endpoint}")
        
        print("\n🎯 All imports successful! The issue might be Flask not reloading.")
        print("Try stopping Flask completely and restarting it.")
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
