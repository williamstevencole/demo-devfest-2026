from app.agent.trace import TraceSpan

KIND_TOOL_CALL = "tool_call"


def test_trace_span_mide_duracion() -> None:
    events = []
    ticks = iter([10.0, 10.042])
    span = TraceSpan(
        events.append,
        "load_portfolio",
        KIND_TOOL_CALL,
        "Portafolio",
        clock=lambda: next(ticks),
    )

    span.finish("ok", [])

    assert events[0]["status"] == "running"
    assert events[1]["duration_ms"] == 42


def test_trace_span_reutiliza_el_id_entre_running_y_done() -> None:
    events = []
    span = TraceSpan(events.append, "naive", "retrieval", "Buscar")

    span.finish("ok", [])

    assert events[0]["id"] == events[1]["id"]
    assert events[0]["id"]


def test_trace_span_usa_ids_distintos_por_operacion() -> None:
    events = []
    first = TraceSpan(events.append, "naive", "retrieval", "Buscar")
    second = TraceSpan(events.append, "naive", "answer", "Redactar")

    first.finish("ok", [])
    second.finish("ok", [])

    assert events[0]["id"] != events[1]["id"]
