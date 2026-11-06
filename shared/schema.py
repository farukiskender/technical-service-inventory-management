"""
Shared database models and configuration for Teknik Servis ve Stok Yönetim Sistemi.
"""

import json
import os
from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float, JSON, create_engine, inspect, text
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "db_config.json")


class Base(DeclarativeBase):
    pass


# ─── Users & Roles ──────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    can_view = Column(Boolean, default=True)
    can_create = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    title = Column(String(200))
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    stock_movements = relationship("StockMovement", back_populates="user")


# ─── Products & Warehouses ───────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    unit = Column(String(50), default="Adet")
    category = Column(String(100))
    image_path = Column(String(500))
    serial_tracking = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stock_movements = relationship("StockMovement", back_populates="product")
    serial_numbers = relationship("SerialNumber", back_populates="product")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    location = Column(String(200))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stock_movements = relationship("StockMovement", back_populates="warehouse")


class SerialNumber(Base):
    __tablename__ = "serial_numbers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    serial_no = Column(String(200), nullable=False)
    status = Column(String(50), default="available")  # available / used / reserved
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))

    product = relationship("Product", back_populates="serial_numbers")
    warehouse = relationship("Warehouse")


# ─── Stock Movements ─────────────────────────────────────────────────────────

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    movement_type = Column(String(30), nullable=False)  # IN / OUT / TRANSFER_IN / TRANSFER_OUT / SERVICE_OUT
    quantity = Column(Float, nullable=False)
    serial_numbers_json = Column(JSON)
    reason = Column(String(500))
    reference_id = Column(Integer)
    reference_type = Column(String(50))  # TRANSFER / MANUAL
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="stock_movements")
    warehouse = relationship("Warehouse", back_populates="stock_movements")
    user = relationship("User", back_populates="stock_movements")








# ─── Persons & Customers ───────────────────────────────────────────────────

class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    tc_no = Column(String(11))
    title = Column(String(200))
    phone = Column(String(50), nullable=False)
    email = Column(String(200))
    address = Column(Text)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_records = relationship("ServiceRecord", back_populates="person")


# ─── Service Records & Items ───────────────────────────────────────────────

class ServiceRecord(Base):
    __tablename__ = "service_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_no = Column(String(50), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    customer_name = Column(String(200))
    customer_phone = Column(String(50))
    device_info = Column(String(255), nullable=False)
    device_serial = Column(String(200))
    complaint = Column(Text, nullable=False)
    status = Column(String(50), default="Kayıt Alındı")  # Kayıt Alındı, İncelemede, Onay Bekliyor, Onarıldı, Teslim Edildi, İptal Edildi
    work_done = Column(Text)
    notes = Column(Text)
    delivered_by = Column(String(200))   # Cihazı teslim eden kişi
    received_by = Column(String(200))    # Teslim alan personel
    delivered_to = Column(String(200))   # Teslim edilen müşteri/kişi
    received_from = Column(String(200))  # Teslim eden personel
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    person = relationship("Person", back_populates="service_records")
    user = relationship("User")
    items = relationship("ServiceItem", back_populates="service_record", cascade="all, delete-orphan")
    history = relationship("ServiceHistory", back_populates="service_record", cascade="all, delete-orphan", order_by="ServiceHistory.created_at.desc()")


class ServiceItem(Base):
    __tablename__ = "service_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("service_records.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    quantity = Column(Float, default=1.0)
    serial_number = Column(String(200), nullable=True)
    stock_movement_id = Column(Integer, ForeignKey("stock_movements.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_record = relationship("ServiceRecord", back_populates="items")
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    stock_movement = relationship("StockMovement")


class ServiceHistory(Base):
    __tablename__ = "service_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("service_records.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    old_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_record = relationship("ServiceRecord", back_populates="history")
    user = relationship("User")


# ─── App Config ──────────────────────────────────────────────────────────────

class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text)


# ─── DB Connection Helpers ───────────────────────────────────────────────────

def load_db_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def build_connection_url(config: dict) -> str:
    db_type = config.get("type", "sqlite").lower()

    if db_type == "sqlite":
        path = config.get("path", "teknik_servis.db")
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(CONFIG_PATH), path)
        return f"sqlite:///{path}"

    host = config.get("host", "localhost")
    port = config.get("port")
    user = config.get("user", "")
    password = config.get("password", "")
    database = config.get("database", "teknik_servis")
    encoded_pw = quote_plus(str(password)) if password else ""
    user_pass = f"{user}:{encoded_pw}@" if user else ""

    if db_type in ("postgresql", "postgres"):
        port_str = f":{port}" if port else ":5432"
        return f"postgresql+psycopg2://{user_pass}{host}{port_str}/{database}"

    if db_type in ("mssql", "sqlserver"):
        port_str = f":{port}" if port else ":1433"
        driver = config.get("driver", "ODBC Driver 17 for SQL Server")
        driver_str = quote_plus(driver)
        return f"mssql+pyodbc://{user_pass}{host}{port_str}/{database}?driver={driver_str}"

    if db_type == "mysql":
        port_str = f":{port}" if port else ":3306"
        return f"mysql+pymysql://{user_pass}{host}{port_str}/{database}"

    path = config.get("path", "teknik_servis.db")
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(CONFIG_PATH), path)
    return f"sqlite:///{path}"


def get_engine(config: dict):
    url = build_connection_url(config)
    db_type = config.get("type", "sqlite").lower()
    if db_type == "sqlite":
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def create_all_tables(engine):
    Base.metadata.create_all(engine)


def migrate_database(engine):
    """Mevcut veritabanına eksik tabloları ve sütunları güvenli şekilde ekler."""
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    migrations = [
        # (tablo_adı, sütun_adı, SQL tipi, varsayılan)
        ("users", "title", "VARCHAR(200)", None),
        ("products", "image_path", "VARCHAR(500)", None),
        ("service_records", "delivered_by", "VARCHAR(200)", None),
        ("service_records", "received_by", "VARCHAR(200)", None),
        ("service_records", "delivered_to", "VARCHAR(200)", None),
        ("service_records", "received_from", "VARCHAR(200)", None),
        ("service_records", "work_done", "TEXT", None),
    ]

    with engine.connect() as conn:
        for table, column, col_type, default in migrations:
            if table in inspector.get_table_names():
                existing = [c["name"] for c in inspector.get_columns(table)]
                if column not in existing:
                    default_clause = f" DEFAULT '{default}'" if default else ""
                    sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"
                    conn.execute(text(sql))
                    conn.commit()


def get_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
