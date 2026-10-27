"""
Pytest configuration and shared fixtures.
Uses a temporary SQLite database for test isolation.
"""

import sys
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is on path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.database import Base, get_db
from backend.main import app
from backend.services.detector import detector


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Create a temp database path."""
    return tmp_path_factory.mktemp("data") / "test.db"


@pytest.fixture(scope="session")
def test_engine(test_db_path):
    """Create test database engine."""
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Provide a clean database session for each test."""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(test_engine):
    """Provide a test client with overridden database dependency."""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Ensure model is loaded
    if not detector.is_trained:
        detector.load()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_csv_content():
    """Generate a valid sample CSV as bytes."""
    lines = [
        "timestamp,source_ip,dest_ip,protocol,flow_duration,total_fwd_packets,total_bwd_packets,"
        "total_length_of_fwd_packets,total_length_of_bwd_packets,fwd_packet_length_mean,"
        "bwd_packet_length_mean,flow_bytes_per_s,flow_packets_per_s,fwd_iat_mean,bwd_iat_mean,"
        "flow_iat_mean,active_mean,idle_mean,syn_flag_count,ack_flag_count,psh_flag_count,"
        "rst_flag_count,fin_flag_count,label"
    ]

    # Add 30 normal records
    for i in range(30):
        lines.append(
            f"2024-06-15 08:{i:02d}:00,192.168.1.10,10.0.1.5,TCP,"
            f"{200000+i*1000},{5+i%10},{4+i%8},{5000+i*100},{4000+i*80},"
            f"{400+i*10},{300+i*8},{50000+i*500},{100+i*5},"
            f"{10000+i*100},{10000+i*100},{8000+i*80},{2000+i*50},{50000+i*200},"
            f"1,{2+i%3},1,0,1,BENIGN"
        )

    # Add 10 anomalous records
    for i in range(10):
        lines.append(
            f"2024-06-15 09:{i:02d}:00,10.0.5.{100+i},192.168.1.10,TCP,"
            f"{50+i},{1},{0},{60},{0},"
            f"{60},{0},{5000000},{50000},"
            f"{1},{0},{1},{0},{10},"
            f"{5+i},0,0,{i%3},0,PortScan"
        )

    return '\n'.join(lines).encode('utf-8')


@pytest.fixture
def empty_csv_content():
    """Empty CSV file."""
    return b""


@pytest.fixture
def headers_only_csv():
    """CSV with headers but no data."""
    return b"col1,col2,col3\n"


@pytest.fixture
def malformed_csv():
    """Malformed CSV content."""
    return b"col1,col2\nval1,val2,extra\nval3\n"


@pytest.fixture
def insufficient_features_csv():
    """CSV with too few supported features."""
    return b"timestamp,random_col1,random_col2\n2024-01-01,1,2\n2024-01-02,3,4\n"
