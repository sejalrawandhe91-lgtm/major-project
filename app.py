from flask import Flask, request, jsonify
from datetime import datetime
from sqlalchemy import func
import os

from database import init_db, SessionLocal, Project, LandParcel, Dispute

app = Flask(__name__, static_folder='static', static_url_path='')

# Initialize database on startup
with app.app_context():
    init_db()

@app.route('/')
def index():
    return app.send_static_file('index.html')

# 1. Dashboard Stats Endpoint
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    db = SessionLocal()
    try:
        # Counters
        total_projects = db.query(Project).count()
        total_parcels = db.query(LandParcel).count()
        total_disputes = db.query(Dispute).filter(Dispute.status != 'Resolved').count()
        
        # Financial Totals (in Rupees)
        total_compensation = db.query(func.sum(LandParcel.total_compensation)).scalar() or 0.0
        total_disbursed = db.query(func.sum(LandParcel.total_compensation)).filter(LandParcel.status == 'Paid').scalar() or 0.0
        total_disputed_amt = db.query(func.sum(LandParcel.total_compensation)).filter(LandParcel.status == 'Disputed').scalar() or 0.0
        total_pending = total_compensation - total_disbursed - total_disputed_amt
        
        # Acquisition progress (ratio of Paid parcels to total parcels)
        paid_count = db.query(LandParcel).filter(LandParcel.status == 'Paid').count()
        progress_pct = (paid_count / total_parcels * 100.0) if total_parcels > 0 else 0.0
        
        # Land status breakdown
        status_counts = db.query(LandParcel.status, func.count(LandParcel.id)).group_by(LandParcel.status).all()
        status_breakdown = {status: count for status, count in status_counts}
        # Ensure all statuses exist in dict
        for s in ['Pending', 'Notified', 'Valued', 'Paid', 'Disputed']:
            status_breakdown.setdefault(s, 0)
            
        # Project progress details
        projects_data = db.query(Project).all()
        projects_progress = []
        for p in projects_data:
            p_total_acres = sum(lp.area_acres for lp in p.parcels)
            p_acquired_acres = sum(lp.area_acres for lp in p.parcels if lp.status == 'Paid')
            p_progress_pct = (p_acquired_acres / p_total_acres * 100.0) if p_total_acres > 0 else 0.0
            
            projects_progress.append({
                'id': p.id,
                'name': p.name,
                'requiring_agency': p.requiring_agency,
                'state': p.state,
                'status': p.status,
                'target_acres': p.target_acres,
                'acquired_acres': round(p_acquired_acres, 2),
                'progress_percentage': round(p_progress_pct, 1),
                'budget_cr': p.budget_cr
            })
            
        return jsonify({
            'total_projects': total_projects,
            'total_parcels': total_parcels,
            'active_disputes': total_disputes,
            'financials': {
                'total_compensation': round(total_compensation, 2),
                'total_disbursed': round(total_disbursed, 2),
                'total_pending': round(total_pending, 2),
                'total_disputed_amt': round(total_disputed_amt, 2)
            },
            'progress_percentage': round(progress_pct, 1),
            'status_breakdown': status_breakdown,
            'projects': projects_progress
        })
    finally:
        db.close()

# 2. Get All Projects
@app.route('/api/projects', methods=['GET'])
def get_projects():
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        return jsonify([p.to_dict() for p in projects])
    finally:
        db.close()

