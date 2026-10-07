"""Authenticated cross-export Revenue component relationships, never inferred matches."""
import csv
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, LineageReference
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from .contracts import EvidenceScope, EvidenceDeclaration
from .semantics import RegisteredSemanticSource
from .source import RegisteredAccountingSource


class ComponentRecordPair(Contract):
    revenue_record_id: Identifier
    contribution_record_id: Identifier
    underlying_source_record: str = Field(min_length=1)


class ComponentManifest(Contract):
    schema_version: Literal['C0-COMPONENT-MANIFEST-2.55.1'] = 'C0-COMPONENT-MANIFEST-2.55.1'
    scope: EvidenceScope
    revenue_owner_id: Identifier
    contribution_owner_id: Identifier
    revenue_version_id: Identifier
    contribution_version_id: Identifier
    source_system_id: Identifier
    economic_observation_reference: str = Field(min_length=1)
    relationship_reference: str = Field(min_length=1)
    population_relationship: Literal['EXACT_EQUIVALENT', 'SUBSET', 'SUPERSET', 'PARTIAL_OVERLAP', 'UNKNOWN', 'CONTRADICTORY']
    declarations: tuple[EvidenceDeclaration, ...] = ()
    revenue_definition: Literal['NET_REVENUE', 'UNKNOWN']
    revenue_population: str = Field(min_length=1)
    contribution_population: str = Field(min_length=1)
    revenue_inclusion_exclusion: str = Field(min_length=1)
    contribution_inclusion_exclusion: str = Field(min_length=1)
    pairs: tuple[ComponentRecordPair, ...] = ()
    revision: int = Field(strict=True, ge=1)
    predecessor_version_id: Identifier | None = None
    change_kind: Literal['ORIGINAL', 'RESTATEMENT', 'CORRECTION', 'UNKNOWN']
    change_reference: str | None = None

    @model_validator(mode='after')
    def relationship_identity(self):
        if any(d.client_id != self.scope.client_id for d in self.declarations):
            raise ScopeError('Component declarations cannot cross client scope')
        for key in ('revenue_record_id', 'contribution_record_id', 'underlying_source_record'):
            values = [getattr(pair, key) for pair in self.pairs]
            if len(values) != len(set(values)):
                raise ValueError('Component relationship must be a one-to-one source-supported mapping')
        if (self.revision == 1) != (self.predecessor_version_id is None):
            raise ValueError('Component manifest revision requires its registered predecessor')
        return self


class ComponentBinding(Contract):
    schema_version: Literal['C0-COMPONENT-BINDING-2.55.1'] = 'C0-COMPONENT-BINDING-2.55.1'
    qualification_contract: Literal['C0_REVENUE_COMPONENT_EQUIVALENCE_1'] = 'C0_REVENUE_COMPONENT_EQUIVALENCE_1'
    binding_id: Identifier
    series_id: Identifier
    client_id: Identifier
    run_id: Identifier
    revenue_owner_id: Identifier
    contribution_owner_id: Identifier
    proof_version_id: Identifier
    proof_digest: str
    proof: ComponentManifest
    source_authority: Literal['SOURCE_DATA', 'UNKNOWN', 'MANAGEMENT_ASSERTION', 'HUMAN_FD_JUDGEMENT']
    status: Literal['QUALIFIED', 'REFUSED']
    reasons: tuple[str, ...]
    lineage: tuple[LineageReference, ...] = Field(min_length=1)
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    limitations: tuple[str, ...] = ('Equivalence of the named Revenue components only; no causal or temporal conclusion.',)

    @model_validator(mode='after')
    def scoped(self):
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError('Binding revision requires its explicit predecessor')
        if self.proof.scope.client_id != self.client_id or any(r.client_id != self.client_id for r in self.lineage):
            raise ScopeError('Foreign component lineage')
        if (self.proof.revenue_owner_id, self.proof.contribution_owner_id) != (self.revenue_owner_id, self.contribution_owner_id):
            raise ValueError('Component owner envelope disagrees with authenticated proof')
        if self.status == 'QUALIFIED' and (self.reasons or self.source_authority != 'SOURCE_DATA' or
                self.proof.population_relationship != 'EXACT_EQUIVALENT' or not self.proof.pairs):
            raise ValueError('Qualified component binding requires affirmative source evidence')
        if self.status == 'REFUSED' and not self.reasons:
            raise ValueError('Refused binding requires explicit reasons')
        return self


class ComponentSource(RegisteredSemanticSource):
    def proof(self, version):
        profile = 'production-evidence:c0-component-manifest-1'
        row = self.metadata(version, profile)
        path = Path(row['storage_location'])
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['evidence']:
                raise ValueError('Component transport requires its exact evidence column')
            rows = list(reader)
        if len(rows) != 1 or row['row_count'] != 1 or set(rows[0]) != {'evidence'}:
            raise ValueError('Exactly one component manifest required')
        proof = ComponentManifest.from_json(rows[0]['evidence'])
        if proof.scope.client_id != self.client_id:
            raise ScopeError('Component manifest belongs to another client')
        if sha256(path) != row['file_hash']:
            raise RevisionConflict('Retained component manifest changed')
        authority = self.authority_resolver(self.client_id, version, profile, row['file_hash'])
        return proof, row, authority


