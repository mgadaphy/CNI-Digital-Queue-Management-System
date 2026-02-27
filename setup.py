import os
import sys
import subprocess

def run_setup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, 'src')
    run_script = os.path.join(src_dir, 'run.py')
    
    print("Initializing CNI Queue System Database...")
    try:
        # Execute the setup logic directly inside run.py to guarantee perfect module resolution
        subprocess.check_call([sys.executable, run_script, "--setup"], cwd=src_dir)
    except subprocess.CalledProcessError as e:
        print(f"\\nError: Database initialization failed. Ensure you have activated your virtual environment.")
        sys.exit(1)
        
if __name__ == "__main__":
    run_setup()
