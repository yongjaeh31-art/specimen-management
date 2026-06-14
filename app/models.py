from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    batch_type: Mapped[str] = mapped_column(String(20), nullable=False, default="1차")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_no: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    patient_name: Mapped[str | None] = mapped_column(String(120))
    patient_age: Mapped[str | None] = mapped_column(String(40))
    patient_id: Mapped[str | None] = mapped_column(String(120))
    hospital_name: Mapped[str | None] = mapped_column(String(120))
    specimen_name: Mapped[str | None] = mapped_column(String(120))
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    is_in_final_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tests: Mapped[list["OrderTest"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    arrivals: Mapped[list["SpecimenArrival"]] = relationship(back_populates="order")


class OrderTest(Base):
    __tablename__ = "order_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    test_code: Mapped[str | None] = mapped_column(String(80))
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_major: Mapped[str] = mapped_column(String(40), nullable=False, default="기타/확인필요")
    aliquot_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    order: Mapped[Order] = relationship(back_populates="tests")


class SpecimenArrival(Base):
    __tablename__ = "specimen_arrivals"
    __table_args__ = (UniqueConstraint("accession_no", "specimen_category", name="uq_arrival_accession_category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    specimen_category: Mapped[str] = mapped_column(String(40), nullable=False)
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    arrived_by: Mapped[str | None] = mapped_column(String(80))
    workstation_name: Mapped[str | None] = mapped_column(String(120))
    is_prearrival: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unregistered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    order: Mapped[Order | None] = relationship(back_populates="arrivals")


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    scan_type: Mapped[str] = mapped_column(String(40), nullable=False)
    specimen_category: Mapped[str | None] = mapped_column(String(40))
    culture_type: Mapped[str | None] = mapped_column(String(80))
    result_status: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    client_name: Mapped[str | None] = mapped_column(String(120))
    operator_name: Mapped[str | None] = mapped_column(String(80))
    workstation_name: Mapped[str | None] = mapped_column(String(120))
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DepartmentRoute(Base):
    __tablename__ = "department_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    department_major: Mapped[str] = mapped_column(String(40), nullable=False)
    test_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    department_major: Mapped[str] = mapped_column(String(40), nullable=False)
    aliquot_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CultureRule(Base):
    __tablename__ = "culture_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    culture_type: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    next_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MicroCultureAssignment(Base):
    __tablename__ = "micro_culture_assignments"
    __table_args__ = (UniqueConstraint("accession_no", "culture_type", name="uq_micro_accession_culture"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    culture_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    rack_no: Mapped[int] = mapped_column(Integer, nullable=False)
    hole_no: Mapped[int] = mapped_column(Integer, nullable=False)
    hole_code: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MicroCulturePlan(Base):
    """업로드 시 자동 생성되는 미생물 소분류 예정 목록 — LIS순 사전 부여"""
    __tablename__ = "micro_culture_plans"
    __table_args__ = (
        UniqueConstraint("accession_no", "culture_type", name="uq_micro_plan"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    culture_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    lis_order: Mapped[int] = mapped_column(Integer, nullable=False)          # 접수번호 오름차순 고정 순번
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")  # PENDING | DONE
    assignment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 스캔 완료 후 연결
    planned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DepartmentSubcategoryRule(Base):
    __tablename__ = "department_subcategory_rules"
    __table_args__ = (UniqueConstraint("department_name", "subcategory", name="uq_department_subcategory_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_name: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    subcategory: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    next_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RegisteredPC(Base):
    __tablename__ = "registered_pcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pc_name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    registered_by: Mapped[str | None] = mapped_column(String(80))


class DepartmentSubcategoryAssignment(Base):
    __tablename__ = "department_subcategory_assignments"
    __table_args__ = (
        UniqueConstraint("accession_no", "department_name", "subcategory", name="uq_department_subcategory_assignment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_no: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    department_name: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    subcategory: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    rack_no: Mapped[int] = mapped_column(Integer, nullable=False)
    hole_no: Mapped[int] = mapped_column(Integer, nullable=False)
    location_code: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_by: Mapped[str | None] = mapped_column(String(80))
    workstation_name: Mapped[str | None] = mapped_column(String(120))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
