"""Domain-level semantic evidence; publication/measurement ownership is deferred.

Authority is obtained from a trusted application resolver, never from CSV/JSON
flags. Default authority is unknown. The resolver must authenticate the source
export issuer and its scoped report; registering a file is not authentication.
"""
import csv
from calendar import monthrange
from datetime import date
import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from profit_doctor.ingestion.northstar import sha256
from profit_doctor.reasoning.canonical.service import identity
from profit_doctor.reasoning.dataset.contracts import DatasetAssertion, DatasetContract, DatasetCoverage
from profit_doctor.reasoning.domain.contracts import Actor, Contract, Identifier, LineageReference, now
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from .contracts import EvidenceDeclaration, EvidenceScope
from .reconciliation import exact_sum, reconcile
from .source import DOMAIN, PROVIDER, RegisteredAccountingSource


class Manifest(Contract):
    schema_version: Literal['SOURCE-MANIFEST-2.55.1'] = 'SOURCE-MANIFEST-2.55.1'
    report_id: Identifier
    system_id: Identifier
    extraction_id: Identifier
    record_version_id: Identifier
    scope: EvidenceScope
    family: Literal['GENERAL_LEDGER', 'SALES_TRANSACTIONS']
    record_ids: tuple[Identifier, ...] | None = None
    record_count: int = Field(strict=True, ge=0)
    boundary: str = Field(min_length=1)
    inclusion_exclusion: str = Field(min_length=1)
    extraction_query: str | None = None
    # Raw export boundaries, not an internal COMPLETE or VERIFIED answer label.
    extraction_start: date | None = None
    extraction_end: date | None = None
    excluded_record_ids: tuple[Identifier, ...] = ()
    revision_id: Identifier
    predecessor_version_id: Identifier | None = None
    change_kind: Literal['ORIGINAL', 'CORRECTION', 'RESTATEMENT', 'SUPERSESSION', 'UNKNOWN'] = 'UNKNOWN'
    change_reference: str | None = None

    @model_validator(mode='after')
    def inventory(self):
        if self.record_ids is not None and (len(set(self.record_ids)) != len(self.record_ids)
                or len(self.record_ids) != self.record_count):
            raise ValueError('Manifest identities must be unique and agree with its count')
        if set(self.record_ids or ()) & set(self.excluded_record_ids):
            raise ValueError('Included and excluded identities cannot overlap')
        return self


class Mapping(Contract):
    schema_version: Literal['SOURCE-MAPPING-2.55.1'] = 'SOURCE-MAPPING-2.55.1'
    mapping_id: Identifier
    revision: int = Field(strict=True, ge=1)
    supersedes: Identifier | None = None
    scope: EvidenceScope
    effective_from: date
    effective_to: date
    actor: Actor
    recorded_at: AwareDatetime = Field(default_factory=now)
    definition: Literal['NET_REVENUE', 'REVENUE_MINUS_DIRECT_COST', 'UNKNOWN']
    # Account codes, never account names. Costs use the source's positive-cost sign.
    revenue_accounts: tuple[str, ...] = ()
    direct_cost_accounts: tuple[str, ...] = ()
    source_policy_reference: str | None = None
    source_chart_version: Identifier | None = None

    @model_validator(mode='after')
    def explicit(self):
        if not self.actor.actor_id or self.actor.actor_type not in ('HUMAN', 'MANAGEMENT', 'SYSTEM'):
            raise ValueError('Mapping requires an identified attributable actor')
        allowed_authorities = {'HUMAN': {'HUMAN_FD_JUDGEMENT'}, 'MANAGEMENT': {'MANAGEMENT_ASSERTION'},
                              'SYSTEM': {'SOURCE_DATA','SYSTEM_DERIVED'}}
        if self.actor.source_authority not in allowed_authorities[self.actor.actor_type]:
            raise ValueError('Mapping actor and authority disagree; no machine adviser')
        if self.effective_from > self.effective_to:
            raise ValueError('Mapping effective interval reversed')
        if (self.revision == 1) != (self.supersedes is None):
            raise ValueError('Mapping revision requires an explicit predecessor')
        for members in (self.revenue_accounts, self.direct_cost_accounts):
            if len(set(members)) != len(members):
                raise ValueError('Account membership must be unique')
        if set(self.revenue_accounts) & set(self.direct_cost_accounts):
            raise ValueError('Revenue and direct-cost memberships cannot overlap')
        return self


