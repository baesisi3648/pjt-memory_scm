# @TASK P0-T0.4 - Add ticker column and index to companies table
# @SPEC docs/planning/04-database-design.md#companies
"""add_ticker_column_and_index_to_companies

Revision ID: d023a1016a91
Revises: 7d89b37bfab5
Create Date: 2026-03-01 16:42:49.487919

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd023a1016a91'
down_revision: Union[str, Sequence[str], None] = '7d89b37bfab5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Return True if *column_name* already exists in *table_name*.

    This helper is needed because some databases (e.g. those bootstrapped via
    SQLModel.metadata.create_all) may already contain the 'ticker' column even
    though the initial Alembic migration did not create it.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(table_name: str, index_name: str) -> bool:
    """Return True if *index_name* already exists on *table_name*."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    """Upgrade schema.

    Adds the 'ticker' column (stock ticker symbol) to the companies table and
    creates its index. This column was present in the SQLModel definition but
    was omitted from the initial Alembic migration.

    Guard clauses handle databases that were bootstrapped directly via
    SQLModel.metadata.create_all() and therefore already contain the column.
    Fresh installs (running only Alembic migrations) will receive the column
    and index here.
    """
    ticker_exists = _column_exists('companies', 'ticker')
    index_exists = _index_exists('companies', 'ix_companies_ticker')

    if not ticker_exists:
        # Fresh install path: the initial migration ran but create_all() did
        # not, so the column is genuinely absent.
        with op.batch_alter_table('companies') as batch_op:
            batch_op.add_column(
                sa.Column(
                    'ticker',
                    sqlmodel.sql.sqltypes.AutoString(length=20),
                    nullable=True,
                )
            )

    if not index_exists:
        # Create the index whether or not the column was just added.
        # batch_alter_table rebuilds the table in SQLite, which is safe here.
        with op.batch_alter_table('companies') as batch_op:
            batch_op.create_index('ix_companies_ticker', ['ticker'], unique=False)


def downgrade() -> None:
    """Downgrade schema.

    Drops the ticker index and column.  Guard clauses mirror upgrade() so that
    partial states are handled gracefully.
    """
    if _index_exists('companies', 'ix_companies_ticker'):
        with op.batch_alter_table('companies') as batch_op:
            batch_op.drop_index('ix_companies_ticker')

    if _column_exists('companies', 'ticker'):
        with op.batch_alter_table('companies') as batch_op:
            batch_op.drop_column('ticker')
