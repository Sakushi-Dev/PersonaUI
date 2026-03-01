"""
MoodService - Mood state management and database persistence

Handles mood state storage, retrieval, and updates.
Uses MoodEngine for analysis and decay calculations.
"""

from datetime import datetime
from typing import Dict, List, Optional
import sqlite3

from utils.logger import log
from utils.sql_loader import sql
from utils.database.connection import get_db_connection
from utils.mood.engine import MoodEngine


class MoodService:
    """Service for managing persona mood state with database persistence."""
    
    def __init__(self):
        """Initialize MoodService with internal MoodEngine."""
        self.engine = MoodEngine()
    
    def get_mood(self, persona_id: str) -> Dict:
        """
        Get current mood state with decay applied.
        
        Args:
            persona_id: ID of the persona
            
        Returns:
            Dict with current mood state including emoji and dominant emotion
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Try to get existing state
                cursor.execute(sql['mood.get_state'], (persona_id,))
                row = cursor.fetchone()
                
                if row is None:
                    # Create baseline state for new persona
                    cursor.execute(sql['mood.init_state'], (persona_id,))
                    conn.commit()
                    
                    # Return baseline state
                    baseline_state = {dim: self.engine.BASELINE for dim in self.engine.DIMENSIONS}
                    return {
                        **baseline_state,
                        'emoji': self.engine.get_mood_emoji(baseline_state),
                        'dominant': self.engine.calculate_dominant_emotion(baseline_state),
                        'last_updated': datetime.now().isoformat()
                    }
                
                # Extract current state and timestamp
                anger, sadness, affection, arousal, trust, last_updated_str = row
                current_state = {
                    'anger': anger,
                    'sadness': sadness, 
                    'affection': affection,
                    'arousal': arousal,
                    'trust': trust
                }
                
                # Calculate time elapsed for decay
                if last_updated_str:
                    try:
                        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                        seconds_elapsed = (datetime.now() - last_updated).total_seconds()
                    except (ValueError, TypeError):
                        seconds_elapsed = 0
                else:
                    seconds_elapsed = 0
                
                # Apply decay if time has passed
                if seconds_elapsed > 0:
                    from utils.settings import _read_setting
                    decay_rate = _read_setting('moodDecayRate', 0.1)
                    current_state = self.engine.apply_decay(current_state, decay_rate, seconds_elapsed)
                    
                    # Update database with decayed state
                    cursor.execute(
                        sql['mood.update_state'],
                        (persona_id, current_state['anger'], current_state['sadness'],
                         current_state['affection'], current_state['arousal'], current_state['trust'])
                    )
                    conn.commit()
                
                # Add metadata
                result = {
                    **current_state,
                    'emoji': self.engine.get_mood_emoji(current_state),
                    'dominant': self.engine.calculate_dominant_emotion(current_state),
                    'last_updated': datetime.now().isoformat()
                }
                
                return result
                
        except Exception as e:
            log.error("Error getting mood state for persona %s: %s", persona_id, e)
            # Return baseline on error
            baseline_state = {dim: self.engine.BASELINE for dim in self.engine.DIMENSIONS}
            return {
                **baseline_state,
                'emoji': '😊',
                'dominant': 'neutral',
                'last_updated': datetime.now().isoformat()
            }
    
    def update_mood(self, persona_id: str, ai_response: str, sensitivity: float = 0.5) -> Dict:
        """
        Update mood state based on AI response text.
        
        Args:
            persona_id: ID of the persona
            ai_response: AI response text to analyze
            sensitivity: Sensitivity multiplier (0.0-1.0)
            
        Returns:
            New mood state after update
        """
        try:
            # Get current mood (with decay applied)
            current_mood = self.get_mood(persona_id)
            current_state = {dim: current_mood[dim] for dim in self.engine.DIMENSIONS}
            
            # Analyze sentiment deltas
            deltas = self.engine.analyze_response_sentiment(ai_response, sensitivity)
            
            # Apply deltas to current state
            new_state = {}
            for dimension in self.engine.DIMENSIONS:
                new_val = current_state[dimension] + deltas[dimension]
                # Clamp to valid range
                new_state[dimension] = max(0, min(100, round(new_val)))
            
            # Update database
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Update state
                cursor.execute(
                    sql['mood.update_state'],
                    (persona_id, new_state['anger'], new_state['sadness'],
                     new_state['affection'], new_state['arousal'], new_state['trust'])
                )
                
                # Insert history entry
                cursor.execute(
                    sql['mood.insert_history'],
                    (persona_id, new_state['anger'], new_state['sadness'],
                     new_state['affection'], new_state['arousal'], new_state['trust'],
                     ai_response[:1000] if ai_response else None)  # Truncate long responses
                )
                
                conn.commit()
            
            # Return new state with metadata
            result = {
                **new_state,
                'emoji': self.engine.get_mood_emoji(new_state),
                'dominant': self.engine.calculate_dominant_emotion(new_state),
                'last_updated': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            log.error("Error updating mood for persona %s: %s", persona_id, e)
            # Return current state on error
            return self.get_mood(persona_id)
    
    def reset_mood(self, persona_id: str) -> Dict:
        """
        Reset mood to baseline values.
        
        Args:
            persona_id: ID of the persona
            
        Returns:
            Baseline mood state
        """
        try:
            baseline_state = {dim: self.engine.BASELINE for dim in self.engine.DIMENSIONS}
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    sql['mood.update_state'],
                    (persona_id, baseline_state['anger'], baseline_state['sadness'],
                     baseline_state['affection'], baseline_state['arousal'], baseline_state['trust'])
                )
                conn.commit()
            
            result = {
                **baseline_state,
                'emoji': self.engine.get_mood_emoji(baseline_state),
                'dominant': self.engine.calculate_dominant_emotion(baseline_state),
                'last_updated': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            log.error("Error resetting mood for persona %s: %s", persona_id, e)
            # Still return baseline state even on error
            baseline_state = {dim: self.engine.BASELINE for dim in self.engine.DIMENSIONS}
            return {
                **baseline_state,
                'emoji': '😊',
                'dominant': 'neutral', 
                'last_updated': datetime.now().isoformat()
            }
    
    def update_settings(self, persona_id: str, sensitivity: float = None, decay_rate: float = None) -> None:
        """
        Update mood settings (delegates to existing settings system).
        
        Note: Settings are stored globally, not per persona.
        
        Args:
            persona_id: ID of the persona (unused but kept for API consistency)
            sensitivity: New sensitivity value (0.0-1.0)
            decay_rate: New decay rate value
        """
        try:
            from utils.settings import _write_setting
            
            if sensitivity is not None:
                if 0.0 <= sensitivity <= 1.0:
                    _write_setting('moodSensitivity', sensitivity)
                else:
                    raise ValueError("Sensitivity must be between 0.0 and 1.0")
            
            if decay_rate is not None:
                if decay_rate >= 0.0:
                    _write_setting('moodDecayRate', decay_rate)
                else:
                    raise ValueError("Decay rate must be >= 0.0")
                    
        except Exception as e:
            log.error("Error updating mood settings: %s", e)
            raise
    
    def get_history(self, persona_id: str, limit: int = 50) -> List[Dict]:
        """
        Get mood history for a persona.
        
        Args:
            persona_id: ID of the persona
            limit: Maximum number of entries to return
            
        Returns:
            List of mood history entries
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql['mood.get_history'], (persona_id, limit))
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    anger, sadness, affection, arousal, trust, trigger_text, timestamp = row
                    history.append({
                        'anger': anger,
                        'sadness': sadness,
                        'affection': affection,
                        'arousal': arousal,
                        'trust': trust,
                        'trigger_text': trigger_text,
                        'timestamp': timestamp
                    })
                
                return history
                
        except Exception as e:
            log.error("Error getting mood history for persona %s: %s", persona_id, e)
            return []