class SourceChart(Contract):
    schema_version: Literal['SOURCE-CHART-2.55.1'] = 'SOURCE-CHART-2.55.1'
    policy_reference: str = Field(min_length=1)
    scope: EvidenceScope
    effective_from: date
    effective_to: date
    definition: Literal['NET_REVENUE', 'REVENUE_MINUS_DIRECT_COST', 'UNKNOWN']
    recognition_basis: Literal['POSTED_ACCRUAL', 'CASH_RECEIPTS', 'UNKNOWN']
    revenue_basis: Literal['NET_OF_TAX_AND_CREDITS', 'UNKNOWN']
    cost_basis: Literal['ATTRIBUTABLE_DIRECT_COST_BEFORE_CTS_AND_OVERHEAD', 'NOT_APPLICABLE', 'UNKNOWN']
    amount_convention: Literal['POSITIVE_REVENUE_POSITIVE_COST', 'UNKNOWN']
    revenue_accounts: tuple[str, ...]
    direct_cost_accounts: tuple[str, ...] = ()

    @model_validator(mode='after')
    def explicit(self):
        if self.effective_from > self.effective_to or set(self.revenue_accounts) & set(self.direct_cost_accounts):
            raise ValueError('Source chart effective dates or account roles conflict')
        if any(len(set(a)) != len(a) for a in (self.revenue_accounts,self.direct_cost_accounts)):
            raise ValueError('Source chart account memberships are duplicated')
        return self


class SemanticAssessment(Contract):
    assessment_id: Identifier
    contract: DatasetContract
    states: dict[str, Literal['VERIFIED', 'DECLARED', 'INSUFFICIENT_EVIDENCE', 'MISMATCH', 'CONFLICTED']]
    reasons: dict[str, tuple[str, ...]]
    reconciliation: str
    manifest: Manifest
    mapping: Mapping | None
    chart: SourceChart | None
    source_versions: tuple[Identifier, ...]
    evidence_digest: str
    revision: int
    supersedes: Identifier | None = None
    limitations: tuple[str, ...] = ('Semantic evidence is not a monthly measurement or production temporal qualification.',)


