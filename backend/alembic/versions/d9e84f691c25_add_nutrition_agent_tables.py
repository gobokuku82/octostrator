"""add nutrition agent tables

Revision ID: d9e84f691c25
Revises: c8dd4d782b94
Create Date: 2025-11-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd9e84f691c25'
down_revision: Union[str, Sequence[str], None] = 'c8dd4d782b94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add nutrition agent tables."""

    # 1. nutrition_goals 테이블 생성
    op.create_table('nutrition_goals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goal_type', sa.String(length=50), nullable=True),  # weight_loss, muscle_gain, maintenance, health
        sa.Column('target_calories', sa.Integer(), nullable=True),
        sa.Column('target_protein', sa.Float(), nullable=True),
        sa.Column('target_carbs', sa.Float(), nullable=True),
        sa.Column('target_fat', sa.Float(), nullable=True),
        sa.Column('target_water', sa.Integer(), nullable=True),  # ml
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),  # active, completed, paused
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. meal_logs 테이블 확장 (기존 테이블이 있으므로 컬럼 추가)
    # 기존: user_id, date, meal_type, foods, nutrition, created_at
    # 추가할 컬럼들
    op.add_column('meal_logs', sa.Column('total_calories', sa.Float(), nullable=True))
    op.add_column('meal_logs', sa.Column('total_protein', sa.Float(), nullable=True))
    op.add_column('meal_logs', sa.Column('total_carbs', sa.Float(), nullable=True))
    op.add_column('meal_logs', sa.Column('total_fat', sa.Float(), nullable=True))
    op.add_column('meal_logs', sa.Column('meal_photo_url', sa.String(length=500), nullable=True))
    op.add_column('meal_logs', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('meal_logs', sa.Column('feedback', sa.Text(), nullable=True))
    op.add_column('meal_logs', sa.Column('quality_score', sa.Float(), nullable=True))

    # 3. food_database 테이블 생성
    op.create_table('food_database',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),  # protein, carbs, vegetables, fruits, dairy, snacks, beverages
        sa.Column('serving_size', sa.Float(), nullable=True),
        sa.Column('serving_unit', sa.String(length=20), nullable=True),  # g, ml, 개, 공기
        sa.Column('calories_per_serving', sa.Float(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        sa.Column('fiber', sa.Float(), nullable=True),
        sa.Column('sodium', sa.Float(), nullable=True),
        sa.Column('sugar', sa.Float(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('source', sa.String(length=50), nullable=True),  # user_input, korean_fdc, usda
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. daily_nutrition_summary 테이블 생성
    op.create_table('daily_nutrition_summary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_calories', sa.Float(), nullable=True),
        sa.Column('total_protein', sa.Float(), nullable=True),
        sa.Column('total_carbs', sa.Float(), nullable=True),
        sa.Column('total_fat', sa.Float(), nullable=True),
        sa.Column('water_intake', sa.Integer(), nullable=True),  # ml
        sa.Column('meal_count', sa.Integer(), nullable=True),
        sa.Column('goal_achievement_rate', sa.Float(), nullable=True),  # 0.0 ~ 1.0
        sa.Column('quality_score', sa.Float(), nullable=True),  # 0.0 ~ 1.0
        sa.Column('ai_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. nutrition_feedback 테이블 생성
    op.create_table('nutrition_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meal_log_id', sa.Integer(), nullable=True),
        sa.Column('feedback_date', sa.DateTime(), nullable=False),
        sa.Column('feedback_type', sa.String(length=50), nullable=True),  # daily_summary, meal_specific, weekly_review
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('recommendations', sa.Text(), nullable=True),  # JSON
        sa.Column('created_by', sa.String(length=100), nullable=True),  # AI_Agent, Trainer_Name
        sa.Column('sentiment', sa.String(length=20), nullable=True),  # positive, neutral, constructive
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['meal_log_id'], ['meal_logs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 인덱스 생성 (성능 최적화)
    op.create_index('idx_nutrition_goals_user_id', 'nutrition_goals', ['user_id'])
    op.create_index('idx_nutrition_goals_status', 'nutrition_goals', ['status'])
    op.create_index('idx_meal_logs_user_date', 'meal_logs', ['user_id', 'date'])
    op.create_index('idx_food_database_name', 'food_database', ['name'])
    op.create_index('idx_food_database_category', 'food_database', ['category'])
    op.create_index('idx_daily_nutrition_summary_user_date', 'daily_nutrition_summary', ['user_id', 'date'])
    op.create_index('idx_nutrition_feedback_user_id', 'nutrition_feedback', ['user_id'])


def downgrade() -> None:
    """Downgrade schema - Remove nutrition agent tables."""

    # 인덱스 삭제
    op.drop_index('idx_nutrition_feedback_user_id', 'nutrition_feedback')
    op.drop_index('idx_daily_nutrition_summary_user_date', 'daily_nutrition_summary')
    op.drop_index('idx_food_database_category', 'food_database')
    op.drop_index('idx_food_database_name', 'food_database')
    op.drop_index('idx_meal_logs_user_date', 'meal_logs')
    op.drop_index('idx_nutrition_goals_status', 'nutrition_goals')
    op.drop_index('idx_nutrition_goals_user_id', 'nutrition_goals')

    # 테이블 삭제
    op.drop_table('nutrition_feedback')
    op.drop_table('daily_nutrition_summary')
    op.drop_table('food_database')

    # meal_logs 컬럼 제거
    op.drop_column('meal_logs', 'quality_score')
    op.drop_column('meal_logs', 'feedback')
    op.drop_column('meal_logs', 'notes')
    op.drop_column('meal_logs', 'meal_photo_url')
    op.drop_column('meal_logs', 'total_fat')
    op.drop_column('meal_logs', 'total_carbs')
    op.drop_column('meal_logs', 'total_protein')
    op.drop_column('meal_logs', 'total_calories')

    op.drop_table('nutrition_goals')
