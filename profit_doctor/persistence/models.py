"""SQLAlchemy 2.x core product models.

These tables establish production-grade ownership, tenancy, run versioning and
transaction semantics. The legacy diagnostic tables are migrated incrementally via
Alembic after behavioural equivalence gates.
"""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Client(Base):
    __tablename__ = "client"
    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    business_model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    runs: Mapped[list["EngineRun"]] = relationship(back_populates="client", cascade="all, delete-orphan")

class EngineRun(Base):
    __tablename__ = "engine_run"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("client.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_run_id: Mapped[str | None] = mapped_column(String(64))
    baseline_run_id: Mapped[str | None] = mapped_column(String(64))
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    client: Mapped[Client] = relationship(back_populates="runs")

class OpportunityRelationship(Base):
    __tablename__ = "opportunity_relationship_v2"
    __table_args__ = (UniqueConstraint("client_id","run_id","pair_key","relationship_type",name="uq_opportunity_relationship_pair"),)
    relationship_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("client.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("engine_run.run_id", ondelete="RESTRICT"), nullable=False, index=True)
    from_opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    to_opportunity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    pair_key: Mapped[str] = mapped_column(String(140), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    overlap_amount: Mapped[str | None] = mapped_column(String(80))
    evidence_basis: Mapped[str] = mapped_column(Text, nullable=False)

# v2.9 economic backbone. Monetary values remain canonical decimal strings during
# strangler migration so persistence changes cannot alter legacy arithmetic/rounding.
class PrimitiveResult(Base):
    __tablename__='primitive_result_v2'
    primitive_result_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False,index=True); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False,index=True); primitive_id: Mapped[str]=mapped_column(String(64),nullable=False); method_id: Mapped[str]=mapped_column(String(64),nullable=False); numeric_value: Mapped[str|None]=mapped_column(String(80)); unit: Mapped[str]=mapped_column(String(32),nullable=False); result_status: Mapped[str]=mapped_column(String(32),nullable=False); calculated_at: Mapped[str]=mapped_column(String(40),nullable=False)
class TestExecution(Base):
    __tablename__='test_execution_v2'
    test_execution_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False,index=True)
    client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False,index=True)
    test_id: Mapped[str]=mapped_column(String(32),nullable=False,index=True)
    method_id: Mapped[str|None]=mapped_column(String(80))
    eligibility_state: Mapped[str]=mapped_column(String(32),nullable=False)
    execution_status: Mapped[str]=mapped_column(String(32),nullable=False)
    signal_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    limitation: Mapped[str|None]=mapped_column(Text)
    started_at: Mapped[str]=mapped_column(String(40),nullable=False)
    completed_at: Mapped[str]=mapped_column(String(40),nullable=False)

class Signal(Base):
    __tablename__='signal_v2'
    signal_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    test_execution_id: Mapped[str|None]=mapped_column(String(64),index=True)
    run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False,index=True)
    client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False,index=True)
    test_id: Mapped[str]=mapped_column(String(32),nullable=False)
    signal_type: Mapped[str]=mapped_column(String(80),nullable=False)
    entity_type: Mapped[str|None]=mapped_column(String(64)); entity_id: Mapped[str|None]=mapped_column(String(128))
    period_from: Mapped[str|None]=mapped_column(String(40)); period_to: Mapped[str|None]=mapped_column(String(40))
    observed_value: Mapped[str|None]=mapped_column(String(80)); comparison_value: Mapped[str|None]=mapped_column(String(80)); variance_value: Mapped[str|None]=mapped_column(String(80))
    unit: Mapped[str|None]=mapped_column(String(32)); materiality_state: Mapped[str]=mapped_column(String(32),nullable=False,default='INFORMATIONAL'); status: Mapped[str]=mapped_column(String(32),nullable=False,default='ACTIVE')
    evidence_summary: Mapped[str]=mapped_column(Text,nullable=False); source_primitive_id: Mapped[str|None]=mapped_column(String(64)); created_at: Mapped[str]=mapped_column(String(40),nullable=False)

class DiagnosticLineage(Base):
    __tablename__='diagnostic_lineage_v2'
    diagnostic_lineage_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    signal_id: Mapped[str]=mapped_column(ForeignKey('signal_v2.signal_id',ondelete='CASCADE'),nullable=False,index=True)
    source_object_type: Mapped[str]=mapped_column(String(64),nullable=False); source_object_id: Mapped[str]=mapped_column(String(128),nullable=False)
    relationship_type: Mapped[str]=mapped_column(String(64),nullable=False); scope_definition: Mapped[str|None]=mapped_column(Text)

class Finding(Base):
    __tablename__='finding_v2'; finding_id: Mapped[str]=mapped_column(String(64),primary_key=True); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False,index=True); finding_type: Mapped[str]=mapped_column(String(32),nullable=False); title: Mapped[str]=mapped_column(String(255),nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); first_run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); last_run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False); updated_at: Mapped[str]=mapped_column(String(40),nullable=False)
class EconomicStory(Base):
    __tablename__='economic_story_v2'; __table_args__=(UniqueConstraint('client_id','story_key',name='uq_story_v2_client_key'),); economic_story_id: Mapped[str]=mapped_column(String(64),primary_key=True); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False,index=True); story_key: Mapped[str]=mapped_column(String(255),nullable=False); story_type: Mapped[str]=mapped_column(String(32),nullable=False); title: Mapped[str]=mapped_column(String(255),nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); first_run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); last_run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False); updated_at: Mapped[str]=mapped_column(String(40),nullable=False)
