import re
import hashlib
from typing import Dict, List, Tuple
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PIIScrubber:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Add custom recognizer for Order ID (e.g. 111-1234567-1234567 or generic #12345)
        order_id_pattern = Pattern(
            name="order_id_pattern",
            regex=r"(?i)(?:order\s*(?:id|#)?\s*[:\-]?\s*)([0-9A-Z\-]{8,20})",
            score=0.8
        )
        order_id_recognizer = PatternRecognizer(
            supported_entity="ORDER_ID", 
            patterns=[order_id_pattern]
        )
        self.analyzer.registry.add_recognizer(order_id_recognizer)

        # Basic account/tracking number pattern
        account_id_pattern = Pattern(
            name="account_id_pattern",
            regex=r"(?i)(?:account\s*(?:id|#)?\s*[:\-]?\s*|tracking\s*(?:id|#)?\s*[:\-]?\s*)([0-9A-Z]{8,20})",
            score=0.8
        )
        account_id_recognizer = PatternRecognizer(
            supported_entity="ACCOUNT_ID",
            patterns=[account_id_pattern]
        )
        self.analyzer.registry.add_recognizer(account_id_recognizer)

    def hash_customer_id(self, author_id: str) -> str:
        """Hash customer IDs so they are retained without raw PII."""
        if author_id.lower() == "amazonhelp":
            return author_id
        return hashlib.sha256(author_id.encode('utf-8')).hexdigest()[:16]

    def scrub_text_deterministic(self, text: str, entity_map: Dict[str, str], entity_counters: Dict[str, int]) -> str:
        """
        Scrubs PII from text deterministically within a thread scope.
        Updates the passed entity_map and entity_counters in place.
        """
        # We need to detect entities first
        # We only care about specific PII to avoid over-scrubbing products
        entities_to_find = ["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "ORDER_ID", "ACCOUNT_ID"]
        results = self.analyzer.analyze(text=text, entities=entities_to_find, language='en')
        
        # Sort results by start index descending to allow replacing from end to start without messing up indices
        results.sort(key=lambda x: x.start, reverse=True)
        
        scrubbed_text = text
        for res in results:
            raw_value = text[res.start:res.end]
            entity_type = res.entity_type
            
            # Create a unique key for the map (e.g., PERSON:John)
            map_key = f"{entity_type}:{raw_value.lower()}"
            
            if map_key not in entity_map:
                entity_counters[entity_type] = entity_counters.get(entity_type, 0) + 1
                placeholder = f"[{entity_type}_{entity_counters[entity_type]}]"
                entity_map[map_key] = placeholder
            
            placeholder = entity_map[map_key]
            
            # Replace in text
            scrubbed_text = scrubbed_text[:res.start] + placeholder + scrubbed_text[res.end:]
            
        return scrubbed_text
