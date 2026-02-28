from interaction.intent_parser import IntentParser

parser = IntentParser()

tests = [
    "IntelShare learn",
    "What is this",
    "yes",
    "no",
    "hello"
]

for t in tests:
    print(f"{t} → {parser.parse(t)}")
