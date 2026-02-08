import os
import sys
import subprocess
import platform

def create_virtual_environment():
    """Create virtual environment if it doesn't exists"""
    venv_dir = 'venv'
    
    if not os.path.exists(venv_dir):
        subprocess.check_call([sys.executable, '-m', 'venv', venv_dir])
        print(f"Virtual environment created at {venv_dir}")
        
        # Install pip and setuptools
        if platform.system() == "Windows":
            pip_path = os.path.join(venv_dir, "Scripts", "pip")
        else:
            pip_path = os.path.join(venv_dir, "bin", "pip")
            
        subprocess.check_call([pip_path, "install", "--upgrade", "pip", "setuptools"])
        return True
    else:
        print("Virtual environment already exists")
        return False
    
def install_requirements():
        """Install requirements virtual environment"""
        system = platform.system()
        
        if system == "Windows":
            pip_path = os.path.join("venv", "Scripts", "pip")
            python_path = os.path.join("venv", "Scripts", "python")
        else:
            pip_path = os.path.join("venv", "bin", "pip")
            python_path = os.path.join("venv", "bin", "python")
            
        print(f"Using Python: {python_path}")
        print(f"Using Pip: {pip_path}")
        
        # Install requirements
        print("Installing requirements...")
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
        
        return python_path
    
