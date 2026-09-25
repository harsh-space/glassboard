"""Canonical seed data per BUILD_SPEC.md §1."""
from datetime import date

SEED_TASKS = [
    {
        "id": 1,
        "title": "Requirements Gathering",
        "duration_days": 2,
        "description": "Gather and document functional and non-functional requirements from stakeholders.",
        "prerequisites": [],
    },
    {
        "id": 2,
        "title": "Database Schema Design",
        "duration_days": 3,
        "description": "Design the relational schema, including tables for tasks, dependencies, and suggestions.",
        "prerequisites": [1],
    },
    {
        "id": 3,
        "title": "UI Wireframes",
        "duration_days": 2,
        "description": "Create wireframes for the Kanban board and task detail views.",
        "prerequisites": [1],
    },
    {
        "id": 4,
        "title": "Backend API Development",
        "duration_days": 5,
        "description": "Build REST endpoints for tasks, dependencies, and scheduling, backed by the database schema.",
        "prerequisites": [2],
    },
    {
        "id": 5,
        "title": "Test Data Setup",
        "duration_days": 2,
        "description": "Prepare seeded and synthetic test data matching the database schema for integration testing.",
        "prerequisites": [2],
    },
    {
        "id": 6,
        "title": "Frontend Implementation",
        "duration_days": 4,
        "description": "Implement the React frontend against the wireframes and the backend API.",
        "prerequisites": [3, 4],
    },
    {
        "id": 7,
        "title": "Integration Testing",
        "duration_days": 2,
        "description": "Run integration tests against the backend API using the prepared test data.",
        "prerequisites": [4, 5],
    },
    {
        "id": 8,
        "title": "API Documentation",
        "duration_days": 1,
        "description": "Write API documentation describing the endpoints built for the backend.",
        "prerequisites": [4],
    },
    {
        "id": 9,
        "title": "Deployment Prep",
        "duration_days": 2,
        "description": "Prepare the deployment environment once the frontend and integration tests pass.",
        "prerequisites": [6, 7],
    },
    {
        "id": 10,
        "title": "Release",
        "duration_days": 1,
        "description": "Tag and release the version once documentation and deployment prep are complete.",
        "prerequisites": [8, 9],
    },
]

# Exactly 13 prerequisite edges:
# T1->T2, T1->T3, T2->T4, T2->T5, T3->T6, T4->T6, T4->T7, T5->T7, T4->T8, T6->T9, T7->T9, T8->T10, T9->T10
# (prerequisite_id, task_id)
SEED_DEPENDENCIES = [
    (1, 2),
    (1, 3),
    (2, 4),
    (2, 5),
    (3, 6),
    (4, 6),
    (4, 7),
    (5, 7),
    (4, 8),
    (6, 9),
    (7, 9),
    (8, 10),
    (9, 10),
]
