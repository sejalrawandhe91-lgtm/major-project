import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///land_acquisition.db"

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    requiring_agency = Column(String, nullable=False)
    state = Column(String, nullable=False)
    status = Column(String, default="Initiated")  # Initiated, Surveying, Notification, Valuation, Disbursement, Completed
    target_acres = Column(Float, nullable=False)
    budget_cr = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    parcels = relationship("LandParcel", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'requiring_agency': self.requiring_agency,
            'state': self.state,
            'status': self.status,
            'target_acres': self.target_acres,
            'budget_cr': self.budget_cr,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LandParcel(Base):
    __tablename__ = 'land_parcels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    survey_number = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    area_acres = Column(Float, nullable=False)
    land_type = Column(String, nullable=False)  # Agricultural, Residential, Commercial
    market_value = Column(Float, nullable=False)
    multiplier = Column(Float, default=1.0)
    solatium = Column(Float, nullable=False)
    assets_value = Column(Float, default=0.0)
    total_compensation = Column(Float, nullable=False)
    status = Column(String, default="Pending")  # Pending, Notified, Valued, Paid, Disputed
    disbursement_date = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="parcels")
    disputes = relationship("Dispute", back_populates="parcel", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'survey_number': self.survey_number,
            'owner_name': self.owner_name,
            'area_acres': self.area_acres,
            'land_type': self.land_type,
            'market_value': self.market_value,
            'multiplier': self.multiplier,
            'solatium': self.solatium,
            'assets_value': self.assets_value,
            'total_compensation': self.total_compensation,
            'status': self.status,
            'disbursement_date': self.disbursement_date.isoformat() if self.disbursement_date else None
        }

class Dispute(Base):
    __tablename__ = 'disputes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    parcel_id = Column(Integer, ForeignKey('land_parcels.id'), nullable=False)
    dispute_type = Column(String, nullable=False)  # Compensation Amount, Ownership Title, Measurement Border
    raised_by = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="Pending")  # Pending, In Hearing, Resolved
    resolution_details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    parcel = relationship("LandParcel", back_populates="disputes")

    def to_dict(self):
        return {
            'id': self.id,
            'parcel_id': self.parcel_id,
            'dispute_type': self.dispute_type,
            'raised_by': self.raised_by,
            'description': self.description,
            'status': self.status,
            'resolution_details': self.resolution_details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