def setup_environment():
    """Setup the development environment"""
    print("Setting up Vision Assistant Environment...")
    
    # Create necessary directions
    directories = [
        'database',
        'ai_modules',
        'features',
        'utils',
        'logs',
        'models',
        'data',
        'config'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
        
        # Create virtual environment
        create_virtual_environment()
        
        # Install requirements
        python_path = install_requirements()
        
        # Download models
        print("Downloading AI Models...")
        download_models(python_path)
        
        # Create configuration files
        create_config_files()
        
        print("\n" + "="*50)
        print("SETUP COMPLETE!")
        print("="*50)
        
def download_models(python_path):
    """Download necessary AI Models"""
    print("Note: Models will be downloaded on first run.")
    
    # Create a script to download models
    download_script = """
    import torch
    import cv2
    from transformers import pipeline
    print("PyTorch version:", torch.__version__)
    print("OpenCV version:", cv2.__version__)
    print("Models will be downloaded automatically on first use")
    """
    
    with open("check_models.py", "w") as f:
        f.write(download_script)
        
    # Run the script
    subprocess.check_call([python_path, "check_models.py"])
    os.remove("check_models.py")
    
def create_config_files():
    """Create configuration files if they don't exist"""
    
    # Create .env file
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("""# API Keys Configuration
                    OPENAI_API_KEY=your_openai_api_key_here
                    GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
                    WEATHER_API_KEY=your_weather_api_key_here
                    
                    # Database Configuration
                    DATABASE_URL=sqlite:///database/vision_assistant.db
                    
                    # Application Settings
                    DEBUG=True
                    LOG_LEVEL=INFO
                    
                    # Speech Settings
                    DEFAULT_LANGUAGE=en
                    SPEECH_RATE=150
                    USE_GOOGLE_TTS=False
                    
                    # Vision Settings
                    CAMERA_INDEX=0
                    DETECTION_CONFIDENCE=0.5
                    
                    # Emergency Contacts (comma separated)
                    EMERGENCY_CONTACTS=+1234567890,family@email.com
                    """)
            print("Created .env file - Please update with your API keys")
            
    # Create config .yaml if not exists
    if not os.path.exists('config.yaml'):
        with open('config.yaml', 'w') as f:
            f.write("""app:
                    name: "Vision Assistant for Visually Impaired (AIForUs)"
                    version: "0.0.1"
                    debug: true
                    
                    ai:
                    llm_provider: "openai"
                    local_model: "microsoft/DialoGPT-small"
                    vision_model: "yolov8n"
                    text_model: "easyocr"
                    
                    speech:
                    default_language: "en"
                    speech_rate: 150
                    use_google_tts: false
                    
                    user:
                    default_name: "User"
                    disability_type: "visual_impaired"
                    emergency_contacts: ["+1234567890", "family@email.com"]
                    
                    database:
                    path: "database/vision_assistant.db"
                    backup_hours: 24
                    
                    logging:
                    level: "INFO"
                    file: "logs/app.log"
                    max_size_mb: 10
                    """)
            print("Created config.yaml")
            
def create_activation_scripts():
    """Create scripts to activate virtual environment"""
    system = platform.system()
    
    if system == "Windows":
        """Create activation script for Windows"""
        with open("activate_env.bat", "w") as f:
            f.write("""@echo off
                    echo Activating Virtual Environment...
                    call venv\\Scripts\\activate.bat
                    echo Environment activated!
                    echo.
                    echo To run the application: python app.py
                    echo.
                    cmd /k
                    """)
            
        # Create run script for Windows
        with open("run.bat", "w") as f:
            f.write("""@echo off
                    echo Starting Vision Assistant...
                    call venv\\Scripts\\activate.bat
                    python app.py
                    pause
                    """)
            
            print("Created Windows scripts: activate_env.bat, run.bat")
            
    else: # Linux/Mac
        # Create activation script for Unix
        with open("activate_env.sh", "w") as f:
            f.write("""#!/bin/bash
                    echo "Activating Virtual Environment..."
                    echo "Activating Virtual Environment..."
                    source venv/bin/activate
                    echo "Environment activated!"
                    echo ""
                    echo "To run the application: python app.py"
                    echo ""
                    exec $SHELL
                    """)
            os.chmod("activate_env.sh", 0o755)
                    
            # Create run script for Unix
            with open("run.sh", "w") as f:
                f.write("""#!/bin/bash
                    echo "Starting Vision Assistant...
                    source venv/bin/activate
                    python app.py
                    """)
                os.chmod("run.sh", 0o755)
                    
                print("Created Unix scripts: activate_env.sh, run.sh")
        
def check_system():
    """Check system requirements"""
    print("\n" + "="*50)
    print("SYSTEM CHECK")
    print("="*50)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("WARNING: Python 3.8 or higher is recommended")
    else:
        print("Python version OK")
        
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        print(f"Free disk space: {free_gb} GB")
        
        if free_gb <5:
            print("WARNING: Low disk space (<5GB)")
    except:
        pass
    
    print("\nRequired components:")
    print("1. Camera (webcam or external)")
    print("2. Microphone")
    print("3. Speakers or headphones")
    print("4. Internet connection (for some features)")
    
    if __name__ == "__main__":
        print("="*50)
        print("VISION ASSISTANT (AIForUs) - DEVELOPMENT SETUP")
        print("="*50)
        
        try:
            setup_environment()
            create_activation_scripts()
            check_system()
            
            print("\n" + "="*50)
            print("NEXT STEPS:")
            print("="*50)
            print("1. Edit the '.env' file and add your API keys")
            print("2. Activate the virtual environment")
            
            if platform.system() == "Windows":
                print(" Run: activate_env.bat")
                print(" OR: venv\\Scripts\\activate.bat")
                print(" Then run: python app.py")
                print(" OR just double-click: run.bat")
            else:
                print(" Run: source activate_env.sh")
                print(" OR: source venv/bin/activate")
                print(" Then run: python app.py")
                print(" OR: ./run.sh")
                
            print("\n3. For first time setup, you might need to:")
            print(" - Allow camera/microphone access")
            print(" - Install system dependencies (if prompted)")
            print("\nEnjoy your Vision Assistant")
            
        except Exception as e:
            print(f"\nSetup failed: {e}")
            print("\nManual setup:")
            print("1. python -m venv venv")
            print("2. source venv/bin/activate # or venv\\Scripts\\activate.bat")
            print("3. pip install -r requirements.txt")
            print("4. python app.py")