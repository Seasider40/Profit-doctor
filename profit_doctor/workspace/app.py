"""Loopback operator application; no unauthenticated client-data routes."""
from contextlib import contextmanager
import secrets
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


def create_app(factory, operator, store, *, port=8765, access_code=None, reader_factory=None):
    if not isinstance(store, EvidenceStore) or not 1024 <= port <= 65535:
        raise ValueError('Controlled evidence storage and unprivileged loopback port required')
    access_code = access_code or secrets.token_urlsafe(32)
    session_token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
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
            if not secrets.compare_digest(request.cookies.get('pd_workspace', ''), session_token):
                return JSONResponse({'error': 'Operator session required'}, status_code=401)
            if request.method not in ('GET', 'HEAD') and not secrets.compare_digest(
                    request.headers.get('X-CSRF-Token', ''), csrf):
                return JSONResponse({'error': 'Request token required'}, status_code=403)
        try:
            response = await call_next(request)
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
        if len(data) > 200 or not secrets.compare_digest(data.decode('utf-8'), access_code):
            return JSONResponse({'error': 'Operator access code refused'}, status_code=401)
        response = JSONResponse({'csrf': csrf, 'actor': operator.actor, 'client_grants': sorted(operator.clients)})
        response.set_cookie('pd_workspace', session_token, httponly=True, samesite='strict', path='/')
        return response

    @app.get('/clients')
    def clients():
        with service() as owner:
            return owner.clients()

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
                'history': owner.history(client, engagement)}

    @app.post('/clients/{client}/engagements/{engagement}/receipts')
    async def receive(client: str, engagement: str, request: Request):
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > store.LIMIT:
                return JSONResponse({'error': 'Receipt exceeds 50 MiB'}, status_code=413)
            data.extend(chunk)
        with service() as owner:
            return owner.receive(client, engagement, request.headers.get('X-Filename', ''), bytes(data),
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
