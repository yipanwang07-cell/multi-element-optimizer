"""JavaFoil PolarCard stall-model IDs (SM_CALCFOIL, SM_EPPLER, SM_NONE)."""
STALL_MODELS = {0: "Calcfoil", 1: "Eppler", 2: "None"}
DEFAULT_STALL_MODEL = 1


def stall_model_id(value=DEFAULT_STALL_MODEL):
    if type(value) is not int or value not in STALL_MODELS:
        raise ValueError("Stall model must be 0 (Calcfoil), 1 (Eppler), or 2 (None)")
    return value


def stall_model_name(value=DEFAULT_STALL_MODEL):
    return STALL_MODELS[stall_model_id(value)]
