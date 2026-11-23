"""Tests for the instructions the agent receives."""

from datetime import date

from app.agent.prompt import (
    ANSWER_INSTRUCTION,
    SUFFICIENCY_SYSTEM,
    SYSTEM,
    build_system_prompt,
)

PROMPT = " ".join(SYSTEM.split())
FINAL_INSTRUCTION = " ".join(ANSWER_INSTRUCTION.split())
VERIFIER = " ".join(SUFFICIENCY_SYSTEM.split())


def test_prompt_pide_los_tres_bloques_del_analisis_de_portafolio() -> None:
    assert "Lo bueno" in PROMPT
    assert "Lo malo" in PROMPT
    assert "Qué revisar" in PROMPT


def test_prompt_limita_las_recomendaciones_a_observaciones_educativas() -> None:
    assert "observaciones educativas" in PROMPT
    assert "no como órdenes de compra o venta" in PROMPT


def test_prompt_refuerza_scenario_impact_para_me_afecta() -> None:
    assert "no basta con analyze_portfolio" in PROMPT
    assert "scenario_impact en el mismo turno" in PROMPT


def test_instruccion_final_no_pierde_la_regla_de_no_inventar() -> None:
    assert "No inventes" in PROMPT or "No inventes" in FINAL_INSTRUCTION


def test_verificador_exige_escenario_numerico_para_preguntas_de_impacto() -> None:
    assert "impacto en el dinero del usuario" in VERIFIER
    assert "no hay un resultado de scenario_impact" in VERIFIER


def test_verificador_no_acepta_exposicion_sin_escenario() -> None:
    assert "La exposición de analyze_portfolio no alcanza" in VERIFIER


def test_verificador_sugiere_scenario_impact_cuando_falta_el_escenario() -> None:
    assert "next_tool=scenario_impact" in VERIFIER


def test_prompt_incluye_la_fecha_de_hoy() -> None:
    prompt = build_system_prompt(date(2026, 11, 23))

    assert "Fecha de hoy: 2026-11-23" in prompt
    assert "{today}" not in prompt


def test_prompt_ya_no_limita_a_una_sola_busqueda() -> None:
    assert "busca una vez" not in PROMPT.lower()
    assert "una sola búsqueda" not in PROMPT.lower()


def test_prompt_exige_verificar_el_estado_actual() -> None:
    assert "estado actual" in PROMPT
    assert "sigue fuera o si volvió" in PROMPT
    assert "Máximo 3 búsquedas" in PROMPT


def test_prompt_pide_escenarios_en_ambas_direcciones() -> None:
    assert "ambas direcciones" in PROMPT
    assert "no solo a la baja" in FINAL_INSTRUCTION


def test_prompt_resuelve_conflictos_por_tipo() -> None:
    assert "información desactualizada" in PROMPT
    assert "gana la fuente más reciente" in PROMPT


def test_prompt_usa_secciones_para_separar_reglas() -> None:
    for section in (
        "<rol>",
        "<contexto_de_sesion>",
        "<herramientas>",
        "<protocolo_noticias>",
        "<grounding>",
        "<formato>",
        "<incertidumbre>",
    ):
        assert section in SYSTEM


def test_verificador_detecta_evidencia_desactualizada() -> None:
    assert "stale_evidence" in VERIFIER
    assert "estado actual" in VERIFIER
    assert "conflict_type" in VERIFIER


def test_prompt_tiene_protocolo_de_decision() -> None:
    assert "<protocolo_decision>" in SYSTEM
    assert "Si vendes" in PROMPT
    assert "Qué cambiaría la decisión" in PROMPT
    assert 'No digas "vende" ni "no vendas"' in PROMPT


def test_prompt_separa_recomendacion_general_de_decision_de_venta() -> None:
    assert "<protocolo_recomendacion>" in SYSTEM
    assert "sin referirse a vender o comprar un ticker concreto" in PROMPT
    assert "No uses simulate_sale ni estimate_withdrawal" in PROMPT
    assert "Dónde estás" in PROMPT
    assert "Opciones" in PROMPT


def test_verificador_no_exige_simulate_sale_para_recomendacion_general() -> None:
    assert "decisión de venta, compra o mantenimiento de un ticker concreto" in VERIFIER
    assert "recomendación general de inversión o diversificación" in VERIFIER
    assert "no hay analyze_portfolio" in VERIFIER


def test_prompt_infiere_la_necesidad_de_noticias() -> None:
    assert "Infiere la necesidad del sentido de la pregunta" in PROMPT
    assert "no de palabras sueltas" in PROMPT


def test_prompt_prohibe_cierres_genericos_sin_cifra() -> None:
    assert "Conviene vigilar" in PROMPT
    assert "sin una cifra" in PROMPT


def test_prompt_lee_la_emocion_de_la_persona() -> None:
    assert "<lectura_de_la_persona>" in SYSTEM
    assert "miedo" in PROMPT
    assert "no lo ignores" in PROMPT.lower()


def test_prompt_no_cita_herramientas_como_fuentes() -> None:
    assert "nombres de herramientas" in PROMPT


def test_verificador_evalua_la_intencion_no_palabras_clave() -> None:
    assert "sentido de la pregunta" in VERIFIER
    assert "no busques palabras clave" in VERIFIER


def test_verificador_rechaza_noticias_que_no_son_del_tema() -> None:
    assert "no tratan del tema" in VERIFIER
    assert "nombre exacto de la empresa" in VERIFIER


def test_prompt_prohibe_inferir_ausencia_de_evidencia() -> None:
    assert "No interpretes la ausencia de noticias" in PROMPT
