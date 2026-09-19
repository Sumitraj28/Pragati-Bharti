"""add core models for document intelligence

Revision ID: c2c3dbc1df55
Revises: 19d872b844c4
Create Date: 2026-09-19 13:25:39.064320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c2c3dbc1df55'
down_revision: Union[str, None] = '19d872b844c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure Postgres Enum types exist
    document_status = postgresql.ENUM('pending', 'processing', 'done', 'failed', name='document_status')
    document_status.create(op.get_bind(), checkfirst=True)

    document_role = postgresql.ENUM('question_paper', 'answer_key', 'unknown', name='document_role')
    document_role.create(op.get_bind(), checkfirst=True)

    question_status = postgresql.ENUM('extracted', 'partial', 'needs_review', name='question_status')
    question_status.create(op.get_bind(), checkfirst=True)

    # Reference types without re-creating during table operations
    doc_status_type = postgresql.ENUM('pending', 'processing', 'done', 'failed', name='document_status', create_type=False)
    doc_role_type = postgresql.ENUM('question_paper', 'answer_key', 'unknown', name='document_role', create_type=False)
    question_status_type = postgresql.ENUM('extracted', 'partial', 'needs_review', name='question_status', create_type=False)

    # 2. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 3. Document Groups table
    op.create_table(
        'document_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_groups_id'), 'document_groups', ['id'], unique=False)

    # 4. Modify Documents table
    op.add_column('documents', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.add_column('documents', sa.Column('group_id', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('file_type', sa.String(length=100), nullable=False))
    op.add_column('documents', sa.Column('doc_role', doc_role_type, nullable=False, server_default='unknown'))
    op.alter_column(
        'documents',
        'status',
        existing_type=sa.VARCHAR(length=50),
        type_=doc_status_type,
        postgresql_using='status::document_status',
        existing_nullable=False,
    )
    op.create_foreign_key('fk_documents_group_id', 'documents', 'document_groups', ['group_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_documents_owner_id', 'documents', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'content_type')
    op.drop_column('documents', 'extracted_text')

    # 5. Pages table
    op.create_table(
        'pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pages_id'), 'pages', ['id'], unique=False)

    # 6. Questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('question_number', sa.Integer(), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('question_type', sa.String(length=50), nullable=True),
        sa.Column('source_pages', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('status', question_status_type, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)

    # 7. Answers table
    op.create_table(
        'answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=True),
        sa.Column('raw_answer_text', sa.Text(), nullable=False),
        sa.Column('matched', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source_document_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_answers_id'), 'answers', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_answers_id'), table_name='answers')
    op.drop_table('answers')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')
    op.drop_index(op.f('ix_pages_id'), table_name='pages')
    op.drop_table('pages')

    op.drop_constraint('fk_documents_group_id', 'documents', type_='foreignkey')
    op.drop_constraint('fk_documents_owner_id', 'documents', type_='foreignkey')
    op.alter_column(
        'documents',
        'status',
        existing_type=sa.Enum('pending', 'processing', 'done', 'failed', name='document_status'),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    op.drop_column('documents', 'doc_role')
    op.drop_column('documents', 'file_type')
    op.drop_column('documents', 'group_id')
    op.drop_column('documents', 'owner_id')
    op.add_column('documents', sa.Column('extracted_text', sa.TEXT(), nullable=True))
    op.add_column('documents', sa.Column('content_type', sa.VARCHAR(length=100), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))

    op.drop_index(op.f('ix_document_groups_id'), table_name='document_groups')
    op.drop_table('document_groups')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    document_status = postgresql.ENUM('pending', 'processing', 'done', 'failed', name='document_status')
    document_status.drop(op.get_bind(), checkfirst=True)
    document_role = postgresql.ENUM('question_paper', 'answer_key', 'unknown', name='document_role')
    document_role.drop(op.get_bind(), checkfirst=True)
    question_status = postgresql.ENUM('extracted', 'partial', 'needs_review', name='question_status')
    question_status.drop(op.get_bind(), checkfirst=True)
