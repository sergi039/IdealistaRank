import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import or_, and_
from models import Land, ScoringCriteria
from app import db

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page redirects to lands listing"""
    return redirect(url_for('main.lands'))

@main_bp.route('/lands')
def lands():
    """Main lands listing page with filtering and sorting"""
    try:
        # Get query parameters
        sort_by = request.args.get('sort', 'score_total')
        sort_order = request.args.get('order', 'desc')
        land_type_filter = request.args.get('land_type', '')
        municipality_filter = request.args.get('municipality', '')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_area = request.args.get('min_area', type=float)
        max_area = request.args.get('max_area', type=float)
        search_query = request.args.get('search', '')
        
        # Build query
        query = Land.query
        
        # Apply filters
        if land_type_filter:
            query = query.filter(Land.land_type == land_type_filter)
        
        if municipality_filter:
            query = query.filter(Land.municipality.ilike(f'%{municipality_filter}%'))
        
        if min_price is not None:
            query = query.filter(Land.price >= min_price)
        
        if max_price is not None:
            query = query.filter(Land.price <= max_price)
        
        if min_area is not None:
            query = query.filter(Land.area >= min_area)
        
        if max_area is not None:
            query = query.filter(Land.area <= max_area)
        
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                or_(
                    Land.title.ilike(search_pattern),
                    Land.description.ilike(search_pattern),
                    Land.municipality.ilike(search_pattern)
                )
            )
        
        # Apply sorting
        if hasattr(Land, sort_by):
            sort_column = getattr(Land, sort_by)
            if sort_order == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        # Get results
        lands = query.all()
        
        # Get unique municipalities for filter dropdown
        municipalities = db.session.query(Land.municipality).distinct().filter(
            Land.municipality.isnot(None)
        ).all()
        municipalities = [m[0] for m in municipalities if m[0]]
        municipalities.sort()
        
        return render_template(
            'lands.html',
            lands=lands,
            municipalities=municipalities,
            current_filters={
                'sort': sort_by,
                'order': sort_order,
                'land_type': land_type_filter,
                'municipality': municipality_filter,
                'min_price': min_price,
                'max_price': max_price,
                'min_area': min_area,
                'max_area': max_area,
                'search': search_query
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to load lands page: {str(e)}")
        flash(f"Error loading lands: {str(e)}", 'error')
        return render_template('lands.html', lands=[], municipalities=[])

@main_bp.route('/lands/<int:land_id>')
def land_detail(land_id):
    """Detailed view of a specific land"""
    try:
        land = Land.query.get_or_404(land_id)
        
        # Get score breakdown from environment field
        score_breakdown = {}
        if land.environment and 'score_breakdown' in land.environment:
            score_breakdown = land.environment['score_breakdown']
        
        return render_template(
            'land_detail.html',
            land=land,
            score_breakdown=score_breakdown
        )
        
    except Exception as e:
        logger.error(f"Failed to load land detail {land_id}: {str(e)}")
        flash(f"Error loading land details: {str(e)}", 'error')
        return redirect(url_for('main.lands'))

@main_bp.route('/criteria')
def criteria():
    """Scoring criteria management page"""
    try:
        criteria = ScoringCriteria.query.filter_by(active=True).all()
        
        # If no criteria exist, create defaults
        if not criteria:
            from config import Config
            for criteria_name, weight in Config.DEFAULT_SCORING_WEIGHTS.items():
                criterion = ScoringCriteria(
                    criteria_name=criteria_name,
                    weight=weight
                )
                db.session.add(criterion)
            db.session.commit()
            criteria = ScoringCriteria.query.filter_by(active=True).all()
        
        return render_template('criteria.html', criteria=criteria)
        
    except Exception as e:
        logger.error(f"Failed to load criteria page: {str(e)}")
        flash(f"Error loading criteria: {str(e)}", 'error')
        return render_template('criteria.html', criteria=[])

@main_bp.route('/criteria/update', methods=['POST'])
def update_criteria():
    """Update scoring criteria weights"""
    try:
        # Get form data
        weights = {}
        for key, value in request.form.items():
            if key.startswith('weight_'):
                criteria_name = key.replace('weight_', '')
                try:
                    weights[criteria_name] = float(value)
                except ValueError:
                    flash(f"Invalid weight value for {criteria_name}", 'error')
                    return redirect(url_for('main.criteria'))
        
        # Update weights using scoring service
        from services.scoring_service import ScoringService
        scoring_service = ScoringService()
        
        if scoring_service.update_weights(weights):
            flash('Scoring criteria updated successfully. All lands have been rescored.', 'success')
        else:
            flash('Failed to update scoring criteria', 'error')
        
        return redirect(url_for('main.criteria'))
        
    except Exception as e:
        logger.error(f"Failed to update criteria: {str(e)}")
        flash(f"Error updating criteria: {str(e)}", 'error')
        return redirect(url_for('main.criteria'))

@main_bp.route('/export.csv')
def export_csv():
    """Export current land selection to CSV"""
    try:
        from flask import make_response
        import csv
        import io
        
        # Get same filters as lands page
        land_type_filter = request.args.get('land_type', '')
        municipality_filter = request.args.get('municipality', '')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_area = request.args.get('min_area', type=float)
        max_area = request.args.get('max_area', type=float)
        search_query = request.args.get('search', '')
        
        # Build query with same filters
        query = Land.query
        
        if land_type_filter:
            query = query.filter(Land.land_type == land_type_filter)
        
        if municipality_filter:
            query = query.filter(Land.municipality.ilike(f'%{municipality_filter}%'))
        
        if min_price is not None:
            query = query.filter(Land.price >= min_price)
        
        if max_price is not None:
            query = query.filter(Land.price <= max_price)
        
        if min_area is not None:
            query = query.filter(Land.area >= min_area)
        
        if max_area is not None:
            query = query.filter(Land.area <= max_area)
        
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                or_(
                    Land.title.ilike(search_pattern),
                    Land.description.ilike(search_pattern),
                    Land.municipality.ilike(search_pattern)
                )
            )
        
        lands = query.order_by(Land.score_total.desc()).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Title', 'URL', 'Price (€)', 'Area (m²)', 'Municipality',
            'Land Type', 'Legal Status', 'Score Total', 'Latitude', 'Longitude',
            'Created At'
        ])
        
        # Data rows
        for land in lands:
            writer.writerow([
                land.id,
                land.title,
                land.url,
                land.price,
                land.area,
                land.municipality,
                land.land_type,
                land.legal_status,
                land.score_total,
                land.location_lat,
                land.location_lon,
                land.created_at.isoformat() if land.created_at else ''
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=idealista_lands.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to export CSV: {str(e)}")
        flash(f"Error exporting CSV: {str(e)}", 'error')
        return redirect(url_for('main.lands'))

@main_bp.route('/healthz')
def health_check():
    """Health check endpoint"""
    return jsonify({"ok": True})
