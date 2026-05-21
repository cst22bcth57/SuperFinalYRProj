HOW TO RUN

1. Open terminal in project folder

2. Install Django
   pip install django

3. Make sure these files exist in root folder:
   - schemes.json
   - eligibility_engine.py
   - intent_detection.py

4. Run server
   python manage.py runserver

5. Open browser
   http://127.0.0.1:8000/

FEATURES
- Browser Speech-to-Text (Web Speech API)
- Browser Text-to-Speech
- Django backend
- Uses your existing test_manual.py logic