class RegisteredSemanticSource:
    """Exact one-document CSV profile; application owns connection and authority."""
    def __init__(self, connection, client_id, authority_resolver=None):
        self.connection, self.client_id = connection, client_id
        self.authority_resolver = authority_resolver or (lambda *args: None)

    def metadata(self, version, profile):
        row = self.connection.execute('''SELECT d.dataset_id,d.client_id,d.data_domain,d.logical_dataset_key,
            v.ingestion_job_id,v.row_count,v.ingestion_status,f.source_file_id,f.client_id AS file_client,
            f.file_hash,f.storage_location,f.immutable_flag,j.client_id AS job_client,j.status,
            r.client_id AS run_client FROM dataset_version v JOIN dataset d ON d.dataset_id=v.dataset_id
            JOIN source_file f ON f.source_file_id=v.source_file_id
            JOIN ingestion_job j ON j.ingestion_job_id=v.ingestion_job_id
            JOIN engine_run r ON r.run_id=j.run_id WHERE v.dataset_version_id=?''', (version,)).fetchone()
        if row is None or any(row[k] != self.client_id for k in ('client_id','file_client','job_client','run_client')):
            raise ScopeError('Evidence version/file/job/run missing or foreign')
        if row['logical_dataset_key'] != profile or row['data_domain'] != DOMAIN:
            raise ScopeError('Unsupported evidence profile')
        if row['ingestion_status'] != 'COMPLETED' or row['status'] != 'COMPLETED':
            raise ScopeError('Evidence import incomplete')
        path = Path(row['storage_location'])
        if not row['immutable_flag'] or not path.is_file() or sha256(path) != row['file_hash']:
            raise RevisionConflict('Retained semantic evidence changed')
        return dict(row)

    def document(self, version, kind):
        profile = 'production-evidence:'+kind+'-1'
        row = self.metadata(version, profile)
        with Path(row['storage_location']).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['evidence']:
                raise ValueError('Semantic transport requires the exact evidence column')
            data = list(reader)
        if len(data) != 1 or row['row_count'] != 1 or set(data[0]) != {'evidence'}:
            raise ValueError('Semantic transport requires exactly one document')
        model = {'manifest': Manifest, 'mapping': Mapping, 'chart': SourceChart}[kind]
        value = model.from_json(data[0]['evidence'])
        if value.scope.client_id != self.client_id:
            raise ScopeError('Semantic document is foreign')
        if sha256(Path(row['storage_location'])) != row['file_hash']:
            raise RevisionConflict('Semantic file changed during read')
        # Only the trusted owner may resolve authority. Document fields cannot.
        authority = self.authority_resolver(self.client_id, version, profile, row['file_hash'])
        return value, row, authority

    def refs(self, version, row):
        return tuple(LineageReference(kind=kind, store='LEGACY_SQLITE', resource=resource,
            source_id=key, client_id=self.client_id) for kind,resource,key in (
                ('DATASET','dataset',row['dataset_id']), ('DATASET_VERSION','dataset_version',version),
                ('SOURCE_FILE','source_file',row['source_file_id'])))

    def same_period_roots(self, manifest):
        versions = self.connection.execute('''SELECT v.dataset_version_id FROM dataset_version v
            JOIN dataset d ON d.dataset_id=v.dataset_id WHERE d.client_id=? AND d.data_domain=?
            AND d.logical_dataset_key=? AND v.ingestion_status='COMPLETED' ''',
            (self.client_id,DOMAIN,'production-evidence:manifest-1')).fetchall()
        roots = set()
        for (version,) in versions:
            candidate, _, authority = self.document(version,'manifest')
            if candidate.scope == manifest.scope and candidate.system_id == manifest.system_id:
                if candidate.predecessor_version_id is None:
                    roots.add(candidate.record_version_id)
        return roots


