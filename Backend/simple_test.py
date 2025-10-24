import requests

# Test the models endpoint
try:
    response = requests.get('http://localhost:5000/models')
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        models = response.json()
        print("Available models:")
        for name, info in models.items():
            print(f"  {name}: {info['purpose']}")

        if 'pitch_analysis' in models:
            print("\n🎵 PITCH ANALYSIS MODEL FOUND!")
            pitch_info = models['pitch_analysis']
            print(f"Default: {pitch_info['default_model']}")
            print(f"Available: {pitch_info['available_models']}")
        else:
            print("\n❌ Pitch analysis model not found")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Connection error: {e}")
