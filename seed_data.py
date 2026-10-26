import random
from datetime import datetime, timedelta
from database import init_db, SessionLocal, Project, LandParcel, Dispute

PROJECTS = [
    {
        "name": "Delhi-Mumbai Expressway Link Road",
        "requiring_agency": "NHAI",
        "state": "Haryana",
        "status": "Disbursement",
        "target_acres": 450.0,
        "budget_cr": 180.0
    },
    {
        "name": "Malwa Canal Network Phase 2",
        "requiring_agency": "Department of Water Resources",
        "state": "Madhya Pradesh",
        "status": "Surveying",
        "target_acres": 320.0,
        "budget_cr": 95.0
    },
    {
        "name": "Eastern Dedicated Freight Railway Corridor",
        "requiring_agency": "Ministry of Railways",
        "state": "Uttar Pradesh",
        "status": "Notification",
        "target_acres": 550.0,
        "budget_cr": 220.0
    },
    {
        "name": "Thar Solar Power Grid Substation",
        "requiring_agency": "Solar Energy Corporation of India",
        "state": "Rajasthan",
        "status": "Valuation",
        "target_acres": 180.0,
        "budget_cr": 45.0
    },
    {
        "name": "Bengaluru Satellite Town Ring Road",
        "requiring_agency": "NHAI",
        "state": "Karnataka",
        "status": "Completed",
        "target_acres": 380.0,
        "budget_cr": 140.0
    }
]

LAND_OWNERS = [
    "Rajesh Kumar", "Sunita Sharma", "Ramesh Patel", "Anil Singh", "Manju Devi",
    "Gaurav Jha", "Priya Verma", "Vijay Yadav", "Sanjay Gupta", "Kiran Reddy",
    "Arjun Naik", "Deepak Rao", "Suresh Choudhary", "Lakshmi Bai", "Vikram Rathore",
    "Amit Mishra", "Meena Joshi", "Harish Shettigar", "Savitri Gowda", "Rohan Deshmukh"
]

LAND_TYPES = ["Agricultural", "Residential", "Commercial"]

def get_valuation_rules(land_type):
    # Rates in INR per acre
    if land_type == "Agricultural":
        rate = 2500000.0  # 25 Lakhs / acre
        multiplier = 2.0  # Rural multiplier
    elif land_type == "Residential":
        rate = 7500000.0  # 75 Lakhs / acre
        multiplier = 1.3  # Semi-urban multiplier
    else:  # Commercial
        rate = 15000000.0  # 1.5 Cr / acre
        multiplier = 1.0  # Urban multiplier
    return rate, multiplier

def seed_database():
    print("Initializing Database...")
    init_db()
    
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Project).count() > 0:
        print("Database already contains data. Skipping seeding.")
        db.close()
        return
        
    print("Generating Projects...")
    created_projects = []
    for proj_data in PROJECTS:
        proj = Project(
            name=proj_data["name"],
            requiring_agency=proj_data["requiring_agency"],
            state=proj_data["state"],
            status=proj_data["status"],
            target_acres=proj_data["target_acres"],
            budget_cr=proj_data["budget_cr"],
            created_at=datetime.utcnow() - timedelta(days=random.randint(60, 300))
        )
        db.add(proj)
        created_projects.append(proj)
        
    db.commit() # Save projects to get IDs
    
    print("Generating Land Parcels & Disputes...")
    for proj in created_projects:
        # Determine number of parcels (12-18 per project)
        num_parcels = random.randint(12, 18)
        accumulated_acres = 0.0
        
        for i in range(num_parcels):
            survey_no = f"{random.randint(100, 999)}/{random.randint(1, 10)}"
            owner = random.choice(LAND_OWNERS) + f" & family" if random.random() < 0.2 else random.choice(LAND_OWNERS)
            
            # Divide target acres reasonably
            parcel_acres = round(random.uniform(1.5, proj.target_acres / (num_parcels - 2)), 2)
            accumulated_acres += parcel_acres
            
            l_type = random.choice(LAND_TYPES)
            rate_per_acre, multiplier = get_valuation_rules(l_type)
            
            market_val = parcel_acres * rate_per_acre
            solatium = market_val * multiplier # 100% of (Market Value * Multiplier)
            assets = round(random.uniform(50000.0, 300000.0), 2) if random.random() < 0.7 else 0.0
            
            total_comp = (market_val * multiplier) + solatium + assets
            
            # Determine status based on project phase
            p_status = "Pending"
            disbursed_date = None
            
            if proj.status == "Completed":
                p_status = "Paid"
                disbursed_date = proj.created_at + timedelta(days=random.randint(30, 55))
            elif proj.status == "Disbursement":
                r_val = random.random()
                if r_val < 0.6:
                    p_status = "Paid"
                    disbursed_date = datetime.utcnow() - timedelta(days=random.randint(2, 20))
                elif r_val < 0.85:
                    p_status = "Valued"
                else:
                    p_status = "Disputed"
            elif proj.status == "Valuation":
                p_status = "Valued" if random.random() < 0.8 else "Pending"
            elif proj.status == "Notification":
                p_status = "Notified"
                
            parcel = LandParcel(
                project_id=proj.id,
                survey_number=survey_no,
                owner_name=owner,
                area_acres=parcel_acres,
                land_type=l_type,
                market_value=market_val,
                multiplier=multiplier,
                solatium=solatium,
                assets_value=assets,
                total_compensation=total_comp,
                status=p_status,
                disbursement_date=disbursed_date
            )
            db.add(parcel)
            db.commit() # Save to get ID
            
            # If the parcel is disputed, add a dispute record
            if p_status == "Disputed":
                dispute_type = random.choice(["Compensation Amount", "Ownership Title", "Measurement Border"])
                desc = ""
                if dispute_type == "Compensation Amount":
                    desc = f"Owner objects to market value calculation of {l_type} land. Claims nearby market transactions justify a 25% higher circle rate."
                elif dispute_type == "Ownership Title":
                    desc = "Title dispute raised by co-sharers claiming ancestral inheritance share is not correctly reflected in mutation records."
                else:
                    desc = "Boundary survey correction requested. Owner claims the highway alignment cuts 0.4 acres more than the recorded survey size."
                    
                dispute = Dispute(
                    parcel_id=parcel.id,
                    dispute_type=dispute_type,
                    raised_by=owner,
                    description=desc,
                    status=random.choice(["Pending", "In Hearing"]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))
                )
                db.add(dispute)
                db.commit()

        # Update project target acres to match sum of parcels for consistency
        proj.target_acres = round(accumulated_acres, 2)
        db.commit()
        
    print("Database seeding completed successfully!")
    db.close()

if __name__ == "__main__":
    seed_database()
