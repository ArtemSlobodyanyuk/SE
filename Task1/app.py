from flask import Flask, jsonify
import random
import datetime

app = Flask(__name__)

facts = [
    "Python названий на честь Monty Python, а не змії",
    "Перший комп'ютерний баг був справжнім жуком — молем",
    "Linux працює на 96.3% серверів у світі",
    "Docker написаний мовою Go",
    "Перший вебсайт досі працює — info.cern.ch",
]

@app.route("/")
def home():
    return jsonify({
        "message": "Привіт з Docker-контейнера! 🐳",
        "student": "Тут впиши своє ім'я",
        "time": datetime.datetime.now().isoformat()
    })

@app.route("/fact")
def random_fact():
    return jsonify({"fact": random.choice(facts)})

@app.route("/dice")
def roll_dice():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return jsonify({
        "dice": [d1, d2],
        "total": d1 + d2,
        "doubles": d1 == d2
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
