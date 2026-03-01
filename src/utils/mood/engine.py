"""
MoodEngine - Mood analysis and decay logic

Pure logic class - no database access, no state management.
Handles sentiment analysis, decay calculations, and emoji mapping.
"""

import re
import math
from typing import Dict


class MoodEngine:
    """Core mood processing engine with local sentiment analysis."""
    
    DIMENSIONS = ['anger', 'sadness', 'affection', 'arousal', 'trust']
    BASELINE = 50  # Neutral value for all dimensions
    
    # Keyword dictionaries for sentiment analysis (German + English)
    KEYWORDS = {
        'anger': {
            'strong': ['furious', 'enraged', 'livid', 'wütend', 'sauer', 'verärgert', 'zornig'],
            'moderate': ['angry', 'annoyed', 'irritated', 'ärgerlich', 'genervt'],
            'weak': ['upset', 'frustrated', 'bothered', 'unzufrieden']
        },
        'sadness': {
            'strong': ['devastated', 'heartbroken', 'depressed', 'verzweifelt', 'niedergeschlagen'],
            'moderate': ['sad', 'melancholy', 'down', 'traurig', 'betrübt'],
            'weak': ['disappointed', 'blue', 'enttäuscht', 'wehmütig']
        },
        'affection': {
            'strong': ['love', 'adore', 'cherish', 'liebe', 'vergöttere', 'schätze'],
            'moderate': ['like', 'fond', 'care', 'mag', 'gern haben'],
            'weak': ['appreciate', 'enjoy', 'schätzen', 'gefällt']
        },
        'arousal': {
            'strong': ['excited', 'thrilled', 'passionate', 'aufgeregt', 'begeistert', 'leidenschaftlich'],
            'moderate': ['interested', 'curious', 'engaged', 'interessiert', 'neugierig'],
            'weak': ['intrigued', 'alert', 'fasziniert', 'aufmerksam']
        },
        'trust': {
            'strong': ['trust', 'confident', 'rely', 'vertrauen', 'verlassen'],
            'moderate': ['believe', 'faith', 'count on', 'glaube', 'zählen'],
            'weak': ['hope', 'expect', 'hoffe', 'erwarte']
        }
    }
    
    # Pattern-based analysis (regex patterns with associated mood deltas)
    PATTERNS = {
        'affection': [
            (r'\b(i love|ich liebe|love you|liebe dich)\b', 20),
            (r'\b(thank you|danke|grateful|dankbar)\b', 8),
            (r'\b(wonderful|amazing|wunderbar|erstaunlich)\b', 10)
        ],
        'trust': [
            (r'\b(i trust|ich vertraue|reliable|zuverlässig)\b', 15),
            (r'\b(honest|ehrlich|trustworthy|vertrauenswürdig)\b', 12)
        ],
        'anger': [
            (r'\b(hate|hasse|disgusting|ekelhaft)\b', 15),
            (r'\b(stupid|dumm|idiot|blöd)\b', 10),
            (r'[!]{2,}', 5)  # Multiple exclamation marks
        ],
        'sadness': [
            (r'\b(sorry|entschuldigung|regret|bereue)\b', 8),
            (r'\b(terrible|schrecklich|awful|furchtbar)\b', 10)
        ],
        'arousal': [
            (r'\b(wow|amazing|incredible|unglaublich)\b', 12),
            (r'\b(exciting|aufregend|fantastic|fantastisch)\b', 10)
        ]
    }
    
    def analyze_response_sentiment(self, text: str, sensitivity: float = 0.5) -> Dict[str, float]:
        """
        Analyze sentiment of AI response text and return mood deltas.
        
        Args:
            text: AI response text to analyze
            sensitivity: Multiplier for deltas (0.0-1.0)
            
        Returns:
            Dict with deltas per dimension (e.g. {'anger': -5.0, 'affection': 12.0, ...})
        """
        if not text or not isinstance(text, str):
            return {dim: 0.0 for dim in self.DIMENSIONS}
            
        text_lower = text.lower()
        deltas = {dim: 0.0 for dim in self.DIMENSIONS}
        
        # Keyword-based analysis
        for dimension, keyword_groups in self.KEYWORDS.items():
            for strength, keywords in keyword_groups.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        if strength == 'strong':
                            deltas[dimension] += 15.0
                        elif strength == 'moderate':
                            deltas[dimension] += 8.0
                        else:  # weak
                            deltas[dimension] += 4.0
        
        # Pattern-based analysis
        for dimension, patterns in self.PATTERNS.items():
            for pattern, delta in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                if matches > 0:
                    deltas[dimension] += delta * matches
        
        # Apply sensitivity scaling
        for dimension in deltas:
            deltas[dimension] *= sensitivity
            
        return deltas
    
    def apply_decay(self, current_state: Dict[str, int], decay_rate: float, seconds_elapsed: float) -> Dict[str, int]:
        """
        Apply time-based decay toward baseline.
        
        Args:
            current_state: Current mood values (0-100)
            decay_rate: Decay rate (higher = faster decay)
            seconds_elapsed: Time elapsed since last update
            
        Returns:
            New mood state with decay applied
        """
        if seconds_elapsed <= 0:
            return current_state.copy()
            
        hours_elapsed = seconds_elapsed / 3600.0
        decay_factor = 1 - math.exp(-decay_rate * hours_elapsed)
        
        new_state = {}
        for dimension in self.DIMENSIONS:
            current_val = current_state.get(dimension, self.BASELINE)
            # Move toward baseline
            diff = self.BASELINE - current_val
            new_val = current_val + (diff * decay_factor)
            # Clamp to valid range and round
            new_state[dimension] = max(0, min(100, round(new_val)))
            
        return new_state
    
    def get_mood_emoji(self, mood_state: Dict[str, int]) -> str:
        """
        Get emoji representing the dominant mood.
        
        Args:
            mood_state: Current mood values
            
        Returns:
            Emoji string for dominant emotion
        """
        dominant = self.calculate_dominant_emotion(mood_state)
        
        emoji_map = {
            'anger': '😠',
            'sadness': '😢', 
            'affection': '🥰',
            'arousal': '😏',
            'trust': '🤗'
        }
        
        return emoji_map.get(dominant, '😊')  # Default neutral emoji
    
    def calculate_dominant_emotion(self, mood_state: Dict[str, int]) -> str:
        """
        Calculate the dominant emotion based on deviation from baseline.
        
        Args:
            mood_state: Current mood values
            
        Returns:
            Dimension name with largest deviation from baseline
        """
        max_deviation = 0
        dominant = 'neutral'
        
        # Priority order for ties: affection > trust > arousal > anger > sadness
        priority_order = ['affection', 'trust', 'arousal', 'anger', 'sadness']
        
        for dimension in priority_order:
            value = mood_state.get(dimension, self.BASELINE)
            deviation = abs(value - self.BASELINE)
            if deviation > max_deviation:
                max_deviation = deviation
                dominant = dimension
        
        # If all values are close to baseline (±5), consider neutral
        if max_deviation <= 5:
            return 'neutral'
            
        return dominant