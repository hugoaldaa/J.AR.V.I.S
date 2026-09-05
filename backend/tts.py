import pyttsx3

def speak(text: str):
    engine = pyttsx3.init("sapi5")
    engine.setProperty("rate", 175)
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()