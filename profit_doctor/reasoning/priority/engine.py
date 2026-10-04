"""Non-weighted attention rules; no monetary thresholds or human decisions."""
from .contracts import PriorityBasis, PriorityResult


def evaluate(basis):
    basis = PriorityBasis.from_json(basis.to_json())
    names = ('materiality', 'evidence_strength', 'urgency', 'controllability', 'persistence')
    gaps = tuple(name+': '+getattr(basis, name).reason for name in names
                 if getattr(basis, name).state == 'NOT_ASSESSED')
    m, e, u, p = (getattr(basis, n).state for n in ('materiality', 'evidence_strength', 'urgency', 'persistence'))
    level, rule = 'INSUFFICIENT_EVIDENCE', 'NO_QUALIFIED_CLASSIFICATION'
    if e == 'STRONG':
        if m == 'HIGH' and u == 'CRITICAL':
            level, rule = 'CRITICAL', 'MATERIAL_IMMINENT_CONSEQUENCE'
        elif m == 'HIGH' and u == 'HIGH':
            level, rule = 'HIGH', 'MATERIAL_URGENT_CONSEQUENCE'
        elif m == 'HIGH' and p in ('RECURRING', 'STRUCTURAL', 'WORSENING'):
            level, rule = 'HIGH', 'MATERIAL_CONTINUING_CONDITION'
        elif m in ('LOW', 'MEDIUM', 'HIGH') and p == 'HISTORICAL_ONLY' and u == 'LOW':
            level, rule = 'LOW', 'HISTORICAL_NO_CONTINUING_CONSEQUENCE'
        elif m == 'MEDIUM' and u == 'MEDIUM':
            level, rule = 'MEDIUM', 'EVIDENCED_MODERATE_ATTENTION'
    reasons = (rule,) + tuple(name+': '+getattr(basis, name).state+' — '+getattr(basis, name).reason for name in names)
    return PriorityResult(classification=level, rule=rule, reasons=reasons, gaps=gaps, basis=basis)
