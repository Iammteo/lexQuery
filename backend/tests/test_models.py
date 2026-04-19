import uuid
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.audit_log import AuditLog


def test_tenant_model_fields():
    t = Tenant(
        id=uuid.uuid4(),
        name="Acme Legal",
        slug="acme-legal",
        plan="professional",
        data_region="eu-west-2",
    )
    assert t.name == "Acme Legal"
    assert t.slug == "acme-legal"
    assert t.plan == "professional"
    assert t.is_active is True


def test_user_role_enum_values():
    assert UserRole.VIEWER == "viewer"
    assert UserRole.EDITOR == "editor"
    assert UserRole.MATTER_ADMIN == "matter_admin"
    assert UserRole.TENANT_ADMIN == "tenant_admin"


def test_user_model_fields():
    tenant_id = uuid.uuid4()
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="sarah@acmelegal.com",
        full_name="Sarah Chen",
        role=UserRole.EDITOR,
    )
    assert u.email == "sarah@acmelegal.com"
    assert u.role == UserRole.EDITOR
    assert u.tenant_id == tenant_id
    assert u.is_active is True
    assert u.hashed_password is None


def test_workspace_model_fields():
    tenant_id = uuid.uuid4()
    w = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Acme Acquisition 2024",
        matter_number="M-2024-001",
    )
    assert w.name == "Acme Acquisition 2024"
    assert w.matter_number == "M-2024-001"
    assert w.is_active is True


def test_document_status_enum_values():
    assert DocumentStatus.PENDING == "pending"
    assert DocumentStatus.PROCESSING == "processing"
    assert DocumentStatus.INDEXED == "indexed"
    assert DocumentStatus.FAILED == "failed"


def test_document_model_fields():
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        filename="contract_v2.pdf",
        document_type=DocumentType.PDF,
        s3_key=f"{tenant_id}/{workspace_id}/contract_v2.pdf",
        status=DocumentStatus.PENDING,
    )
    assert doc.filename == "contract_v2.pdf"
    assert doc.status == DocumentStatus.PENDING
    assert doc.document_type == DocumentType.PDF
    assert doc.chunk_count is None
    assert doc.error_message is None


def test_audit_log_model_fields():
    tenant_id = uuid.uuid4()
    log = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        query_text="What are the termination clauses in the Acme contract?",
        confidence_score=0.87,
        llm_model="claude-sonnet-4-20250514",
        cited_doc_ids=["doc-1", "doc-2"],
    )
    assert log.query_text == "What are the termination clauses in the Acme contract?"
    assert log.confidence_score == 0.87
    assert len(log.cited_doc_ids) == 2


def test_audit_log_has_no_updated_at():
    """Audit logs are immutable — they must not have an updated_at field."""
    assert not hasattr(AuditLog, "updated_at"), (
        "AuditLog must not have updated_at — logs are immutable"
    )


def test_workspace_member_fields():
    member = WorkspaceMember(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        can_ingest=True,
    )
    assert member.can_ingest is True
