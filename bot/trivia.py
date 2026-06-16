import random

TRIVIA_QUESTIONS = [
    {"q": "Which country has won the most FIFA World Cups?", "a": "brazil", "choices": ["Brazil", "Germany", "Italy", "Argentina"]},
    {"q": "Who scored the famous 'Hand of God' goal?", "a": "maradona", "choices": ["Maradona", "Pelé", "Zidane", "Ronaldo"]},
    {"q": "In which year was the first FIFA World Cup held?", "a": "1930", "choices": ["1930", "1934", "1924", "1928"]},
    {"q": "Which country hosted the 2022 FIFA World Cup?", "a": "qatar", "choices": ["Qatar", "UAE", "Saudi Arabia", "Bahrain"]},
    {"q": "Who won the Golden Boot at the 2022 World Cup?", "a": "mbappe", "choices": ["Mbappé", "Messi", "Ronaldo", "Benzema"]},
    {"q": "How many teams participate in the FIFA World Cup finals?", "a": "32", "choices": ["32", "24", "16", "48"]},
    {"q": "Which goalkeeper has the most World Cup clean sheets?", "a": "peter shilton", "choices": ["Peter Shilton", "Buffon", "Casillas", "Neuer"]},
    {"q": "Who is the all-time top scorer in World Cup history?", "a": "miroslav klose", "choices": ["Miroslav Klose", "Ronaldo", "Gerd Müller", "Pelé"]},
    {"q": "Which country won the 2018 FIFA World Cup?", "a": "france", "choices": ["France", "Croatia", "Belgium", "England"]},
    {"q": "Who won the Golden Ball at the 2022 World Cup?", "a": "messi", "choices": ["Messi", "Mbappé", "Modric", "Benzema"]},
    {"q": "Which nation has hosted the World Cup the most times?", "a": "brazil", "choices": ["Brazil", "Mexico", "Italy", "Germany"]},
    {"q": "What was the highest-scoring World Cup game?", "a": "austria 7-5 switzerland", "choices": ["Austria 7-5 Switzerland", "Brazil 8-0 Sweden", "Germany 7-1 Brazil", "Hungary 10-1 El Salvador"]},
    {"q": "How long is each half in a World Cup match?", "a": "45 minutes", "choices": ["45 minutes", "40 minutes", "50 minutes", "35 minutes"]},
    {"q": "Which World Cup had the fastest ever goal?", "a": "2002", "choices": ["2002", "1998", "2006", "1994"]},
    {"q": "Hakan Şükür scored the fastest World Cup goal in how many seconds?", "a": "11", "choices": ["11", "8", "15", "20"]},
    {"q": "Which player received the most red cards in World Cup history?", "a": "rigobert song", "choices": ["Rigobert Song", "Zidane", "Cafu", "Ramos"]},
    {"q": "Germany's 7-1 win over Brazil was in which World Cup?", "a": "2014", "choices": ["2014", "2010", "2018", "2006"]},
    {"q": "How many goals did Mbappé score at the 2022 World Cup final?", "a": "3", "choices": ["3", "2", "1", "4"]},
    {"q": "Which team did Italy beat in the 2006 World Cup final?", "a": "france", "choices": ["France", "Germany", "Portugal", "Brazil"]},
    {"q": "Ronaldo (Brazil) scored how many goals in the 2002 World Cup?", "a": "8", "choices": ["8", "6", "7", "5"]},
    {"q": "Who has the record for most World Cup appearances as a player?", "a": "lothar matthaus", "choices": ["Lothar Matthäus", "Pelé", "Cafu", "Messi"]},
    {"q": "Which country won the first ever Women's World Cup?", "a": "usa", "choices": ["USA", "Germany", "Norway", "Brazil"]},
    {"q": "The 2026 World Cup will be hosted by which countries?", "a": "usa canada mexico", "choices": ["USA, Canada, Mexico", "USA, Canada, Brazil", "USA, Mexico, Argentina", "Canada, Mexico, Colombia"]},
    {"q": "Which player scored a hat-trick in the 2022 World Cup final?", "a": "mbappe", "choices": ["Mbappé", "Messi", "Griezmann", "Giroud"]},
    {"q": "Pelé won how many World Cups?", "a": "3", "choices": ["3", "2", "1", "4"]},
    {"q": "Which country's team is nicknamed 'The Samba Boys'?", "a": "brazil", "choices": ["Brazil", "Argentina", "Colombia", "Uruguay"]},
    {"q": "How many countries qualify for the 2026 World Cup?", "a": "48", "choices": ["48", "32", "40", "36"]},
    {"q": "Who was England's goalkeeper in the 1966 World Cup winning team?", "a": "gordon banks", "choices": ["Gordon Banks", "Peter Shilton", "Ray Clemence", "David Seaman"]},
    {"q": "Argentina's Lionel Messi won his first World Cup in which year?", "a": "2022", "choices": ["2022", "2014", "2018", "2010"]},
    {"q": "Which African team reached the World Cup semi-finals in 2022?", "a": "morocco", "choices": ["Morocco", "Senegal", "Ghana", "Nigeria"]},
]


def get_random_question():
    q = random.choice(TRIVIA_QUESTIONS)
    choices = q["choices"].copy()
    random.shuffle(choices)
    return {
        "question": q["q"],
        "answer": q["a"].lower(),
        "choices": choices,
        "correct_display": choices[0] if choices[0].lower() == q["a"].lower()
        else next((c for c in choices if c.lower() == q["a"].lower()), choices[0])
    }


def check_answer(question_data: dict, user_answer: str) -> bool:
    return question_data["answer"] in user_answer.lower()
