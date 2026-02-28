# Memory SCM Intelligence Platform - 디자인 시스템

## 1. 색상 팔레트

### Primary
- Primary: `#2563EB` (Blue 600) - 주요 액션, 링크
- Primary Hover: `#1D4ED8` (Blue 700)
- Primary Light: `#DBEAFE` (Blue 100) - 배경 강조

### Status
- Critical: `#DC2626` (Red 600) - 심각한 알림
- Warning: `#F59E0B` (Amber 500) - 경고 알림
- Success: `#16A34A` (Green 600) - 정상 상태
- Info: `#2563EB` (Blue 600) - 정보성

### Neutral
- Background: `#F8FAFC` (Slate 50)
- Surface: `#FFFFFF`
- Border: `#E2E8F0` (Slate 200)
- Text Primary: `#0F172A` (Slate 900)
- Text Secondary: `#64748B` (Slate 500)
- Text Muted: `#94A3B8` (Slate 400)

### Graph
- Node Default: `#3B82F6` (Blue 500)
- Node Alert: `#EF4444` (Red 500)
- Node Selected: `#8B5CF6` (Violet 500)
- Edge Default: `#CBD5E1` (Slate 300)
- Edge Highlight: `#2563EB` (Blue 600)
- Cluster Background: `rgba(59, 130, 246, 0.1)`

## 2. 타이포그래피

- **Font Family**: Inter (본문), JetBrains Mono (데이터/수치)
- Heading 1: 24px / 700 / 1.2
- Heading 2: 20px / 600 / 1.3
- Heading 3: 16px / 600 / 1.4
- Body: 14px / 400 / 1.5
- Caption: 12px / 400 / 1.4
- Data: 14px / 500 / JetBrains Mono

## 3. 컴포넌트

### Button
- Primary: bg-blue-600, text-white, rounded-lg, px-4 py-2
- Secondary: bg-white, border, text-slate-700, rounded-lg
- Ghost: bg-transparent, text-slate-600, hover:bg-slate-100
- Danger: bg-red-600, text-white

### Alert Banner
- Critical: bg-red-50, border-l-4 border-red-500, text-red-800
- Warning: bg-amber-50, border-l-4 border-amber-500, text-amber-800
- Info: bg-blue-50, border-l-4 border-blue-500, text-blue-800

### Side Panel
- Width: 400px
- Background: white
- Shadow: shadow-xl
- Animation: slide-in-right 200ms

### Filter Panel
- Width: 320px
- Position: overlay right
- Background: white
- Max-height: 80vh (scrollable)

### Graph Node
- Default: circle, 40px, blue fill
- Cluster: rounded-rect, dynamic size, light fill
- Alert Icon: 16px warning triangle overlay

## 4. 간격 시스템

- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px

## 5. 반응형

- Desktop: > 1280px (primary target)
- Tablet: 768px ~ 1280px (scaled layout)
- Mobile: < 768px (not supported for MVP - complex graph interaction)

## 6. 다크 모드

- MVP에서는 미지원
- 확장 시 CSS variables로 전환 가능하도록 설계
