#!/usr/bin/env python3
"""
Update scoring weights to professional Spanish/European standards
Total weights must equal 1.0 (100%)
"""

import logging
from app import app, db
from models import ScoringCriteria, Land
from services.scoring_service import ScoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Professional scoring weights based on Spanish/European standards
NEW_WEIGHTS = {
    # Location & Accessibility (35%)
    'location_quality': 0.20,          # Proximity to urban centers, neighborhood
    'transport': 0.15,                 # Public transport, road access
    
    # Infrastructure & Utilities (30%)
    'infrastructure_basic': 0.20,      # Water, electricity, sewerage, internet
    'infrastructure_extended': 0.10,   # Gas, telecommunications, public services
    
    # Physical & Environmental (15%)
    'environment': 0.10,               # Environmental quality, natural features
    'physical_characteristics': 0.05,  # Topography, size, shape
    
    # Services & Amenities (10%)
    'services_quality': 0.10,          # Schools, hospitals, shopping
    
    # Legal & Development (10%)
    'legal_status': 0.05,              # Zoning status, building permissions
    'development_potential': 0.05      # Future development possibilities
}

def update_scoring_criteria():
    """Update or create scoring criteria in database"""
    with app.app_context():
        try:
            # Deactivate old criteria not in new weights
            old_criteria = ScoringCriteria.query.all()
            for criterion in old_criteria:
                if criterion.criteria_name not in NEW_WEIGHTS:
                    criterion.active = False
                    logger.info(f"Deactivated old criterion: {criterion.criteria_name}")
            
            # Update or create new criteria
            for criteria_name, weight in NEW_WEIGHTS.items():
                criterion = ScoringCriteria.query.filter_by(
                    criteria_name=criteria_name
                ).first()
                
                if criterion:
                    criterion.weight = weight
                    criterion.active = True
                    logger.info(f"Updated criterion: {criteria_name} = {weight}")
                else:
                    criterion = ScoringCriteria(
                        criteria_name=criteria_name,
                        weight=weight,
                        active=True
                    )
                    db.session.add(criterion)
                    logger.info(f"Created new criterion: {criteria_name} = {weight}")
            
            db.session.commit()
            logger.info("Successfully updated scoring criteria")
            
            # Verify weights sum to 1.0
            total_weight = sum(NEW_WEIGHTS.values())
            logger.info(f"Total weight: {total_weight} (should be 1.0)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update scoring criteria: {str(e)}")
            db.session.rollback()
            return False

def recalculate_all_scores():
    """Recalculate scores for all lands with new weights"""
    with app.app_context():
        try:
            scoring_service = ScoringService()
            
            # Load new weights
            scoring_service.load_custom_weights()
            logger.info(f"Loaded weights: {scoring_service.weights}")
            
            # Get all lands
            lands = Land.query.all()
            logger.info(f"Recalculating scores for {len(lands)} lands")
            
            # Recalculate each land's score
            updated_count = 0
            for land in lands:
                old_score = land.score_total
                new_score = scoring_service.calculate_score(land)
                
                if old_score != new_score:
                    updated_count += 1
                    logger.info(f"Land {land.id}: {old_score} -> {new_score}")
            
            db.session.commit()
            logger.info(f"Successfully recalculated scores. Updated {updated_count} lands")
            
            # Show score distribution
            scores = [float(land.score_total) for land in lands if land.score_total]
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                logger.info(f"Score stats - Avg: {avg_score:.2f}, Max: {max_score:.2f}, Min: {min_score:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to recalculate scores: {str(e)}")
            db.session.rollback()
            return False

def main():
    """Main function to update scoring system"""
    logger.info("Starting scoring system update...")
    
    # Step 1: Update scoring criteria
    if update_scoring_criteria():
        logger.info("✓ Scoring criteria updated successfully")
    else:
        logger.error("✗ Failed to update scoring criteria")
        return
    
    # Step 2: Recalculate all scores
    if recalculate_all_scores():
        logger.info("✓ All scores recalculated successfully")
    else:
        logger.error("✗ Failed to recalculate scores")
        return
    
    logger.info("✓ Scoring system update completed!")

if __name__ == "__main__":
    main()