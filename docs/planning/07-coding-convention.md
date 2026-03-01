# Memory SCM Intelligence Platform - 코딩 컨벤션

## 1. 파일 구조

```
memory-scm/
├── frontend/
│   ├── src/
│   │   ├── components/       # 재사용 UI 컴포넌트
│   │   │   ├── ui/           # 기본 UI (Button, Input 등)
│   │   │   └── graph/        # 그래프 관련 컴포넌트
│   │   ├── pages/            # 라우트별 페이지
│   │   ├── hooks/            # 커스텀 훅
│   │   ├── services/         # API 호출 레이어
│   │   ├── stores/           # 상태 관리
│   │   ├── types/            # TypeScript 타입 정의
│   │   └── utils/            # 유틸리티 함수
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/              # API 엔드포인트 (라우터)
│   │   ├── models/           # SQLModel 모델
│   │   ├── services/         # 비즈니스 로직
│   │   ├── schemas/          # Pydantic 스키마
│   │   ├── core/             # 설정, 보안, DB 연결
│   │   └── main.py           # FastAPI 앱 진입점
│   ├── migrations/           # Alembic 마이그레이션
│   ├── tests/
│   ├── alembic.ini
│   └── pyproject.toml
├── docs/
│   └── planning/             # 기획 문서
└── README.md
```

## 2. 네이밍 규칙

### Frontend (TypeScript/React)
- **변수/함수**: camelCase (`getCompanyData`, `isLoading`)
- **컴포넌트**: PascalCase (`ValueChainGraph`, `AlertBanner`)
- **상수**: UPPER_SNAKE_CASE (`MAX_NODES`, `API_BASE_URL`)
- **타입/인터페이스**: PascalCase (`Company`, `AlertRule`)
- **파일**: 컴포넌트는 PascalCase (`ValueChainGraph.tsx`), 나머지는 camelCase

### Backend (Python)
- **변수/함수**: snake_case (`get_company_data`, `is_active`)
- **클래스**: PascalCase (`CompanyService`, `AlertEngine`)
- **상수**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DB_URL`)
- **파일/모듈**: snake_case (`company_service.py`)

## 3. Lint/Formatter

### Frontend
- **ESLint**: @typescript-eslint/recommended
- **Prettier**: 2 spaces, single quotes, trailing comma
- **설정**: `.eslintrc.json`, `.prettierrc`

### Backend
- **Ruff**: Python linter + formatter (replaces black, isort, flake8)
- **설정**: `pyproject.toml` [tool.ruff]

## 4. Git 커밋 메시지

Conventional Commits:
```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 변경
style: 코드 포맷팅 (동작 변화 없음)
refactor: 리팩토링
test: 테스트 추가/수정
chore: 빌드, 설정 변경
```

예시:
```
feat: add value chain graph visualization with Cytoscape.js
fix: resolve alert banner not showing critical alerts
docs: update PRD with revised MVP scope
```

## 5. 브랜치 전략

```
main          ← 배포 가능 상태
  └── develop ← 개발 통합
       ├── feat/graph-visualization
       ├── feat/alert-engine
       └── fix/node-rendering-performance
```

## 6. API 컨벤션

- RESTful 설계
- URL: `/api/v1/{resource}` (복수형)
- 응답: JSON, snake_case 키
- 에러: `{ "detail": "message" }` 형태
- 인증: `Authorization: Bearer {token}`