# 3. Create New Project
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('requiring_agency') or not data.get('state'):
        return jsonify({'error': 'Missing required fields'}), 400
        
    db = SessionLocal()
    try:
        project = Project(
            name=data['name'],
            requiring_agency=data['requiring_agency'],
            state=data['state'],
            target_acres=float(data.get('target_acres', 0.0)),
            budget_cr=float(data.get('budget_cr', 0.0)),
            status='Initiated'
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return jsonify(project.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# 4. Get Parcels for a specific project
@app.route('/api/projects/<int:project_id>/parcels', methods=['GET'])
def get_project_parcels(project_id):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
            
        parcels = db.query(LandParcel).filter(LandParcel.project_id == project_id).all()
        return jsonify({
            'project': project.to_dict(),
            'parcels': [p.to_dict() for p in parcels]
        })
    finally:
        db.close()

# 5. Add Land Parcel to Project
@app.route('/api/projects/<int:project_id>/parcels', methods=['POST'])
def add_parcel(project_id):
    data = request.get_json()
    required = ['survey_number', 'owner_name', 'area_acres', 'land_type', 'market_value', 'solatium', 'total_compensation']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing field: {f}'}), 400
            
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
            
        parcel = LandParcel(
            project_id=project_id,
            survey_number=data['survey_number'],
            owner_name=data['owner_name'],
            area_acres=float(data['area_acres']),
            land_type=data['land_type'],
            market_value=float(data['market_value']),
            multiplier=float(data.get('multiplier', 1.0)),
            solatium=float(data['solatium']),
            assets_value=float(data.get('assets_value', 0.0)),
            total_compensation=float(data['total_compensation']),
            status=data.get('status', 'Pending')
        )
        db.add(parcel)
        
        # Dynamically increment target acres for the project
        project.target_acres = round(project.target_acres + parcel.area_acres, 2)
        db.commit()
        db.refresh(parcel)
        return jsonify(parcel.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# 6. Disburse Payment (Mark as Paid)
@app.route('/api/parcels/<int:parcel_id>/disburse', methods=['POST'])
def disburse_payment(parcel_id):
    db = SessionLocal()
    try:
        parcel = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
        if not parcel:
            return jsonify({'error': 'Land parcel not found'}), 404
            
        if parcel.status == 'Paid':
            return jsonify({'error': 'Payment has already been disbursed'}), 400
            
        parcel.status = 'Paid'
        parcel.disbursement_date = datetime.utcnow()
        db.commit()
        db.refresh(parcel)
        return jsonify(parcel.to_dict())
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# 7. File Dispute for a parcel
@app.route('/api/parcels/<int:parcel_id>/dispute', methods=['POST'])
def create_parcel_dispute(parcel_id):
    data = request.get_json()
    if not data or not data.get('dispute_type') or not data.get('description'):
        return jsonify({'error': 'Missing dispute details'}), 400
        
    db = SessionLocal()
    try:
        parcel = db.query(LandParcel).filter(LandParcel.id == parcel_id).first()
        if not parcel:
            return jsonify({'error': 'Land parcel not found'}), 404
            
        # Update parcel status to Disputed
        parcel.status = 'Disputed'
        
        dispute = Dispute(
            parcel_id=parcel_id,
            dispute_type=data['dispute_type'],
            raised_by=parcel.owner_name,
            description=data['description'],
            status='Pending'
        )
        db.add(dispute)
        db.commit()
        db.refresh(dispute)
        return jsonify({
            'parcel': parcel.to_dict(),
            'dispute': dispute.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# 8. List Disputes
@app.route('/api/disputes', methods=['GET'])
def list_disputes():
    db = SessionLocal()
    try:
        disputes = db.query(Dispute).order_by(Dispute.created_at.desc()).all()
        results = []
        for d in disputes:
            parcel = d.parcel
            project = parcel.project if parcel else None
            results.append({
                'id': d.id,
                'parcel_id': d.parcel_id,
                'dispute_type': d.dispute_type,
                'raised_by': d.raised_by,
                'description': d.description,
                'status': d.status,
                'resolution_details': d.resolution_details,
                'created_at': d.created_at.isoformat(),
                'parcel_survey': parcel.survey_number if parcel else 'N/A',
                'parcel_area': parcel.area_acres if parcel else 0.0,
                'project_name': project.name if project else 'N/A'
            })
        return jsonify(results)
    finally:
        db.close()

# 9. Resolve Dispute
@app.route('/api/disputes/<int:dispute_id>/resolve', methods=['POST'])
def resolve_dispute(dispute_id):
    data = request.get_json()
    resolution_text = data.get('resolution_details', 'Resolved after review')
    
    db = SessionLocal()
    try:
        dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            return jsonify({'error': 'Dispute not found'}), 404
            
        dispute.status = 'Resolved'
        dispute.resolution_details = resolution_text
        
        # Restore parcel status to 'Valued' so it can be paid, or 'Paid' directly depending on user request
        parcel = dispute.parcel
        if parcel and parcel.status == 'Disputed':
            parcel.status = 'Valued'
            
        db.commit()
        return jsonify({
            'success': True,
            'dispute': dispute.to_dict(),
            'parcel': parcel.to_dict() if parcel else None
        })
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
