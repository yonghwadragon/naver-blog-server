# Naver Blog Automation Cloud Server

클라우드 기반 네이버 블로그 자동 포스팅 서버입니다. FastAPI + Celery + Redis 아키텍처를 사용하여 확장 가능하고 안정적인 블로그 자동화 서비스를 제공합니다.

## 아키텍처

- **FastAPI**: REST API 서버
- **Celery**: 백그라운드 작업 큐
- **Redis**: 메시지 브로커 및 결과 저장소
- **Selenium**: 네이버 블로그 자동화
- **Docker**: 컨테이너화된 배포

## 로컬 개발 설정

### 1. 필수 조건

- Docker & Docker Compose
- Python 3.11+ (로컬 개발용)

### 2. 환경 설정

```bash
# 환경 변수 파일 복사
cp .env.example .env

# 필요한 경우 환경 변수 수정
vim .env
```

### 3. Docker로 실행

```bash
# 모든 서비스 시작 (Redis, FastAPI, Celery Worker, Flower)
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build
```

### 4. 서비스 확인

- **FastAPI 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Flower 모니터링**: http://localhost:5555
- **헬스 체크**: http://localhost:8000/health

## API 엔드포인트

### POST /api/blog/post
새 블로그 포스팅 작업을 시작합니다.

**요청 본문:**
```json
{
  "postData": {
    "title": "블로그 제목",
    "content": "블로그 내용",
    "category": "카테고리 (선택사항)",
    "tags": "태그 (선택사항)"
  },
  "naverAccount": {
    "id": "네이버 아이디",
    "password": "네이버 비밀번호"
  }
}
```

**응답:**
```json
{
  "task_id": "uuid",
  "status": "pending",
  "message": "블로그 포스팅 작업이 시작되었습니다."
}
```

### GET /api/blog/task/{task_id}
작업 상태를 조회합니다.

**응답:**
```json
{
  "task_id": "uuid",
  "status": "completed|pending|in_progress|failed",
  "result": {},
  "error": null,
  "progress": 100
}
```

### DELETE /api/blog/task/{task_id}
실행 중인 작업을 취소합니다.

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `LOG_LEVEL` | 로그 레벨 | `info` |
| `PORT` | 서버 포트 | `8000` |
| `CORS_ORIGINS` | CORS 허용 도메인 | localhost:3000,navely.vercel.app |

## 프로덕션 배포

### AWS/GCP 배포 준비

1. **Docker 이미지 빌드**:
```bash
docker build -t naver-blog-server .
```

2. **컨테이너 레지스트리에 푸시**:
```bash
# AWS ECR 예시
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.region.amazonaws.com
docker tag naver-blog-server:latest $AWS_ACCOUNT_ID.dkr.ecr.region.amazonaws.com/naver-blog-server:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.region.amazonaws.com/naver-blog-server:latest
```

3. **클라우드 배포**:
   - AWS ECS/Fargate
   - Google Cloud Run
   - Azure Container Instances

### 환경별 설정

- **개발**: `docker-compose.yml`
- **스테이징**: 별도 Redis 클러스터, 스케일링된 워커
- **프로덕션**: 관리형 Redis, 로드 밸런서, 모니터링

## 모니터링

### Flower 대시보드
- 실시간 작업 모니터링
- 워커 상태 확인
- 작업 큐 상태 확인

### 로그 확인
```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f web
docker-compose logs -f worker
```

### 헬스 체크
```bash
curl http://localhost:8000/health
```

## 개발 가이드

### 로컬 Python 개발

```bash
# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Redis 시작 (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# FastAPI 서버 시작
uvicorn main:app --reload

# Celery 워커 시작 (별도 터미널)
celery -A celery_app worker --loglevel=info
```

### 코드 구조

```
naver-blog-server/
├── main.py              # FastAPI 애플리케이션
├── celery_app.py        # Celery 설정 및 작업
├── naver_blog_automation.py  # 블로그 자동화 로직
├── requirements.txt     # Python 의존성
├── Dockerfile          # Docker 이미지 정의
├── docker-compose.yml  # 로컬 개발 환경
└── README.md           # 문서
```

## 보안 고려사항

1. **비밀번호 보호**: 네이버 계정 정보는 메모리에서만 처리
2. **네트워크 보안**: VPC 내부 통신, HTTPS 사용
3. **로그 보안**: 민감한 정보 로깅 방지
4. **접근 제어**: API 키 또는 JWT 토큰 인증 (향후 구현)

## 문제 해결

### 일반적인 문제

1. **Chrome 드라이버 오류**:
   - Docker 컨테이너 내에서 headless 모드로 실행
   - Chrome 및 ChromeDriver 버전 확인

2. **Redis 연결 오류**:
   - Redis 서비스 상태 확인
   - 네트워크 연결 확인

3. **메모리 부족**:
   - Celery 워커 concurrency 조정
   - 컨테이너 리소스 제한 확인

### 로그 레벨 조정

```bash
# 개발 시 디버그 로그
export LOG_LEVEL=debug

# 프로덕션 시 에러만
export LOG_LEVEL=error
```

## 기여하기

1. Feature 브랜치 생성
2. 변경사항 커밋
3. 테스트 실행
4. Pull Request 생성

## 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.