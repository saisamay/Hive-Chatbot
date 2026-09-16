import re
from typing import Dict, Any

class SafetyDetector:
    def __init__(self):
        # High confidence serious safety/legal/fraud patterns
        self.serious_patterns = [
            # Physical safety / Abuse
            r"\b(physical|sexual)\s+(abuse|assault)\b",
            r"\b(harm|kill)\s+myself\b",
            r"\bcommit(ting)?\s+suicide\b",
            r"\blife\s+threatening\b",
            r"\bdangerous\s+(driver|driving|truck|van)\b",
            r"\breckless\s+(driver|driving)\b",
            r"\bact\s+of\s+hate\b",
            
            # Serious Legal / Regulatory
            r"\bfiling\s+(a\s+)?lawsuit\b",
            r"\bclass\s+action\b",
            r"\bbreach\s+of\s+contract\b",
            r"\bcontact(ing)?\s+(my|an)\s+(attorney|lawyer)\s+regarding\b",
            r"\b(report|filed)\s+(has\s+been\s+)?(filed\s+with|to)\s+(the\s+)?(police|authorities|inspector)\b",
            
            # Severe Fraud / Security
            r"\b(identity|credit\s+card|bank\s+account)\s+(theft|fraud|stolen|hacked|drained)\b",
            r"\bforged\s+(my\s+)?signature\b",
            r"\baccount\s+(was|got|been)\s+(hacked|compromised|stolen)\b",
            r"\bunauthorized\s+(charge|purchase|transaction|access)\b",
            r"\b(someone|third\s+party)\s+(is\s+using|changed)\s+(my\s+email|my\s+account)\b",
            r"\bcard\s+info(rmation)?\s+was\s+leaked\b"
        ]
        
        # Ambiguous patterns that need human context, mapped to UNKNOWN
        self.ambiguous_patterns = [
            r"\bhacked\b",
            r"\bfraud\b",
            r"\bstolen\b",
            r"\btheft\b",
            r"\bpolice\b",
            r"\blawyer\b",
            r"\battorney\b",
            r"\bsue\b",
            r"\bunsafe\b",
            r"\bexploded\b",
            r"\bsparked\b",
            r"\bfire\b",
            r"\bscam\b",
            r"\babuse\b",
            r"\babusive\b",
            r"\bhate\b"
        ]

    def _extract_text(self, conversation: Dict[str, Any]) -> str:
        if 'tweets' in conversation:
            tweets = list(conversation['tweets'].values())
            return " ".join([t.get('text_clean', '') for t in tweets if t.get('inbound')]).lower()
        elif 'text_clean' in conversation:
            return conversation.get('text_clean', '').lower()
        return str(conversation).lower()

    def evaluate(self, conversation: Dict[str, Any]) -> str:
        """
        Evaluates the conversation text.
        Returns one of: "SAFE", "SAFETY_CONCERN", "UNKNOWN"
        """
        text = self._extract_text(conversation)
        
        # Check serious safety/legal/fraud (maps to SAFETY_CONCERN)
        for pattern in self.serious_patterns:
            if re.search(pattern, text):
                return "SAFETY_CONCERN"
                
        # Check ambiguous patterns (maps to UNKNOWN)
        is_ambiguous = False
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, text):
                is_ambiguous = True
                break
                
        if is_ambiguous:
            return "UNKNOWN"
            
        return "SAFE"
