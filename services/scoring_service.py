import logging
from typing import Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class ScoringService:
    def __init__(self):
        self.weights = Config.DEFAULT_SCORING_WEIGHTS
        self.load_custom_weights()
    
    def load_custom_weights(self):
        """Load custom scoring weights from database"""
        try:
            from models import ScoringCriteria
            
            criteria = ScoringCriteria.query.filter_by(active=True).all()
            if criteria:
                custom_weights = {}
                for criterion in criteria:
                    custom_weights[criterion.criteria_name] = float(criterion.weight)
                
                # Update weights if we have custom ones
                if custom_weights:
                    self.weights.update(custom_weights)
                    logger.info(f"Loaded custom scoring weights: {custom_weights}")
            
        except Exception as e:
            logger.error(f"Failed to load custom weights: {str(e)}")
    
    def calculate_score(self, land) -> float:
        """Calculate total score for a land based on all criteria"""
        try:
            scores = {}
            
            # Calculate individual scores
            scores['infrastructure_basic'] = self._score_infrastructure_basic(land)
            scores['infrastructure_extended'] = self._score_infrastructure_extended(land)
            scores['transport'] = self._score_transport(land)
            scores['environment'] = self._score_environment(land)
            scores['neighborhood'] = self._score_neighborhood(land)
            scores['services_quality'] = self._score_services_quality(land)
            scores['legal_status'] = self._score_legal_status(land)
            
            # Calculate weighted total score
            total_score = 0
            total_weight = 0
            
            for criterion, score in scores.items():
                if score is not None and criterion in self.weights:
                    weight = self.weights[criterion]
                    total_score += score * weight
                    total_weight += weight
            
            # Normalize to 0-100 scale
            if total_weight > 0:
                final_score = (total_score / total_weight) * 100
            else:
                final_score = 0
            
            # Update land record
            land.score_total = round(final_score, 2)
            
            # Store individual scores in JSONB fields for transparency
            if not hasattr(land, 'score_breakdown'):
                # We'll store this in the environment field for now
                if not land.environment:
                    land.environment = {}
                land.environment['score_breakdown'] = scores
            
            logger.info(f"Calculated score for land {land.id}: {final_score}")
            return final_score
            
        except Exception as e:
            logger.error(f"Failed to calculate score for land {land.id}: {str(e)}")
            return 0
    
    def _score_infrastructure_basic(self, land) -> Optional[float]:
        """Score basic infrastructure (electricity, water, internet, gas)"""
        try:
            if not land.infrastructure_basic:
                return None
            
            basic_infra = land.infrastructure_basic
            score = 0
            max_score = 4  # 4 basic utilities
            
            # Check for basic utilities mentions in description
            description = (land.description or "").lower()
            
            utilities = {
                'electricity': ['electricidad', 'luz', 'eléctrico'],
                'water': ['agua', 'suministro agua', 'abastecimiento'],
                'internet': ['internet', 'fibra', 'adsl', 'wifi'],
                'gas': ['gas', 'butano', 'propano']
            }
            
            for utility, keywords in utilities.items():
                if basic_infra.get(utility) or any(kw in description for kw in keywords):
                    score += 1
            
            return (score / max_score) * 100
            
        except Exception as e:
            logger.error(f"Failed to score basic infrastructure: {str(e)}")
            return None
    
    def _score_infrastructure_extended(self, land) -> Optional[float]:
        """Score extended infrastructure (supermarket, school, restaurants, hospital)"""
        try:
            if not land.infrastructure_extended:
                return None
            
            extended_infra = land.infrastructure_extended
            score = 0
            
            # Score based on availability and distance
            amenities = ['supermarket', 'school', 'restaurant', 'hospital']
            
            for amenity in amenities:
                if extended_infra.get(f'{amenity}_available'):
                    distance = extended_infra.get(f'{amenity}_distance', float('inf'))
                    
                    # Score based on distance (closer is better)
                    if distance <= 1000:  # Within 1km
                        score += 25
                    elif distance <= 3000:  # Within 3km
                        score += 15
                    elif distance <= 5000:  # Within 5km
                        score += 10
                    else:
                        score += 5
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Failed to score extended infrastructure: {str(e)}")
            return None
    
    def _score_transport(self, land) -> Optional[float]:
        """Score transport accessibility"""
        try:
            if not land.transport:
                return None
            
            transport = land.transport
            score = 0
            
            # Score transport options
            transport_options = {
                'train_station': 30,
                'bus_station': 20,
                'airport': 25,
                'highway': 25
            }
            
            for option, max_points in transport_options.items():
                if transport.get(f'{option}_available'):
                    distance = transport.get(f'{option}_distance', float('inf'))
                    
                    # Score based on distance
                    if distance <= 2000:  # Within 2km
                        score += max_points
                    elif distance <= 5000:  # Within 5km
                        score += max_points * 0.7
                    elif distance <= 10000:  # Within 10km
                        score += max_points * 0.4
                    else:
                        score += max_points * 0.2
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Failed to score transport: {str(e)}")
            return None
    
    def _score_environment(self, land) -> Optional[float]:
        """Score environment features"""
        try:
            if not land.environment:
                return None
            
            environment = land.environment
            score = 0
            
            # View bonuses
            if environment.get('sea_view'):
                score += 40
            if environment.get('mountain_view'):
                score += 30
            if environment.get('forest_view'):
                score += 20
            
            # Orientation bonus (south-facing is preferred in Spain)
            orientation = environment.get('orientation', '').lower()
            if 'south' in orientation:
                score += 20
            elif 'southeast' in orientation or 'southwest' in orientation:
                score += 15
            elif 'east' in orientation or 'west' in orientation:
                score += 10
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Failed to score environment: {str(e)}")
            return None
    
    def _score_neighborhood(self, land) -> Optional[float]:
        """Score neighborhood characteristics"""
        try:
            if not land.neighborhood:
                return 50  # Default neutral score
            
            neighborhood = land.neighborhood
            score = 50  # Start with neutral score
            
            # Price level impact
            price_level = neighborhood.get('area_price_level', 'medium')
            if price_level == 'high':
                score += 20
            elif price_level == 'medium':
                score += 10
            
            # New houses nearby (indicates development)
            if neighborhood.get('new_houses'):
                score += 15
            
            # Noise level impact
            noise_level = neighborhood.get('noise', 'medium')
            if noise_level == 'low':
                score += 15
            elif noise_level == 'high':
                score -= 15
            
            return min(max(score, 0), 100)  # Keep between 0-100
            
        except Exception as e:
            logger.error(f"Failed to score neighborhood: {str(e)}")
            return None
    
    def _score_services_quality(self, land) -> Optional[float]:
        """Score quality of nearby services"""
        try:
            if not land.services_quality:
                return None
            
            services = land.services_quality
            score = 0
            count = 0
            
            # Average ratings of nearby services
            service_types = ['school_avg_rating', 'restaurant_avg_rating', 'cafe_avg_rating']
            
            for service_type in service_types:
                rating = services.get(service_type)
                if rating and rating > 0:
                    # Convert rating (1-5 scale) to percentage
                    score += (rating / 5) * 100
                    count += 1
            
            if count > 0:
                return score / count
            else:
                return None
            
        except Exception as e:
            logger.error(f"Failed to score services quality: {str(e)}")
            return None
    
    def _score_legal_status(self, land) -> Optional[float]:
        """Score legal status"""
        try:
            legal_status = (land.legal_status or "").lower()
            land_type = (land.land_type or "").lower()
            
            # Only developed and buildable are acceptable
            if 'developed' in legal_status or land_type == 'developed':
                return 100  # Fully developed land
            elif 'buildable' in legal_status or land_type == 'buildable':
                return 80   # Buildable land (some risk)
            else:
                return 0    # Rustic or other (not suitable)
            
        except Exception as e:
            logger.error(f"Failed to score legal status: {str(e)}")
            return None
    
    def update_weights(self, new_weights: Dict[str, float]) -> bool:
        """Update scoring weights and rescore all lands"""
        try:
            from models import ScoringCriteria, Land
            from app import db
            
            # Update or create criteria records
            for criteria_name, weight in new_weights.items():
                criterion = ScoringCriteria.query.filter_by(
                    criteria_name=criteria_name
                ).first()
                
                if criterion:
                    criterion.weight = weight
                else:
                    criterion = ScoringCriteria(
                        criteria_name=criteria_name,
                        weight=weight
                    )
                    db.session.add(criterion)
            
            db.session.commit()
            
            # Update local weights
            self.weights.update(new_weights)
            
            # Rescore all lands
            lands = Land.query.all()
            for land in lands:
                self.calculate_score(land)
            
            db.session.commit()
            
            logger.info(f"Updated scoring weights and rescored {len(lands)} lands")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update weights: {str(e)}")
            return False
    
    def get_current_weights(self) -> Dict[str, float]:
        """Get current scoring weights"""
        return self.weights.copy()
