import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types
import openai

class GenerationOutput(BaseModel):
    generated_response: str = Field(description="The customer-facing response following the brand voice: Empathy -> Ownership -> Information/Verification -> Next Step.")
    claims_made: List[str] = Field(description="A list of factual claims made in the response (e.g., 'your package is delayed by 2 days').")
    actions_implied: List[str] = Field(description="A list of specific backend action keys (e.g., 'action_refund', 'action_cancel_order', 'verify_account') that the response implies are possible or have been executed.")
    claimed_execution: bool = Field(description="Set to true ONLY if the response claims an action was completely executed (e.g., 'I have issued your refund'). Set to false if it only discusses/proposes the action (e.g., 'I can issue a refund').")

class Generator:
    def __init__(self, ai_disclosure_string="[AI Generated]"):
        self.ai_disclosure_string = ai_disclosure_string
        
        # Check provider (default to gemini for evaluation reproducibility)
        self.provider = os.environ.get("GENERATOR_PROVIDER", "gemini").lower()
        self.gemini_client = None
        self.openai_client = None
        
        if self.provider == "openai":
            self.openai_client = openai.OpenAI()
            self.model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            self.generation_mode = "interactive_ui"
        else:
            self.gemini_client = genai.Client()
            self.model_name = "gemini-2.5-flash"
            self.generation_mode = "evaluation"
            
        self.system_instruction = """You are an AI customer support agent for AmazonHelp on Twitter.
Your responses must be concise, natural, and follow this brand voice:
Empathy -> Ownership -> Necessary Information / Verification -> Next Step.

CRITICAL EVIDENCE HIERARCHY:
1. Current Verified Capability (Authoritative Truth): This defines what actions are actually possible or completed.
   - AVAILABLE: You may discuss or propose the action. You may ONLY claim it is executed if explicit completion evidence is provided.
   - UNAVAILABLE: You must NOT claim the action is possible. Provide an alternative or escalate.
   - UNKNOWN: You must NOT claim the action is possible. Gather required information or escalate.
2. Historical Precedents (Playbook): These show HOW human agents handled similar situations (tone, structure, troubleshooting). They are NOT factual evidence about the current customer's state. DO NOT copy their factual claims (e.g., do not say "I refunded you $10" just because a precedent did).
3. Model Knowledge: Do not override missing current evidence or invent Amazon policies.

MULTI-INTENT / FRUSTRATION:
- If intent is UNKNOWN or you are missing info, lean into gathering information ("Could you clarify...").
- Address all sub-issues independently.
- Acknowledge frustration empathetically, do not repeat redundant troubleshooting.

Your output must exactly follow the structured schema.
"""

    def _build_prompt(self, context):
        prompt = "--- CONTEXT ---\n"
        prompt += f"Query Conversation:\n{json.dumps(context.get('query_conversation', {}), indent=2)}\n\n"
        prompt += f"Predicted Intent: {context.get('predicted_intent', 'UNKNOWN')} (Confidence: {context.get('intent_confidence', 0.0)})\n\n"
        
        prompt += "--- CURRENT VERIFIED CAPABILITY STATE ---\n"
        prompt += f"{json.dumps(context.get('capability_state', {}), indent=2)}\n\n"
        
        prompt += "--- HISTORICAL PRECEDENTS (PLAYBOOK EVIDENCE ONLY) ---\n"
        for p in context.get('retrieved_precedents', []):
            prompt += f"- Intent: {p.get('precedent_intent')} | Outcome: {p.get('outcome_status')} | Text: {p.get('relevant_text')}\n"
            
        prompt += "\nGenerate the response and metadata according to the strict hierarchy."
        return prompt

    def generate_response(self, context):
        prompt = self._build_prompt(context)
        
        config_disclosure = context.get('config', {}).get('ai_disclosure_string', self.ai_disclosure_string)
        
        try:
            if self.provider == "openai":
                response = self.openai_client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=GenerationOutput,
                    temperature=0.2,
                )
                llm_output = response.choices[0].message.parsed.model_dump()
            else:
                response = self.gemini_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        response_mime_type="application/json",
                        response_schema=GenerationOutput,
                        temperature=0.2,
                    )
                )
                llm_output = json.loads(response.text)
        except Exception as e:
            print(f"Exception during LLM generation: {e}")
            import traceback
            traceback.print_exc()
            # Fallback if API fails
            llm_output = {
                "generated_response": "I'm sorry, I am having trouble processing your request right now. Please DM us your account details so our team can assist.",
                "claims_made": [],
                "actions_implied": [],
                "claimed_execution": False
            }
            
        # Deterministic Claim Validation
        capability_state = context.get('capability_state', {})
        unsupported = False
        
        for action in llm_output.get("actions_implied", []):
            state = capability_state.get(action)
            
            if isinstance(state, dict):
                status = state.get("status", "UNKNOWN")
                execution_status = state.get("execution_status", "NONE")
            else:
                status = state if state else "UNKNOWN"
                execution_status = "NONE"
                
            if status != "AVAILABLE":
                unsupported = True
                break
                
            if llm_output.get("claimed_execution") and execution_status != "COMPLETED":
                unsupported = True
                break

        if unsupported:
            # Drop the response and fallback to safe escalation (Routing to Deep Analysis / Agent)
            final_response = f"I want to make sure this is handled correctly. Could you please DM us with your order details so our specialized team can look into it? {config_disclosure}"
            return {
                "generated_response": final_response,
                "claims_made": llm_output.get("claims_made", []),
                "actions_implied": llm_output.get("actions_implied", []),
                "unsupported_claims_removed": True,
                "routed_to_deep_analysis": True,
                "raw_llm_response": llm_output.get("generated_response"),
                "provider": self.provider,
                "model": self.model_name,
                "generation_mode": self.generation_mode
            }
            
        # Append AI disclosure if not already present
        final_resp = llm_output.get("generated_response", "").strip()
        if config_disclosure not in final_resp:
            final_resp = f"{final_resp} {config_disclosure}"

        return {
            "generated_response": final_resp,
            "claims_made": llm_output.get("claims_made", []),
            "actions_implied": llm_output.get("actions_implied", []),
            "unsupported_claims_removed": False,
            "routed_to_deep_analysis": False,
            "provider": self.provider,
            "model": self.model_name,
            "generation_mode": self.generation_mode
        }
