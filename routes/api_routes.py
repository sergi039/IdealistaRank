import logging
from flask import Blueprint, jsonify, request
from models import Land, ScoringCriteria
from app import db

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/healthz')
def health_check():
    """API health check"""
    return jsonify({"ok": True})

@api_bp.route('/ingest/email/run', methods=['POST'])
def manual_ingestion():
    """Manually trigger email ingestion"""
    try:
        from config import Config
        
        if Config.EMAIL_BACKEND == "imap":
            from services.imap_service import IMAPService
            service = IMAPService()
            backend_name = "IMAP"
        else:
            from services.gmail_service import GmailService
            service = GmailService()
            backend_name = "Gmail API"
        
        processed_count = service.run_ingestion()
        
        return jsonify({
            "success": True,
            "processed_count": processed_count,
            "backend": backend_name,
            "message": f"Successfully processed {processed_count} new properties via {backend_name}"
        })
        
    except Exception as e:
        logger.error(f"Manual ingestion failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/lands')
def get_lands():
    """Get lands with optional filtering and sorting"""
    try:
        # Get query parameters
        sort_by = request.args.get('sort', 'score_total')
        sort_order = request.args.get('order', 'desc')
        land_type_filter = request.args.get('filter')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = Land.query
        
        # Apply land type filter
        if land_type_filter and land_type_filter in ['developed', 'buildable']:
            query = query.filter(Land.land_type == land_type_filter)
        
        # Apply sorting
        if hasattr(Land, sort_by):
            sort_column = getattr(Land, sort_by)
            if sort_order == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        # Apply pagination
        lands = query.offset(offset).limit(limit).all()
        
        # Convert to JSON
        lands_data = [land.to_dict() for land in lands]
        
        return jsonify({
            "success": True,
            "count": len(lands_data),
            "lands": lands_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get lands: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/lands/<int:land_id>')
def get_land_detail(land_id):
    """Get detailed information about a specific land"""
    try:
        land = Land.query.get(land_id)
        
        if not land:
            return jsonify({
                "success": False,
                "error": "Land not found"
            }), 404
        
        land_data = land.to_dict()
        
        # Add score breakdown if available
        if land.environment and 'score_breakdown' in land.environment:
            land_data['score_breakdown'] = land.environment['score_breakdown']
        
        return jsonify({
            "success": True,
            "land": land_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get land detail {land_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/criteria')
def get_criteria():
    """Get current scoring criteria weights"""
    try:
        from services.scoring_service import ScoringService
        
        scoring_service = ScoringService()
        weights = scoring_service.get_current_weights()
        
        return jsonify({
            "success": True,
            "criteria": weights
        })
        
    except Exception as e:
        logger.error(f"Failed to get criteria: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/criteria', methods=['PUT'])
def update_criteria():
    """Update scoring criteria weights"""
    try:
        data = request.get_json()
        
        if not data or 'criteria' not in data:
            return jsonify({
                "success": False,
                "error": "Missing criteria data"
            }), 400
        
        weights = data['criteria']
        
        # Validate weights
        for criteria_name, weight in weights.items():
            if not isinstance(weight, (int, float)) or weight < 0:
                return jsonify({
                    "success": False,
                    "error": f"Invalid weight for {criteria_name}: must be a positive number"
                }), 400
        
        # Update weights
        from services.scoring_service import ScoringService
        scoring_service = ScoringService()
        
        if scoring_service.update_weights(weights):
            return jsonify({
                "success": True,
                "message": "Criteria updated successfully and all lands rescored"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update criteria"
            }), 500
        
    except Exception as e:
        logger.error(f"Failed to update criteria: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/scheduler/status')
def scheduler_status():
    """Get scheduler status"""
    try:
        from services.scheduler_service import get_scheduler_status
        
        status = get_scheduler_status()
        
        return jsonify({
            "success": True,
            "scheduler": status
        })
        
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route('/stats')
def get_stats():
    """Get application statistics"""
    try:
        # Basic statistics
        total_lands = Land.query.count()
        developed_lands = Land.query.filter_by(land_type='developed').count()
        buildable_lands = Land.query.filter_by(land_type='buildable').count()
        
        # Score statistics
        avg_score = db.session.query(db.func.avg(Land.score_total)).scalar()
        max_score = db.session.query(db.func.max(Land.score_total)).scalar()
        min_score = db.session.query(db.func.min(Land.score_total)).scalar()
        
        # Municipality distribution
        municipality_stats = db.session.query(
            Land.municipality,
            db.func.count(Land.id)
        ).group_by(Land.municipality).all()
        
        municipality_distribution = {
            municipality: count for municipality, count in municipality_stats if municipality
        }
        
        return jsonify({
            "success": True,
            "stats": {
                "total_lands": total_lands,
                "land_types": {
                    "developed": developed_lands,
                    "buildable": buildable_lands
                },
                "scores": {
                    "average": float(avg_score) if avg_score else 0,
                    "maximum": float(max_score) if max_score else 0,
                    "minimum": float(min_score) if min_score else 0
                },
                "municipality_distribution": municipality_distribution
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
