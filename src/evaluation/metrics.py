import collections

def calculate_intent_metrics(gold_cases, predictions):
    """
    Calculates deterministic intent metrics.
    """
    correct = 0
    total = len(gold_cases)
    
    intent_tp = collections.defaultdict(int)
    intent_fp = collections.defaultdict(int)
    intent_fn = collections.defaultdict(int)
    
    multi_correct = 0
    secondary_overlap_total = 0
    secondary_overlap_score = 0.0
    
    missed_secondaries = []
    
    for gold, pred in zip(gold_cases, predictions):
        g_primary = gold.get('primary_intent')
        p_primary = pred.get('primary_intent')
        
        if g_primary == p_primary:
            correct += 1
            intent_tp[g_primary] += 1
        else:
            intent_fn[g_primary] += 1
            intent_fp[p_primary] += 1
            
        g_multi = gold.get('is_multi_intent', False)
        p_multi = pred.get('is_multi_intent', False)
        if g_multi == p_multi:
            multi_correct += 1
            
        g_sec = set(gold.get('secondary_intents', []))
        p_sec = set(pred.get('secondary_intents', []))
        
        if g_sec or p_sec:
            secondary_overlap_total += 1
            if g_sec:
                intersection = len(g_sec.intersection(p_sec))
                secondary_overlap_score += intersection / len(g_sec)
                if intersection < len(g_sec) and g_primary == p_primary:
                    missed_secondaries.append(gold.get('root_tweet_id'))
                    
    accuracy = correct / total if total > 0 else 0
    
    per_intent = {}
    all_intents = set(intent_tp.keys()) | set(intent_fp.keys()) | set(intent_fn.keys())
    for intent in all_intents:
        tp = intent_tp[intent]
        fp = intent_fp[intent]
        fn = intent_fn[intent]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        per_intent[intent] = {"precision": precision, "recall": recall, "f1": f1}
        
    macro_f1 = sum(m["f1"] for m in per_intent.values()) / len(per_intent) if per_intent else 0
    
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_intent": per_intent,
        "multi_intent_accuracy": multi_correct / total if total > 0 else 0,
        "secondary_intent_overlap": secondary_overlap_score / secondary_overlap_total if secondary_overlap_total > 0 else 1.0,
        "cases_missing_secondary": missed_secondaries
    }


def calculate_trust_metrics(gold_cases, predictions):
    """
    Cost-weighted 3-class confusion matrix for Trust Tier.
    Cost mapping (Example):
      Gold=HUMAN, Pred=AUTO -> High Cost (Dangerous miss)
      Gold=AUTO, Pred=HUMAN -> Low Cost (Unnecessary escalation)
    """
    tiers = ["AUTO_HANDLE", "DEEP_ANALYSIS", "HUMAN_ESCALATION"]
    matrix = {g: {p: 0 for p in tiers} for g in tiers}
    
    # Cost weights: matrix[gold][pred]
    costs = {
        "AUTO_HANDLE": {"AUTO_HANDLE": 0, "DEEP_ANALYSIS": 1, "HUMAN_ESCALATION": 2},
        "DEEP_ANALYSIS": {"AUTO_HANDLE": 5, "DEEP_ANALYSIS": 0, "HUMAN_ESCALATION": 1},
        "HUMAN_ESCALATION": {"AUTO_HANDLE": 10, "DEEP_ANALYSIS": 5, "HUMAN_ESCALATION": 0},
    }
    
    total_cost = 0
    
    for gold, pred in zip(gold_cases, predictions):
        g = gold.get('trust_tier', 'HUMAN_ESCALATION') # Default safe
        p = pred.get('trust_tier', 'HUMAN_ESCALATION')
        if g in matrix and p in matrix[g]:
            matrix[g][p] += 1
            total_cost += costs[g][p]
            
    return {
        "confusion_matrix": matrix,
        "total_cost": total_cost,
        "average_cost": total_cost / len(gold_cases) if gold_cases else 0
    }

def calculate_safety_metrics(gold_cases, predictions):
    """
    Measures safety recall, precision, and surfaces dangerous misses.
    """
    tp, fp, fn, tn = 0, 0, 0, 0
    dangerous_misses = []
    
    for gold, pred in zip(gold_cases, predictions):
        g_safe = gold.get('safety') == 'SAFETY_CONCERN'
        p_safe = pred.get('safety') == 'SAFETY_CONCERN'
        
        if g_safe and p_safe:
            tp += 1
        elif g_safe and not p_safe:
            fn += 1
            dangerous_misses.append(gold.get('root_tweet_id'))
        elif not g_safe and p_safe:
            fp += 1
        else:
            tn += 1
            
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    
    return {
        "recall": recall,
        "precision": precision,
        "false_negatives": fn,
        "dangerous_misses": dangerous_misses
    }

def calculate_resolution_metrics(gold_cases, predictions):
    """
    Resolution accuracy and confusion matrix.
    Ensures UNKNOWN != RESOLVED.
    """
    states = ["RESOLVED", "UNRESOLVED", "UNKNOWN"]
    matrix = {g: {p: 0 for p in states} for g in states}
    
    correct = 0
    for gold, pred in zip(gold_cases, predictions):
        g = gold.get('resolution', 'UNKNOWN')
        p = pred.get('resolution', 'UNKNOWN')
        
        if g not in matrix: g = "UNKNOWN"
        if p not in matrix: p = "UNKNOWN"
        
        matrix[g][p] += 1
        if g == p:
            correct += 1
            
    accuracy = correct / len(gold_cases) if gold_cases else 0
    
    return {
        "accuracy": accuracy,
        "confusion_matrix": matrix
    }

def calculate_capability_metrics(gold_cases, predictions):
    correct = 0
    for gold, pred in zip(gold_cases, predictions):
        if gold.get('capability') == pred.get('capability'):
            correct += 1
            
    return {
        "accuracy": correct / len(gold_cases) if gold_cases else 0
    }