class SemanticVerificationService:
    """Read-only, explicit history supplied by caller; persistence is deferred.

    No method accepts Dataset verified flags or caller-produced reconciliations.
    A configured authority resolver is a trusted application dependency, not an
    upload/request parameter. Unknown authority never produces verified claims.
    """
    def __init__(self, connection, client_id, run_id, authority_resolver=None):
        self.sources = RegisteredSemanticSource(connection, client_id, authority_resolver)
        self.connection, self.client_id, self.run_id = connection, client_id, run_id
        row = connection.execute('SELECT client_id FROM engine_run WHERE run_id=?', (run_id,)).fetchone()
        if row is None or row[0] != client_id:
            raise ScopeError('Semantic assessment requires a scoped run')

    def assess(self, record_version, control_version, manifest_version, *, mapping_version=None,
               declarations=(), previous=None):
        declarations = tuple(declarations)
        manifest, meta, authority = self.sources.document(manifest_version, 'manifest')
        if manifest.record_version_id != record_version:
            raise ScopeError('Manifest does not identify requested source version')
        records_meta = self.sources.metadata(record_version, PROVIDER)
        control_meta = self.sources.metadata(control_version, PROVIDER)
        records = RegisteredAccountingSource(self.connection, self.client_id).read(record_version)
        controls = RegisteredAccountingSource(self.connection, self.client_id).read(control_version)
        scope = manifest.scope
        if any(r.scope != scope for r in (*records, *controls)):
            raise ScopeError('Source/manifest/control scope, period, currency or definition differs')
        arithmetic = reconcile(scope, records, controls)
        mapping = None
        mapping_refs = ()
        mapping_authority = None
        chart = None
        chart_authority = None
        if mapping_version:
            mapping, mapping_meta, mapping_authority = self.sources.document(mapping_version, 'mapping')
            mapping_refs = self.sources.refs(mapping_version, mapping_meta)
            if mapping.scope != scope or not (scope.period.start and scope.period.end and
                    mapping.effective_from <= scope.period.start <= scope.period.end <= mapping.effective_to):
                raise ScopeError('Mapping scope/effective period disagrees')
            if mapping.source_chart_version:
                chart, chart_meta, chart_authority = self.sources.document(mapping.source_chart_version,'chart')
                if chart.scope != scope or not (scope.period.start and scope.period.end and
                        chart.effective_from <= scope.period.start <= scope.period.end <= chart.effective_to):
                    raise ScopeError('Source chart scope/effective period disagrees')
                mapping_refs += self.sources.refs(mapping.source_chart_version,chart_meta)
        refs = self.sources.refs(record_version, records_meta)
        witnesses = (*self.sources.refs(manifest_version, meta), *refs, *arithmetic.source_b)
        def source_authority(version,row):
            return self.sources.authority_resolver(self.client_id,version,PROVIDER,row['file_hash']) == 'SOURCE_DATA'
        trusted = authority == 'SOURCE_DATA' and source_authority(record_version,records_meta)
        control_kinds = {'TB_ACTIVITY','PNL'} if scope.period.nature == 'FLOW' else {'TB_CLOSING','BALANCE_SHEET'}
        trusted_control = (source_authority(control_version,control_meta) and bool(controls)
            and all(r.kind in control_kinds for r in controls)
            and control_meta['file_hash'] != records_meta['file_hash'])
        accounts_a = {r.account_code for r in records}
        accounts_b = {r.account_code for r in controls}
        control_accounts_match = accounts_a == accounts_b and all(
            exact_sum(r.amount for r in records if r.account_code == account) ==
            exact_sum(r.amount for r in controls if r.account_code == account) for account in accounts_a)
        claims, states, reasons = {}, {}, {}

        def claim(key, value, permitted, why, evidence=witnesses):
            claims[key] = DatasetAssertion(verified_value=value if permitted else None,
                verification_authority='SYSTEM_DERIVED' if permitted else None,
                verification_evidence=evidence if permitted else ())
            states[key] = 'VERIFIED' if permitted else 'INSUFFICIENT_EVIDENCE'
            reasons[key] = (why,)

        allowed = {'SALES_TRANSACTIONS': {'SALES'}, 'GENERAL_LEDGER': {'TB_ACTIVITY','TB_CLOSING','PNL','BALANCE_SHEET'}}
        family_ok = trusted and bool(records) and all(r.kind in allowed[manifest.family] for r in records)
        claim('family', manifest.family, family_ok, 'REGISTERED_SOURCE_FAMILY' if family_ok else 'SOURCE_AUTHORITY_OR_FAMILY_UNRESOLVED')
        claim('source_provider', manifest.system_id, trusted, 'SOURCE_SYSTEM_IDENTITY')
        identity_match = manifest.record_ids is not None and set(manifest.record_ids) == {r.record_id for r in records}
        bounded = bool(manifest.extraction_query and manifest.boundary == scope.population and
            manifest.extraction_start == scope.period.start and manifest.extraction_end == scope.period.end)
        monthly = bool(scope.period.start and scope.period.end and scope.period.basis == 'MONTHLY'
            and scope.period.start.day == 1 and scope.period.start.year == scope.period.end.year
            and scope.period.start.month == scope.period.end.month
            and scope.period.end.day == monthrange(scope.period.end.year,scope.period.end.month)[1])
        membership = trusted and family_ok and identity_match and bounded
        claim('population', scope.population, membership, 'EXACT_MANIFEST_MEMBERSHIP_AND_BOUNDARY' if membership else 'POPULATION_WITNESSES_INSUFFICIENT')
        if trusted and manifest.record_ids is not None and not identity_match:
            states['population'], reasons['population'] = 'MISMATCH', ('SOURCE_RECORD_IDENTITIES_DIFFER_FROM_MANIFEST',)
        claim('inclusion_exclusion', manifest.inclusion_exclusion, membership, 'RETAINED_EXTRACTION_FILTERS')
        complete = (membership and not manifest.excluded_record_ids and arithmetic.state == 'MATCH'
            and trusted_control and control_accounts_match)
        partial = membership and bool(manifest.excluded_record_ids)
        coverage = DatasetCoverage(period=scope.period, completeness='COMPLETE' if complete else 'PARTIAL' if partial else 'UNKNOWN',
            coverage_basis=manifest.boundary if complete or partial else None)
        claim('coverage', coverage.model_dump(mode='json'), complete or partial,
              'COMPLETE_IDENTITIES_BOUNDARIES_AND_CONTROL' if complete else 'EXPLICIT_PARTIAL_POPULATION' if partial else 'COMPLETE_COVERAGE_NOT_PROVEN')
        if trusted_control and (arithmetic.state == 'MISMATCH' or not control_accounts_match):
            states['coverage'], reasons['coverage'] = 'MISMATCH', ('CONTROL_RECONCILIATION_MISMATCH',)
        for key,value in (('organisational_scope', {'entity':scope.entity_id,'ledger':scope.ledger_id}),
                          ('currency',scope.currency),('unit','MONEY'),
                          ('time_basis',scope.period.basis.value)):
            claim(key, value, trusted and bounded, 'SOURCE_REPORT_CONFIGURATION')
        if not monthly and scope.period.nature == 'FLOW':
            claims['time_basis'] = DatasetAssertion()
            states['time_basis'],reasons['time_basis'] = 'INSUFFICIENT_EVIDENCE',('FULL_CALENDAR_MONTH_NOT_ESTABLISHED',)
        definition_ok = bool(trusted and mapping and mapping_authority in ('SOURCE_DATA','HUMAN_FD_JUDGEMENT','MANAGEMENT_ASSERTION')
            and chart and chart_authority == 'SOURCE_DATA' and mapping.source_policy_reference == chart.policy_reference
            and mapping.source_chart_version and mapping.revenue_accounts
            and mapping.definition == chart.definition == scope.definition
            and chart.recognition_basis == 'POSTED_ACCRUAL' and chart.revenue_basis == 'NET_OF_TAX_AND_CREDITS'
            and chart.amount_convention == 'POSITIVE_REVENUE_POSITIVE_COST'
            and set(mapping.revenue_accounts) == set(chart.revenue_accounts)
            and (mapping.definition == 'NET_REVENUE' or (mapping.definition == 'REVENUE_MINUS_DIRECT_COST'
                and chart.cost_basis == 'ATTRIBUTABLE_DIRECT_COST_BEFORE_CTS_AND_OVERHEAD'
                and mapping.direct_cost_accounts and set(mapping.direct_cost_accounts) == set(chart.direct_cost_accounts)))
            and {r.account_code for r in records} <= set((*mapping.revenue_accounts, *mapping.direct_cost_accounts)))
        definition = ({key:getattr(chart,key) for key in ('definition','recognition_basis','revenue_basis',
            'cost_basis','amount_convention','policy_reference')} if chart else None)
        claim('definition', definition, definition_ok,
              'SOURCE_SUPPORTED_EXPLICIT_ACCOUNT_MEMBERSHIP' if definition_ok else 'DEFINITION_OR_MAPPING_NOT_VERIFIED',
              (*witnesses, *mapping_refs))
        if mapping and chart and chart_authority == 'SOURCE_DATA' and mapping.definition != 'UNKNOWN' and chart.definition != 'UNKNOWN':
            if (mapping.definition != chart.definition or mapping.source_policy_reference != chart.policy_reference
                    or set(mapping.revenue_accounts) != set(chart.revenue_accounts)
                    or set(mapping.direct_cost_accounts) != set(chart.direct_cost_accounts)):
                states['definition'], reasons['definition'] = 'CONFLICTED', ('MAPPING_CONTRADICTED_BY_SOURCE_POLICY',)
        if definition_ok and mapping.definition == 'REVENUE_MINUS_DIRECT_COST' and not set(
                (*mapping.revenue_accounts,*mapping.direct_cost_accounts)) <= accounts_a:
            claims['coverage'] = DatasetAssertion()
            states['coverage'], reasons['coverage'] = 'INSUFFICIENT_EVIDENCE', ('C0_REQUIRED_ACCOUNT_OBSERVATIONS_NOT_PROVIDED',)
        relation = {'ORIGINAL':'NEW_OBSERVATION','RESTATEMENT':'RESTATEMENT','CORRECTION':'CORRECTION','SUPERSESSION':'SUPERSESSION'}.get(manifest.change_kind)
        revision_ok = trusted and bool(manifest.change_reference) and relation is not None
        roots = self.sources.same_period_roots(manifest)
        if relation == 'NEW_OBSERVATION' and len(roots) != 1:
            revision_ok = False
        if previous:
            old = previous.contract
            if (old.client_id != self.client_id or previous.manifest.scope != scope
                    or previous.manifest.system_id != manifest.system_id
                    or previous.manifest.family != manifest.family
                    or previous.manifest.report_id != manifest.report_id):
                raise ScopeError('Revision predecessor scope differs')
            if relation == 'NEW_OBSERVATION' or manifest.predecessor_version_id != old.source_version.source_id:
                revision_ok = False
            if mapping and previous.mapping and mapping != previous.mapping:
                if (mapping.mapping_id == previous.mapping.mapping_id or mapping.revision != previous.mapping.revision + 1
                        or mapping.supersedes != previous.mapping.mapping_id):
                    raise RevisionConflict('Changed mapping needs the explicit mapping predecessor and next revision')
        elif relation != 'NEW_OBSERVATION' or manifest.predecessor_version_id:
            revision_ok = False
        claim('revision_relationship', relation, revision_ok, 'SOURCE_SUPPORTED_REVISION_CHAIN' if revision_ok else 'REVISION_AUTHORITY_UNRESOLVED')
        for declaration in declarations:
            declaration = EvidenceDeclaration.from_json(declaration.to_json())
            if declaration.client_id != self.client_id:
                raise ScopeError('Foreign semantic declaration')
            key = declaration.dimension
            old = claims[key]
            claims[key] = DatasetAssertion(**old.model_dump(exclude={'declared_value','declaration_authority','declared_by','declared_at'}),
                declared_value=declaration.claim, declaration_authority=declaration.actor.source_authority,
                declared_by=declaration.actor, declared_at=declaration.recorded_at)
            if old.verified_value is not None and old.verified_value != declaration.claim:
                states[key], reasons[key] = 'CONFLICTED', ('DECLARATION_CONTRADICTED_BY_SOURCE_EVIDENCE',)
            elif old.verified_value is None:
                states[key] = 'DECLARED'
        basis = [record_version, control_version, manifest_version, mapping_version,
                 manifest.to_json(), mapping.to_json() if mapping else None,
                 chart.to_json() if chart else None, arithmetic.to_json(), [d.to_json() for d in declarations],
                 trusted,trusted_control,mapping_authority,chart_authority,sorted(roots),
                 records_meta['file_hash'],control_meta['file_hash'],meta['file_hash'],
                 mapping_meta['file_hash'] if mapping else None,chart_meta['file_hash'] if chart else None]
        encoded = json.dumps(basis, sort_keys=True, default=lambda v: v.model_dump(mode='json'), separators=(',',':'))
        import hashlib
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        if previous and digest == previous.evidence_digest:
            return previous
        revision = previous.revision + 1 if previous else 1
        cid = identity('dataset-contract-production-2.55.1', self.client_id, digest, revision)
        contract = DatasetContract(contract_id=cid, client_id=self.client_id, recorded_run_id=self.run_id,
            source_dataset=refs[0], source_version=refs[1], source_file=refs[2],
            source_file_sha256=records_meta['file_hash'], source_capture_id=records_meta['ingestion_job_id'],
            logical_dataset_key=records_meta['logical_dataset_key'], source_data_domain=records_meta['data_domain'],
            source_digest=digest, revision=revision, supersedes=previous.contract.contract_id if previous else None,
            revision_target_contract_id=previous.contract.contract_id if revision_ok and previous else None,
            observed_row_count=len(records), created_at=now(), **claims)
        return SemanticAssessment(assessment_id=identity('semantic-assessment-2.55.1',cid), contract=contract,
            states=states, reasons=reasons, reconciliation=arithmetic.to_json(), manifest=manifest, mapping=mapping, chart=chart,
            source_versions=tuple(v for v in (record_version,control_version,manifest_version,mapping_version,
                mapping.source_chart_version if mapping else None) if v),
            evidence_digest=digest, revision=revision, supersedes=previous.assessment_id if previous else None)
