# Evaluación offline con RAGAS

Evalúa **solo el RAG del corpus**, sin grafo, sin portafolio y sin web.

```text
pregunta → NaiveChat → Chroma → respuesta
```

## Instalación

```bash
cd agent-service
.venv/bin/pip install -r requirements-eval.txt
```

## Ejecutar

```bash
cd agent-service
make eval
# o solo las primeras 2 preguntas
.venv/bin/python -m eval.run_ragas --limit 2
```

Los resultados se guardan en `eval/results/ragas-<timestamp>.json`.

## Métricas

- `faithfulness`: que la respuesta se sostenga en los contextos recuperados.
- `answer_relevancy`: que la respuesta conteste la pregunta.
- `context_precision`: que los contextos recuperados sean útiles.
- `context_recall`: que el retrieval haya traído lo necesario para cubrir la
  respuesta de referencia.

`answer_correctness` necesita una referencia más estricta; se puede agregar
después.

## Alcance

RAGAS no evalúa:

- llamadas a tools;
- identidad;
- cálculos de exposición o retiro;
- elección de fuentes;
- trayectoria del agente.

Eso se cubre con los tests deterministas del agente.

## Versiones

El eval usa `ragas==0.4.4`. RAGAS 0.4 ya no importa el módulo antiguo
`langchain_community.chat_models.vertexai`, así que el script no necesita el shim
de compatibilidad que usaba con 0.2.x.

RAGAS declara `scikit-network` como dependencia, pero solo la usa para generar
grafos de testset, que este eval no utiliza. Se fija `scikit-network==0.12.1`
porque es pure Python y tiene wheel para Python 3.14; las versiones nuevas
requieren compilar C++.
