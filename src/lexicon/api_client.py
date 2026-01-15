"""
API client module for AI model interactions
"""

import os
import json
import re
from typing import Dict, Optional
from ollama import chat


def extract_json(text: str) -> Optional[str]:
    """Extract JSON from text"""
    try:
        json.loads(text)
        return text
    except:
        pass
    
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return None


class APIClient:
    """API client wrapper"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma3"
    ):
        """
        Initialize API client
        
        Args:
            api_key: API key (not required for Ollama, set to None)
            base_url: API base URL (kept for compatibility, not used by ollama chat)
            model: Model name (default: gemma3)
        """
        self.model = model
    
    def label_image(
        self,
        image_path: str,
        prompt: str
    ) -> Dict:
        """
        Label a single image
        
        Args:
            image_path: Image file path
            prompt: Prompt text
        
        Returns:
            Label result dictionary
        """
        max_attempts = 3
        last_error: Optional[str] = None
        last_content: str = ""
        is_debug = os.getenv('DEBUG', '').lower() == 'true'

        for attempt in range(1, max_attempts + 1):
            try:
                response = chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [image_path],
                        }
                    ],
                )
                content = response.message.content.strip()
                last_content = content
                
                json_str = extract_json(content)
                if json_str:
                    try:
                        labels = json.loads(json_str)
                        return {
                            'labels': labels,
                            'raw_response': content,
                            'error': None
                        }
                    except json.JSONDecodeError as e:
                        last_error = f'JSON parsing failed: {str(e)}'
                        if is_debug:
                            print(f"\n[DEBUG] Attempt {attempt} JSON parsing failed: {e}")
                            print(f"[DEBUG] Extracted JSON string: {json_str[:500]}...")
                        continue
                else:
                    last_error = 'JSON parsing failed: unable to extract JSON from response'
                    if is_debug:
                        print(f"\n[DEBUG] Attempt {attempt} parsing failed: unable to extract JSON from response")
                        print(f"[DEBUG] Raw response content:\n{content}")
                    continue
                    
            except Exception as e:
                last_error = str(e)
                if is_debug:
                    print(f"\n[DEBUG] Attempt {attempt} API call error: {e}")
                continue

        return {
            'labels': {},
            'raw_response': last_content,
            'error': last_error or 'Unknown error'
        }