def binding_reasons(proof, authority, revenue, contribution, connection):
    """Source attestation is necessary; arithmetic/metadata only detect contradictions."""
    reasons = []
    if authority != 'SOURCE_DATA':
        reasons.append('SOURCE_AUTHORITATIVE_COMPONENT_RELATIONSHIP_REQUIRED')
    if proof.population_relationship != 'EXACT_EQUIVALENT':
        reasons.append('EXACT_REVENUE_POPULATION_EQUIVALENCE_REQUIRED')
    expected_declarations = {'population': proof.population_relationship, 'definition': proof.revenue_definition,
        'organisational_scope': proof.scope.ledger_id, 'currency': proof.scope.currency, 'unit': 'MONEY',
        'time_basis': proof.scope.period.basis.value, 'inclusion_exclusion': proof.revenue_inclusion_exclusion}
    for declaration in proof.declarations:
        if declaration.dimension not in expected_declarations:
            reasons.append('COMPONENT_DECLARATION_DIMENSION_UNVERIFIED')
        elif declaration.claim != expected_declarations[declaration.dimension]:
            reasons.append('CONTRADICTORY_COMPONENT_DECLARATION')
    if revenue.family != 'REVENUE' or contribution.family != 'CONTRIBUTION_0':
        reasons.append('SEPARATE_QUALIFIED_COMPONENT_OWNERS_REQUIRED')
    r, c = revenue.semantic, contribution.semantic
    if (proof.revenue_owner_id, proof.contribution_owner_id, proof.revenue_version_id, proof.contribution_version_id) != (
            revenue.measurement_id, contribution.measurement_id, r.contract.source_version.source_id, c.contract.source_version.source_id):
        reasons.append('AUTHENTICATED_COMPONENT_IDENTITIES_DISAGREE')
    # Definition differs deliberately between the full C0 population and its
    # Revenue component. The authenticated relationship identifies that component.
    for scope in (r.manifest.scope, c.manifest.scope):
        if (scope.client_id, scope.entity_id, scope.ledger_id, scope.period, scope.currency) != (
                proof.scope.client_id, proof.scope.entity_id, proof.scope.ledger_id, proof.scope.period, proof.scope.currency):
            reasons.append('COMPONENT_SCOPE_PERIOD_OR_CURRENCY_MISMATCH')
    if proof.scope.definition != 'NET_REVENUE' or proof.revenue_definition != 'NET_REVENUE':
        reasons.append('QUALIFIED_NET_REVENUE_DEFINITION_REQUIRED')
    if (proof.revenue_population, proof.contribution_population, proof.revenue_inclusion_exclusion,
            proof.contribution_inclusion_exclusion, proof.source_system_id) != (
            r.manifest.scope.population, c.manifest.scope.population, r.manifest.inclusion_exclusion,
            c.manifest.inclusion_exclusion, r.manifest.system_id) or proof.source_system_id != c.manifest.system_id:
        reasons.append('COMPONENT_SOURCE_POPULATION_OR_INCLUSION_MISMATCH')
    if proof.scope.population != proof.revenue_population:
        reasons.append('COMPONENT_PROOF_POPULATION_SCOPE_MISMATCH')
    if not proof.pairs:
        reasons.append('EXACT_SOURCE_RECORD_RELATIONSHIP_REQUIRED')
    if any(x is None for x in (r.mapping, c.mapping, r.chart, c.chart)):
        reasons.append('QUALIFIED_COMPONENT_DEFINITION_EVIDENCE_REQUIRED')
    else:
        for key in ('recognition_basis', 'revenue_basis', 'amount_convention'):
            if getattr(r.chart, key) != getattr(c.chart, key) or getattr(r.chart, key) == 'UNKNOWN':
                reasons.append('COMPONENT_REVENUE_DEFINITION_MISMATCH')
        source = RegisteredAccountingSource(connection, revenue.client_id)
        left = {x.record_id: x for x in source.read(proof.revenue_version_id) if x.account_code in r.mapping.revenue_accounts}
        right = {x.record_id: x for x in source.read(proof.contribution_version_id) if x.account_code in c.mapping.revenue_accounts}
        if set(left) != {p.revenue_record_id for p in proof.pairs} or set(right) != {p.contribution_record_id for p in proof.pairs}:
            reasons.append('COMPONENT_RECORD_MEMBERSHIP_MISMATCH')
        for pair in proof.pairs:
            a, b = left.get(pair.revenue_record_id), right.get(pair.contribution_record_id)
            if a is not None and b is not None and (a.amount != b.amount or a.account_code != b.account_code):
                reasons.append('SOURCE_COMPONENT_RELATIONSHIP_CONTRADICTED_BY_RECORDS')
    if revenue.revenue != contribution.revenue:
        reasons.append('SOURCE_COMPONENT_RELATIONSHIP_CONTRADICTED_BY_AMOUNTS')
    if proof.change_kind == 'UNKNOWN' or not proof.change_reference:
        reasons.append('COMPONENT_REVISION_AUTHORITY_REQUIRED')
    return tuple(sorted(set(reasons)))
