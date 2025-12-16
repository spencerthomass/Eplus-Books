from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import date

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Tables (Models) ---
class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class DailyLog(Base):
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))
    date = Column(Date, default=date.today)
    starting_cash = Column(Float, default=0.0)
    closing_cash = Column(Float, default=0.0)
    deposit = Column(Float, default=0.0)
    status = Column(String, default="OPEN") # OPEN, CLOSED

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    daily_log_id = Column(Integer, ForeignKey("daily_logs.id"))
    
    # Vehicle Info
    vehicle_make = Column(String)
    vin = Column(String, nullable=True)
    plate = Column(String, nullable=True)
    
    # The Checkboxes from your sheet
    is_dmv = Column(Boolean, default=False)
    is_tsi = Column(Boolean, default=False)
    is_safety = Column(Boolean, default=False)
    is_renewal = Column(Boolean, default=False)
    
    # Cert Numbers
    emis_cert_num = Column(String, nullable=True)
    dmv_num = Column(String, nullable=True)
    
    # Money
    total_amount = Column(Float)
    payment_method = Column(String) # CASH, CC, FLEET

Base.metadata.create_all(bind=engine)

# --- The App API ---
app = FastAPI(title="Emissions Tracker")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Start a New Day (Opening Cash)
class DayStart(BaseModel):
    location_id: int
    starting_cash: float

@app.post("/start-day/")
def start_day(day_data: DayStart, db: Session = Depends(get_db)):
    new_log = DailyLog(
        location_id=day_data.location_id, 
        starting_cash=day_data.starting_cash,
        date=date.today()
    )
    db.add(new_log)
    db.commit()
    return {"status": "Day Started", "log_id": new_log.id}

# 2. Add a Transaction (Vehicle)
class TransactionCreate(BaseModel):
    daily_log_id: int
    vehicle_make: str
    is_dmv: bool = False
    is_safety: bool = False
    total_amount: float
    payment_method: str

@app.post("/add-transaction/")
def add_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    new_tx = Transaction(**tx.dict())
    db.add(new_tx)
    db.commit()
    return {"status": "Saved"}

# 3. Get End-of-Day Report (Balancing)
@app.get("/balance-day/{daily_log_id}")
def balance_day(daily_log_id: int, db: Session = Depends(get_db)):
    # Calculate totals automatically like your sheet
    transactions = db.query(Transaction).filter(Transaction.daily_log_id == daily_log_id).all()
    
    total_sales = sum(t.total_amount for t in transactions)
    cash_sales = sum(t.total_amount for t in transactions if t.payment_method == "CASH")
    cc_sales = sum(t.total_amount for t in transactions if t.payment_method == "CC")
    
    log = db.query(DailyLog).filter(DailyLog.id == daily_log_id).first()
    expected_cash = log.starting_cash + cash_sales
    
    return {
        "total_sales": total_sales,
        "cash_sales": cash_sales,
        "credit_card_sales": cc_sales,
        "expected_drawer_cash": expected_cash
    }