class EconomicImpact(Base):
    __tablename__='economic_impact_v2'; impact_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); economic_story_id: Mapped[str]=mapped_column(ForeignKey('economic_story_v2.economic_story_id',ondelete='RESTRICT'),nullable=False); impact_type: Mapped[str]=mapped_column(String(64),nullable=False); primary_economic_measure: Mapped[str]=mapped_column(String(64),nullable=False); amount: Mapped[str|None]=mapped_column(String(80)); currency: Mapped[str]=mapped_column(String(3),nullable=False); attribution_state: Mapped[str]=mapped_column(String(40),nullable=False); calculation_basis: Mapped[str]=mapped_column(Text,nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
class EconomicExposure(Base):
    __tablename__='economic_exposure_v2'; exposure_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); economic_story_id: Mapped[str]=mapped_column(ForeignKey('economic_story_v2.economic_story_id',ondelete='RESTRICT'),nullable=False); exposure_type: Mapped[str]=mapped_column(String(64),nullable=False); amount: Mapped[str|None]=mapped_column(String(80)); currency: Mapped[str]=mapped_column(String(3),nullable=False); exposure_pathway: Mapped[str]=mapped_column(Text,nullable=False); evidence_basis: Mapped[str]=mapped_column(Text,nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
class OpportunityCandidate(Base):
    __tablename__='opportunity_candidate_v2'; opportunity_candidate_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); economic_story_id: Mapped[str]=mapped_column(ForeignKey('economic_story_v2.economic_story_id',ondelete='RESTRICT'),nullable=False); finding_id: Mapped[str]=mapped_column(ForeignKey('finding_v2.finding_id',ondelete='RESTRICT'),nullable=False); mechanism_id: Mapped[str|None]=mapped_column(String(64)); purpose: Mapped[str]=mapped_column(String(32),nullable=False); benefit_type: Mapped[str]=mapped_column(String(64),nullable=False); theoretical_amount: Mapped[str|None]=mapped_column(String(80)); addressable_amount: Mapped[str|None]=mapped_column(String(80)); expected_amount: Mapped[str|None]=mapped_column(String(80)); currency: Mapped[str]=mapped_column(String(3),nullable=False); availability_state: Mapped[str]=mapped_column(String(32),nullable=False); candidate_status: Mapped[str]=mapped_column(String(40),nullable=False); limitation: Mapped[str|None]=mapped_column(Text); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
class Opportunity(Base):
    __tablename__='opportunity_v2'; opportunity_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); economic_story_id: Mapped[str]=mapped_column(ForeignKey('economic_story_v2.economic_story_id',ondelete='RESTRICT'),nullable=False); finding_id: Mapped[str]=mapped_column(ForeignKey('finding_v2.finding_id',ondelete='RESTRICT'),nullable=False); mechanism_id: Mapped[str]=mapped_column(String(64),nullable=False); purpose: Mapped[str]=mapped_column(String(32),nullable=False); benefit_type: Mapped[str]=mapped_column(String(64),nullable=False); theoretical_amount: Mapped[str|None]=mapped_column(String(80)); addressable_amount: Mapped[str]=mapped_column(String(80),nullable=False); expected_amount: Mapped[str]=mapped_column(String(80),nullable=False); currency: Mapped[str]=mapped_column(String(3),nullable=False); availability_state: Mapped[str]=mapped_column(String(32),nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
class Decision(Base):
    __tablename__='decision_v2'; decision_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); opportunity_id: Mapped[str]=mapped_column(ForeignKey('opportunity_v2.opportunity_id',ondelete='RESTRICT'),nullable=False); selected_course: Mapped[str]=mapped_column(Text,nullable=False); rationale: Mapped[str]=mapped_column(Text,nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); decided_at: Mapped[str]=mapped_column(String(40),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
class Action(Base):
    __tablename__='action_v2'; action_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); decision_id: Mapped[str]=mapped_column(ForeignKey('decision_v2.decision_id',ondelete='RESTRICT'),nullable=False); opportunity_id: Mapped[str]=mapped_column(ForeignKey('opportunity_v2.opportunity_id',ondelete='RESTRICT'),nullable=False); description: Mapped[str]=mapped_column(Text,nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False); updated_at: Mapped[str]=mapped_column(String(40),nullable=False)
class BenefitLeg(Base):
    __tablename__='benefit_leg_v2'; benefit_leg_id: Mapped[str]=mapped_column(String(64),primary_key=True); run_id: Mapped[str]=mapped_column(ForeignKey('engine_run.run_id',ondelete='RESTRICT'),nullable=False); client_id: Mapped[str]=mapped_column(ForeignKey('client.client_id',ondelete='RESTRICT'),nullable=False); opportunity_id: Mapped[str]=mapped_column(ForeignKey('opportunity_v2.opportunity_id',ondelete='RESTRICT'),nullable=False); action_id: Mapped[str]=mapped_column(ForeignKey('action_v2.action_id',ondelete='RESTRICT'),nullable=False); benefit_type: Mapped[str]=mapped_column(String(64),nullable=False); gross_amount: Mapped[str]=mapped_column(String(80),nullable=False); implementation_cost: Mapped[str]=mapped_column(String(80),nullable=False); ongoing_cost: Mapped[str]=mapped_column(String(80),nullable=False); adverse_effect: Mapped[str]=mapped_column(String(80),nullable=False); net_amount: Mapped[str]=mapped_column(String(80),nullable=False); currency: Mapped[str]=mapped_column(String(3),nullable=False); attribution_state: Mapped[str]=mapped_column(String(40),nullable=False); status: Mapped[str]=mapped_column(String(32),nullable=False); created_at: Mapped[str]=mapped_column(String(40),nullable=False)
