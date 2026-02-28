"""Seed script for Memory SCM Intelligence Platform.

Populates the database with realistic semiconductor supply chain data:
- 5 clusters (tiers)
- 30+ companies across the value chain
- Company relations (supplier-customer)
- Sample alerts, news, alert rules
- Admin user
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlmodel import Session, create_engine, select

from app.models import (
    Alert,
    AlertRule,
    Cluster,
    Company,
    CompanyRelation,
    DataPoint,
    DataSource,
    NewsItem,
    User,
    UserFilter,
)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

DATABASE_URL = "sqlite:///./memory_scm.db"
engine = create_engine(DATABASE_URL)

NOW = datetime.now(timezone.utc)


def seed_clusters(session: Session) -> dict[str, int]:
    clusters = [
        Cluster(name="원자재", tier="raw_material"),
        Cluster(name="장비사", tier="equipment"),
        Cluster(name="팹", tier="fab"),
        Cluster(name="패키징", tier="packaging"),
        Cluster(name="모듈", tier="module"),
    ]
    for c in clusters:
        session.add(c)
    session.flush()
    return {c.tier: c.id for c in clusters}


def seed_companies(session: Session, cluster_map: dict[str, int]) -> dict[str, int]:
    companies_data = [
        # Raw Materials
        ("SK Materials", "SK머티리얼즈", "raw_material", "KR", "특수가스 및 반도체 소재"),
        ("Soulbrain", "솔브레인", "raw_material", "KR", "반도체 공정용 화학소재"),
        ("DNF", "디엔에프", "raw_material", "KR", "반도체 전구체 소재"),
        ("Hansol Chemical", "한솔케미칼", "raw_material", "KR", "과산화수소, CMP 슬러리"),
        ("SUMCO", "SUMCO", "raw_material", "JP", "실리콘 웨이퍼"),
        ("Shin-Etsu Chemical", "신에츠화학", "raw_material", "JP", "실리콘 웨이퍼, 포토마스크"),
        # Equipment
        ("ASML", "ASML", "equipment", "NL", "EUV/DUV 노광장비"),
        ("Applied Materials", "어플라이드머티리얼즈", "equipment", "US", "반도체 장비"),
        ("Lam Research", "램리서치", "equipment", "US", "식각/증착 장비"),
        ("Tokyo Electron", "도쿄일렉트론", "equipment", "JP", "코터/디벨로퍼, CVD"),
        ("SEMES", "세메스", "equipment", "KR", "세정/코팅 장비 (삼성 자회사)"),
        ("PSK", "피에스케이", "equipment", "KR", "애싱/식각 장비"),
        # FAB
        ("Samsung Electronics", "삼성전자", "fab", "KR", "DRAM, NAND, 파운드리"),
        ("SK hynix", "SK하이닉스", "fab", "KR", "DRAM, NAND"),
        ("Micron Technology", "마이크론", "fab", "US", "DRAM, NAND"),
        ("TSMC", "TSMC", "fab", "TW", "파운드리"),
        ("Intel", "인텔", "fab", "US", "CPU, 파운드리"),
        ("Kioxia", "키옥시아", "fab", "JP", "NAND Flash"),
        # Packaging
        ("ASE Group", "ASE그룹", "packaging", "TW", "OSAT (후공정)"),
        ("Amkor Technology", "앰코테크놀로지", "packaging", "US", "반도체 패키징/테스트"),
        ("JCET", "JCET", "packaging", "CN", "반도체 패키징"),
        ("NEPES", "네패스", "packaging", "KR", "WLP, Fan-Out 패키징"),
        ("SFA Semicon", "SFA반도체", "packaging", "KR", "메모리 패키징/테스트"),
        ("Hana Micron", "하나마이크론", "packaging", "KR", "메모리 패키징"),
        # Module
        ("Samsung SDI", "삼성SDI", "module", "KR", "배터리 모듈"),
        ("SK Nexilis", "SK넥실리스", "module", "KR", "동박 (배터리/반도체)"),
        ("LG Innotek", "LG이노텍", "module", "KR", "카메라 모듈, 기판"),
        ("Innox Advanced Materials", "이녹스첨단소재", "module", "KR", "FPCB, OLED 소재"),
        ("BH", "BH", "module", "KR", "카메라 모듈"),
        ("Daeduck Electronics", "대덕전자", "module", "KR", "반도체 기판, PCB"),
    ]

    company_map = {}
    for name, name_kr, tier, country, desc in companies_data:
        c = Company(
            name=name,
            name_kr=name_kr,
            cluster_id=cluster_map[tier],
            tier=tier,
            country=country,
            description=desc,
        )
        session.add(c)
        session.flush()
        company_map[name] = c.id
    return company_map


def seed_relations(session: Session, cm: dict[str, int]) -> None:
    relations = [
        # Raw Material → FAB
        ("SK Materials", "Samsung Electronics", "supplier", 0.95),
        ("SK Materials", "SK hynix", "supplier", 0.90),
        ("Soulbrain", "Samsung Electronics", "supplier", 0.85),
        ("Soulbrain", "SK hynix", "supplier", 0.80),
        ("DNF", "Samsung Electronics", "supplier", 0.70),
        ("Hansol Chemical", "Samsung Electronics", "supplier", 0.65),
        ("SUMCO", "Samsung Electronics", "supplier", 0.80),
        ("SUMCO", "TSMC", "supplier", 0.85),
        ("Shin-Etsu Chemical", "TSMC", "supplier", 0.90),
        ("Shin-Etsu Chemical", "Intel", "supplier", 0.75),
        # Equipment → FAB
        ("ASML", "Samsung Electronics", "supplier", 0.95),
        ("ASML", "TSMC", "supplier", 0.98),
        ("ASML", "SK hynix", "supplier", 0.85),
        ("ASML", "Intel", "supplier", 0.90),
        ("Applied Materials", "Samsung Electronics", "supplier", 0.80),
        ("Applied Materials", "TSMC", "supplier", 0.85),
        ("Lam Research", "Samsung Electronics", "supplier", 0.75),
        ("Lam Research", "SK hynix", "supplier", 0.80),
        ("Tokyo Electron", "Samsung Electronics", "supplier", 0.70),
        ("Tokyo Electron", "TSMC", "supplier", 0.75),
        ("SEMES", "Samsung Electronics", "supplier", 0.90),
        ("PSK", "Samsung Electronics", "supplier", 0.65),
        ("PSK", "SK hynix", "supplier", 0.60),
        # FAB → Packaging
        ("Samsung Electronics", "NEPES", "customer", 0.70),
        ("Samsung Electronics", "SFA Semicon", "customer", 0.80),
        ("Samsung Electronics", "Hana Micron", "customer", 0.75),
        ("SK hynix", "Amkor Technology", "customer", 0.85),
        ("SK hynix", "Hana Micron", "customer", 0.70),
        ("Micron Technology", "ASE Group", "customer", 0.80),
        ("TSMC", "ASE Group", "customer", 0.90),
        ("Kioxia", "JCET", "customer", 0.65),
        # Packaging → Module
        ("NEPES", "LG Innotek", "customer", 0.60),
        ("ASE Group", "LG Innotek", "customer", 0.70),
        ("Amkor Technology", "Daeduck Electronics", "customer", 0.55),
        ("SFA Semicon", "Samsung SDI", "customer", 0.65),
        # Partner relations
        ("Samsung Electronics", "TSMC", "partner", 0.30),
        ("SK hynix", "Micron Technology", "partner", 0.25),
    ]
    for src, tgt, rtype, strength in relations:
        session.add(CompanyRelation(
            source_id=cm[src],
            target_id=cm[tgt],
            relation_type=rtype,
            strength=strength,
        ))


def seed_alerts(session: Session, cm: dict[str, int]) -> None:
    alerts = [
        (cm["ASML"], "critical", "EUV 장비 납기 6개월 지연",
         "ASML의 High-NA EUV 장비 납기가 2026 H2로 연기. 삼성/TSMC 2nm 공정 일정에 영향 예상."),
        (cm["SK Materials"], "critical", "특수가스 공급 차질",
         "SK머티리얼즈 세종공장 정기보수 연장. NF3 가스 공급 2주간 30% 감소 예상."),
        (cm["Samsung Electronics"], "warning", "평택 P4 가동률 하락",
         "DRAM 재고 조정으로 평택 P4 팹 가동률 85%→70% 하향. Q2 출하량 영향."),
        (cm["SK hynix"], "warning", "HBM3E 수율 이슈",
         "HBM3E 12단 적층 공정 수율이 목표 대비 15%p 미달. 엔비디아 납기 리스크."),
        (cm["TSMC"], "warning", "3nm 수율 정체",
         "N3E 공정 수율 개선 속도 둔화. 애플 M4 Pro 생산에 영향 가능성."),
        (cm["Micron Technology"], "info", "일본 히로시마 팹 증설",
         "마이크론 히로시마 공장 DRAM 생산라인 증설 완료. 월 생산 15K 웨이퍼 추가."),
        (cm["Lam Research"], "info", "신규 ALD 장비 출시",
         "램리서치 차세대 ALD 장비 발표. GAA 구조 양산용, 2026 Q3 출하 예정."),
        (cm["SUMCO"], "warning", "300mm 웨이퍼 가격 인상",
         "SUMCO, 2026년 상반기 300mm 웨이퍼 가격 8% 인상 통보."),
        (cm["Kioxia"], "critical", "요카이치 팹 전력 문제",
         "키옥시아 요카이치 공장 전력 공급 불안정. 3D NAND 생산 일시 중단."),
        (cm["NEPES"], "info", "Fan-Out 패키징 수주 확대",
         "네패스, 모바일 AP용 Fan-Out 패키징 신규 수주. 2026 Q2 양산 시작."),
    ]
    for i, (cid, severity, title, desc) in enumerate(alerts):
        session.add(Alert(
            company_id=cid,
            severity=severity,
            title=title,
            description=desc,
            is_read=i > 5,
            created_at=NOW - timedelta(hours=i * 6),
        ))


def seed_news(session: Session, cm: dict[str, int]) -> None:
    news = [
        ("ASML, High-NA EUV 2호기 삼성전자 납품 완료", "Reuters",
         cm["ASML"], 2),
        ("SK하이닉스, HBM4 개발 착수…2027년 양산 목표", "한국경제",
         cm["SK hynix"], 1),
        ("삼성전자, 2nm GAA 공정 시험 생산 시작", "전자신문",
         cm["Samsung Electronics"], 3),
        ("TSMC, 일본 구마모토 2공장 건설 본격화", "Nikkei Asia",
         cm["TSMC"], 5),
        ("마이크론, 중국 시안 공장 NAND 생산 축소", "Bloomberg",
         cm["Micron Technology"], 4),
        ("SUMCO, 실리콘 웨이퍼 장기 공급 계약 체결", "日経新聞",
         cm["SUMCO"], 7),
        ("램리서치, 식각 장비 시장 점유율 1위 탈환", "SemiEngineering",
         cm["Lam Research"], 6),
        ("네패스, 차량용 반도체 패키징 라인 증설", "매일경제",
         cm["NEPES"], 8),
        ("인텔, 파운드리 사업부 분사 검토", "CNBC",
         cm["Intel"], 10),
        ("키옥시아-WD 합병 협상 재개", "日経アジア",
         cm["Kioxia"], 12),
    ]
    for title, source, cid, days_ago in news:
        session.add(NewsItem(
            title=title,
            url=f"https://example.com/news/{title[:10].replace(' ', '-')}",
            source=source,
            company_id=cid,
            published_at=NOW - timedelta(days=days_ago),
        ))


def seed_users(session: Session) -> int:
    admin = User(
        email="admin@memoryscm.com",
        hashed_password=hash_password("admin1234"),
        name="관리자",
        role="admin",
    )
    session.add(admin)
    analyst = User(
        email="analyst@memoryscm.com",
        hashed_password=hash_password("analyst1234"),
        name="분석가",
        role="analyst",
    )
    session.add(analyst)
    session.flush()
    return admin.id


def seed_alert_rules(session: Session, admin_id: int) -> None:
    rules = [
        ("Critical 알림", {"severity": "critical", "notify": True}),
        ("납기 지연 감지", {"keyword": "납기", "severity": ["critical", "warning"]}),
        ("가격 변동 감지", {"metric": "price", "change_pct": 5}),
    ]
    for name, condition in rules:
        session.add(AlertRule(
            user_id=admin_id,
            name=name,
            condition=json.dumps(condition, ensure_ascii=False),
            is_active=True,
        ))


def seed_data_sources_and_points(session: Session, cm: dict[str, int]) -> None:
    ds = DataSource(name="Market Data API", type="api", is_active=True)
    session.add(ds)
    session.flush()

    points = [
        (cm["Samsung Electronics"], "inventory_days", 45.2, "days"),
        (cm["Samsung Electronics"], "lead_time", 12.5, "weeks"),
        (cm["SK hynix"], "inventory_days", 52.1, "days"),
        (cm["SK hynix"], "lead_time", 10.3, "weeks"),
        (cm["TSMC"], "utilization", 92.5, "%"),
        (cm["Micron Technology"], "inventory_days", 68.3, "days"),
        (cm["ASML"], "backlog_months", 18.0, "months"),
        (cm["SUMCO"], "price_index", 108.5, "index"),
    ]
    for cid, metric, value, unit in points:
        session.add(DataPoint(
            source_id=ds.id,
            company_id=cid,
            metric=metric,
            value=value,
            unit=unit,
        ))


def seed_user_filters(session: Session, admin_id: int, cm: dict[str, int]) -> None:
    korean_fab_ids = [cm["Samsung Electronics"], cm["SK hynix"]]
    session.add(UserFilter(
        user_id=admin_id,
        name="한국 팹",
        company_ids=json.dumps(korean_fab_ids),
        is_default=True,
    ))
    top_equip_ids = [cm["ASML"], cm["Applied Materials"], cm["Lam Research"], cm["Tokyo Electron"]]
    session.add(UserFilter(
        user_id=admin_id,
        name="주요 장비사",
        company_ids=json.dumps(top_equip_ids),
        is_default=False,
    ))


def main() -> None:
    with Session(engine) as session:
        # Check if already seeded
        existing = session.exec(select(Company)).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        print("Seeding clusters...")
        cluster_map = seed_clusters(session)

        print("Seeding companies (30)...")
        cm = seed_companies(session, cluster_map)

        print("Seeding relations (37)...")
        seed_relations(session, cm)

        print("Seeding users...")
        admin_id = seed_users(session)

        print("Seeding alerts (10)...")
        seed_alerts(session, cm)

        print("Seeding news (10)...")
        seed_news(session, cm)

        print("Seeding alert rules (3)...")
        seed_alert_rules(session, admin_id)

        print("Seeding data sources & points (8)...")
        seed_data_sources_and_points(session, cm)

        print("Seeding user filters (2)...")
        seed_user_filters(session, admin_id, cm)

        session.commit()
        print("Seed complete!")
        print(f"  Clusters: 5")
        print(f"  Companies: {len(cm)}")
        print(f"  Relations: 37")
        print(f"  Users: 2 (admin@memoryscm.com / admin1234)")
        print(f"  Alerts: 10")
        print(f"  News: 10")
        print(f"  Alert Rules: 3")
        print(f"  Data Points: 8")
        print(f"  User Filters: 2")


if __name__ == "__main__":
    main()
