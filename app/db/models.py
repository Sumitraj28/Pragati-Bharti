import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    Float,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class DocumentRole(str, enum.Enum):
    QUESTION_PAPER = "question_paper"
    ANSWER_KEY = "answer_key"
    UNKNOWN = "unknown"


class QuestionStatus(str, enum.Enum):
    EXTRACTED = "extracted"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document_groups = relationship("DocumentGroup", back_populates="owner", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class DocumentGroup(Base):
    __tablename__ = "document_groups"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="document_groups")
    documents = relationship("Document", back_populates="group")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(
        SQLEnum(DocumentStatus, name="document_status", values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    doc_role = Column(
        SQLEnum(DocumentRole, name="document_role", values_callable=lambda x: [e.value for e in x]),
        default=DocumentRole.UNKNOWN,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="documents")
    group = relationship("DocumentGroup", back_populates="documents")
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="pages")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=True)
    question_text = Column(Text, nullable=False)
    options = Column(JSONB, nullable=True)
    question_type = Column(String(50), nullable=True)
    source_pages = Column(ARRAY(Integer), nullable=True)
    confidence_score = Column(Float, nullable=True)
    status = Column(
        SQLEnum(QuestionStatus, name="question_status", values_callable=lambda x: [e.value for e in x]),
        default=QuestionStatus.EXTRACTED,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="questions")
    answers = relationship("Answer", foreign_keys="[Answer.question_id]", back_populates="question")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    raw_answer_text = Column(Text, nullable=False)
    matched = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Float, nullable=True)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    unmatched_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    question = relationship("Question", foreign_keys=[question_id], back_populates="answers")
    source_document = relationship("Document", foreign_keys=[source_document_id])
