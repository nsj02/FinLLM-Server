# Docker ContainerConfig 에러 해결 방법

## 1. 기존 컨테이너 및 이미지 완전 제거
```bash
# 컨테이너 중지 및 제거
docker-compose down --remove-orphans

# 관련 컨테이너 강제 제거
docker rm -f finllm-api-server

# 관련 이미지 제거
docker rmi finllm-server_api-server finllm-server-api-server

# 사용하지 않는 이미지 정리
docker image prune -f

# 전체 시스템 정리 (옵션)
docker system prune -f
```

## 2. Docker Compose 파일 검증
```bash
# docker-compose.yml 문법 검증
docker-compose config
```

## 3. 새로 빌드 및 실행
```bash
# 캐시 없이 새로 빌드
docker-compose build --no-cache

# 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api-server
```

## 4. 만약 계속 문제가 있다면
```bash
# Docker 데몬 재시작
sudo systemctl restart docker

# 또는 서버 재부팅 후 다시 시도
sudo reboot
```

## 5. 대안: 직접 Docker 명령어 사용
```bash
# 이미지 빌드
docker build -t finllm-api .

# 컨테이너 실행
docker run -d \
  --name finllm-api-server \
  -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://alstpdusMin:Alstpdus!!@finance-db.c36egosuec87.ap-northeast-2.rds.amazonaws.com:3306/stock_data" \
  -e API_SERVER_URL="http://0.0.0.0:8000" \
  -e PYTHONUNBUFFERED=1 \
  finllm-api
```