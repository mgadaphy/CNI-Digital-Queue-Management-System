import os
import sys
import subprocess

def install_requirements(base_dir):
    """Install requirements, handling packages that need binary wheels on Windows"""
    req_file = os.path.join(base_dir, 'requirements.txt')
    if not os.path.exists(req_file):
        return
    
    print("Installing dependencies...")
    
    # First, install packages that commonly fail to compile from source on Windows
    # cffi and cryptography need C++ Build Tools if not installed as binary wheels
    binary_packages = ['cffi', 'cryptography']
    for pkg in binary_packages:
        subprocess.call([sys.executable, '-m', 'pip', 'install', pkg, '--only-binary=:all:', '-q'])
    
    # Now install the full requirements list
    result = subprocess.call([sys.executable, '-m', 'pip', 'install', '-r', req_file, '-q'])
    if result != 0:
        print("\nWarning: Some packages may not have installed correctly.")
        print("If you see errors about C++ Build Tools, run:")
        print("  pip install cryptography cffi --only-binary=:all:")
        print("  pip install -r requirements.txt")

def run_setup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, 'src')
    run_script = os.path.join(src_dir, 'run.py')
    
    install_requirements(base_dir)
    
    print("Initializing CNI Queue System Database...")
    try:
        # Execute the setup logic directly inside run.py to guarantee perfect module resolution
        subprocess.check_call([sys.executable, run_script, "--setup"], cwd=src_dir)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Database initialization failed. Ensure you have activated your virtual environment.")
        sys.exit(1)
        
if __name__ == "__main__":
    run_setup()
