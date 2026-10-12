"""JavaFoil's one-based transition IDs and published Reynolds guidance.
Source: https://www.mh-aerotools.de/airfoils/jf_analysis_boundarylayer.htm
Missing recommendations are intentionally not extrapolated.
"""
TRANSITION_MODELS = {
    1: ("Eppler 1 (standard)", "Re > 100,000"),
    2: ("Eppler 2 (extended)", "Re > 100,000"),
    3: ("Michel 1", "Re > 2,000,000"),
    4: ("Michel 2", "Re > 2,000,000"),
    5: ("H12-Re(s)", "Re guidance not published"),
    6: ("Granville", "Re > 5,000,000"),
    7: ("Drela e^n (before 1991)", "Re guidance not published"),
    8: ("Drela e^n (after 1991)", "Re guidance not published"),
    9: ("Arnal e^n (Wurz)", "Re guidance not published"),
}


def transition_model_id(value=1):
    if type(value) is not int or value not in TRANSITION_MODELS:
        raise ValueError("Transition model must be an integer from 1 to 9 (JavaFoil IDs)")
    return value


def transition_model_name(value=1):
    return TRANSITION_MODELS[transition_model_id(value)][0]


def transition_model_label(value=1):
    return " - ".join(TRANSITION_MODELS[transition_model_id(value)])
