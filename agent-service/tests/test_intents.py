from app.domain.intents import classify_question


def test_clasifica_pregunta_de_chips() -> None:
    intent = classify_question("¿Me afecta que China restrinja la exportación de chips?")

    assert intent.mentions_chips is True


def test_clasifica_retiro() -> None:
    intent = classify_question("¿Puedo retirar $5,000 hoy?")

    assert intent.asks_withdrawal is True


def test_clasifica_recomendacion() -> None:
    intent = classify_question("¿Debería vender NVDA?")

    assert intent.requests_recommendation is True


def test_clasifica_pregunta_simple() -> None:
    intent = classify_question("¿Qué es un ETF?")

    assert intent.mentions_chips is False
    assert intent.requests_recommendation is False
    assert intent.asks_withdrawal is False
