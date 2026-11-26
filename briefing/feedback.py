"""Feedback-CLI: Vorlieben speichern, die die KI-Bewertung verbessern.

  python -m briefing.feedback add positive "Mehr Homelab-Schnäppchen"
  python -m briefing.feedback add negative "Kein Hollywood-Klatsch"
  python -m briefing.feedback list
"""
import sys

from briefing import db


def main():
    argv = sys.argv[1:]
    if len(argv) >= 3 and argv[0] == "add" and argv[1] in ("positive", "negative"):
        db.add_feedback(argv[1], " ".join(argv[2:]))
        print("Gespeichert.")
        return
    fb = db.load_feedback()
    print("Positiv:")
    for e in fb["positive"]:
        print(f"  + {e}")
    print("Negativ:")
    for e in fb["negative"]:
        print(f"  - {e}")


if __name__ == "__main__":
    main()
