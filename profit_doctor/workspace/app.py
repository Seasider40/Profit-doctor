"""Loopback operator application; no unauthenticated client-data routes."""
from contextlib import contextmanager
import secrets
from urllib.parse import unquote
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from profit_doctor.persistence import session_scope
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from .contracts import EngagementRevision, InformationRevision
from .service import WorkspaceService
from .storage import EvidenceStore
from .session import OperatorSession, SessionRefused
from .setup import SetupFields, SetupService
from .home import reviews as review_summaries


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ClientInput(Input):
    client_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    currency: str = 'GBP'


class EngagementInput(Input):
    value: EngagementRevision
    expected_revision: int = Field(ge=0, strict=True)


class InformationInput(Input):
    value: InformationRevision
    expected_revision: int = Field(ge=0, strict=True)


class RegistrationInput(Input):
    receipt_id: str
    version_id: str


class SetupInput(Input):
    draft_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    fields: SetupFields
    expected_revision: int = Field(strict=True, ge=0)
    action: str = 'SAVE'
    step: int = Field(strict=True, ge=1, le=3, default=1)


def create_app(factory, operator, store, *, port=8765, access_code=None, reader_factory=None, session_clock=None):
    if not isinstance(store, EvidenceStore) or not 1024 <= port <= 65535:
        raise ValueError('Controlled evidence storage and unprivileged loopback port required')
    access_code = access_code or secrets.token_urlsafe(32)
    operator_session = OperatorSession(clock=session_clock)
    origin = f'http://127.0.0.1:{port}'
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @contextmanager
    def service():
        with session_scope(factory) as session:
            # Reader resources belong to this request and must be closed by its host.
            if reader_factory:
                with reader_factory(session) as reader:
                    yield WorkspaceService(session, operator, store, reader=reader)
            else:
                yield WorkspaceService(session, operator, store)

    def key(request):
        return request.headers.get('Idempotency-Key', '')

    @app.middleware('http')
    async def boundary(request, call_next):
        if request.client is None or request.client.host not in ('127.0.0.1', '::1', 'testclient'):
            return JSONResponse({'error': 'Loopback access only'}, status_code=403)
        if request.headers.get('host') != f'127.0.0.1:{port}':
            return JSONResponse({'error': 'Unexpected local host'}, status_code=403)
        if request.method not in ('GET', 'HEAD') and request.headers.get('origin') != origin:
            return JSONResponse({'error': 'Origin validation failed'}, status_code=403)
        if request.url.path not in ('/', '/session', '/ui.js', '/ui.css'):
            try:
                request.state.operator_session = operator_session.authenticate(
                    request.cookies.get('pd_workspace', ''),
                    csrf=request.headers.get('X-CSRF-Token', '') if request.method not in ('GET', 'HEAD') else None,
                    touch=request.url.path not in ('/workspace/session', '/workspace/session/renew', '/workspace/session/end'))
            except SessionRefused:
                return JSONResponse({'error': 'Operator session required'}, status_code=401)
            except PermissionError:
                return JSONResponse({'error': 'Request token required'}, status_code=403)
        try:
            response = await call_next(request)
        except SessionRefused:
            response = JSONResponse({'error': 'Operator session required'}, status_code=401)
        except (PermissionError, ScopeError):
            response = JSONResponse({'error': 'Object unavailable in authorised scope'}, status_code=403)
        except (RevisionConflict, IntegrityError):
            response = JSONResponse({'error': 'Revision or relationship conflict; refresh before changing'}, status_code=409)
        except (ValueError, FileNotFoundError):
            response = JSONResponse({'error': 'Invalid request or evidence integrity failure'}, status_code=400)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; object-src 'none'"
        return response

    @app.get('/')
    def index():
        return HTMLResponse(Path(__file__).with_name('index.html').read_text(encoding='utf-8'))

    @app.get('/ui.js')
    def javascript():
        return Response(Path(__file__).with_name('ui.js').read_text(encoding='utf-8'), media_type='text/javascript')

    @app.get('/ui.css')
    def stylesheet():
        return Response(Path(__file__).with_name('ui.css').read_text(encoding='utf-8'), media_type='text/css')

    @app.post('/session')
    async def login(request: Request):
        data = await request.body()
        if len(data) > 200 or not secrets.compare_digest(data, access_code.encode()):
            return JSONResponse({'error': 'Operator access code refused'}, status_code=401)
        binding = operator_session.login()
        response = JSONResponse(operator_session.metadata(binding) | {'actor': operator.actor, 'client_grants': sorted(operator.clients)})
        response.set_cookie('pd_workspace', binding.token, httponly=True, samesite='strict', path='/')
        return response

    @app.get('/workspace/session')
    def resume_session(request: Request):
        return operator_session.metadata(request.state.operator_session) | {'actor': operator.actor, 'client_grants': sorted(operator.clients)}

    @app.post('/workspace/session/renew')
    def renew_session(request: Request):
        return operator_session.metadata(request.state.operator_session, renew=True)

    @app.post('/workspace/session/end')
    def end_session(request: Request):
        operator_session.end(request.state.operator_session)
        response = JSONResponse({'signed_out': True})
        response.delete_cookie('pd_workspace', path='/', httponly=True, samesite='strict')
        return response

    @app.get('/clients/{client}/setup-drafts')
    def setup_drafts(client: str, offset: int = 0, limit: int = 50):
        with service() as owner:
            return SetupService(owner).list(client, offset=offset, limit=limit)

    @app.get('/clients/{client}/setup-drafts/{draft}')
    def setup_draft(client: str, draft: str):
        with service() as owner:
            return SetupService(owner).get(client, draft).model_dump(mode='json')

    @app.get('/clients/{client}/setup-drafts/{draft}/history')
    def setup_history(client: str, draft: str):
        with service() as owner:
            return SetupService(owner).history(client, draft)

    @app.post('/clients/{client}/setup-drafts')
    def save_setup(client: str, data: SetupInput, request: Request):
        with service() as owner:
            return SetupService(owner).save(client, data.draft_id, data.fields,
                expected_revision=data.expected_revision, key=key(request), action=data.action, step=data.step).model_dump(mode='json')

    @app.get('/clients')
    def clients():
        with service() as owner:
            return owner.clients()

    @app.get('/workspace/home')
    def home(offset: int = 0, limit: int = 50):
        with service() as owner:
            return {'clients': owner.clients(), 'reviews': review_summaries(owner, offset=offset, limit=limit)}

    @app.post('/clients')
    def create_client(data: ClientInput):
        with service() as owner:
            owner.create_client(data.client_id, data.name, data.currency)
        return {'created': data.client_id}

    @app.get('/clients/{client}/engagements')
    def engagements(client: str):
        with service() as owner:
            return owner.engagements(client)

    @app.post('/clients/{client}/engagements')
    def save_engagement(client: str, data: EngagementInput, request: Request):
        if client != data.value.client_id:
            raise ScopeError('Route/client mismatch')
        with service() as owner:
            return owner.save_engagement(data.value, expected_revision=data.expected_revision, key=key(request)).model_dump(mode='json')

    @app.get('/clients/{client}/engagements/{engagement}')
    def workspace(client: str, engagement: str):
        with service() as owner:
            return {'engagement': owner.engagement(client, engagement).model_dump(mode='json'),
                'inventory': owner.inventory(client, engagement), 'requests': owner.requests(client, engagement),
                'history': owner.history(client, engagement),
                'setup_history': SetupService(owner).review_history(client, engagement)}

    @app.post('/clients/{client}/engagements/{engagement}/receipts')
    async def receive(client: str, engagement: str, request: Request):
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > store.LIMIT:
                return JSONResponse({'error': 'Receipt exceeds 50 MiB'}, status_code=413)
            data.extend(chunk)
        with service() as owner:
            encoded = request.headers.get('X-Filename-Encoded')
            filename = unquote(encoded, encoding='utf-8', errors='strict') if encoded is not None else request.headers.get('X-Filename', '')
            return owner.receive(client, engagement, filename, bytes(data),
                role=request.headers.get('X-Source-Role', 'UNSPECIFIED'),
                predecessor=request.headers.get('X-Predecessor'), key=key(request)).model_dump(mode='json')

    @app.get('/clients/{client}/receipts/{receipt}')
    def original(client: str, receipt: str):
        with service() as owner:
            value = owner.receipt(client, receipt)
            owner.engagement(client, value.engagement_id)
            data = store.read(value.sha256, value.byte_count)
        # Never render untrusted uploaded HTML/scripts in the application origin.
        return Response(data, media_type='application/octet-stream', headers={'Content-Disposition': 'attachment'})

    @app.post('/clients/{client}/engagements/{engagement}/registration')
    def registration(client: str, engagement: str, data: RegistrationInput, request: Request):
        with service() as owner:
            return owner.associate_registration(client, engagement, data.receipt_id, data.version_id, key=key(request))

    @app.post('/clients/{client}/engagements/{engagement}/requests')
    def information(client: str, engagement: str, data: InformationInput, request: Request):
        if (client, engagement) != (data.value.client_id, data.value.engagement_id):
            raise ScopeError('Route/request mismatch')
        with service() as owner:
            return owner.save_information(data.value, expected_revision=data.expected_revision, key=key(request)).model_dump(mode='json')

    @app.get('/clients/{client}/engagements/{engagement}/readiness')
    def readiness(client: str, engagement: str, historical: bool | None = None):
        with service() as owner:
            return owner.readiness(client, engagement, historical=historical)

    @app.get('/clients/{client}/engagements/{engagement}/coverage')
    def coverage(client: str, engagement: str):
        with service() as owner:
            return owner.coverage(client, engagement)

    return app
