import json
from typing import Dict, Any, List

class TrustGate:
    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def evaluate(self, 
                 context: Dict[str, Any], 
                 loop_state: Dict[str, Any], 
                 generation_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluates context and loop state to determine the Trust Tier.
        Returns:
            {
                "tier": "AUTO_HANDLE" | "DEEP_ANALYSIS" | "HUMAN_ESCALATION",
                "reasons": list of strings explaining the decision,
                "handoff_payload": Optional structured handoff if HUMAN_ESCALATION
            }
        """
        reasons = []
        
        # 1. HARD SAFETY / HUMAN RULES
        if context.get("explicit_human_request"):
            reasons.append("explicit_human_request")
            return self._create_decision("HUMAN_ESCALATION", reasons, context)
            
        if context.get("safety_legal_concern"):
            reasons.append("safety_legal_concern")
            return self._create_decision("HUMAN_ESCALATION", reasons, context)
            
        if context.get("suspicious_identity"):
            reasons.append("suspicious_identity")
            return self._create_decision("HUMAN_ESCALATION", reasons, context)

        # 2. LOOP BREAKER STATE
        da_attempts = loop_state.get("deep_analysis_attempts", 0)
        still_persists = loop_state.get("issue_persists", False)
        repeated_complaints = loop_state.get("repeated_complaints", 0)
        
        if da_attempts >= 1 and still_persists:
            reasons.append("persistent_loop_after_deep_analysis")
            return self._create_decision("HUMAN_ESCALATION", reasons, context)
            
        # 3. CAPABILITY, INTENT, AND GENERATION EVIDENCE
        # If we reach here, no hard Human rule is met. Default assumption is AUTO if perfect, else DEEP.
        is_auto = True
        
        intent = context.get("predicted_intent", "UNKNOWN")
        confidence = context.get("intent_confidence", 0.0)
        
        if intent == "UNKNOWN":
            is_auto = False
            reasons.append("ambiguous_intent")
            
        if confidence < self.confidence_threshold:
            is_auto = False
            reasons.append("low_intent_confidence")
            
        capability_state = context.get("capability_state", {})
        # If any capability is explicitly UNKNOWN, route to Deep Analysis to verify
        for k, v in capability_state.items():
            state_str = v.get("status") if isinstance(v, dict) else v
            if state_str == "UNKNOWN":
                is_auto = False
                reasons.append(f"unknown_capability_{k}")
                
        # If generation explicitly removed unsupported claims or requested routing
        if generation_result and generation_result.get("routed_to_deep_analysis"):
            is_auto = False
            reasons.append("unsupported_generation_claim")
            
        # First repeated complaint or strong loop signal that hasn't exhausted Deep Analysis yet
        if repeated_complaints >= 1:
            is_auto = False
            reasons.append(f"repeated_complaint_count_{repeated_complaints}")

        if is_auto:
            return self._create_decision("AUTO_HANDLE", ["high_confidence_safe_complete"], None)
        else:
            return self._create_decision("DEEP_ANALYSIS", reasons, None)
            
    def _create_decision(self, tier: str, reasons: List[str], context: Dict[str, Any] = None) -> Dict[str, Any]:
        decision = {
            "tier": tier,
            "reasons": reasons
        }
        if tier == "HUMAN_ESCALATION" and context:
            decision["handoff_payload"] = self._build_handoff(context, reasons)
        return decision
        
    def _build_handoff(self, context: Dict[str, Any], reasons: List[str]) -> Dict[str, Any]:
        return {
            "reason_for_escalation": reasons,
            "current_intent": context.get("predicted_intent", "UNKNOWN"),
            "multi_intent_info": context.get("multi_intent_info", False),
            "capability_state": context.get("capability_state", {}),
            "frustration_trajectory": context.get("frustration_trajectory", "STABLE"),
            "historical_precedents_considered_as_playbooks": context.get("retrieved_precedents", []),
            "thread_context": context.get("query_conversation", {})
        }
