pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        // ── Image names ───────────────────────────────────────────────────────
        BACKEND_IMAGE   = 'fazri-analyzer-backend'
        AUTH_IMAGE      = 'fazri-analyzer-auth'
        DEEPFACE_IMAGE  = 'fazri-deepface-server'
        GO2RTC_IMAGE    = 'fazri-go2rtc'
        NETWORK_NAME    = 'backend_fazri-network'
        DOCKER_BUILDKIT = '1'

        // ── Backend credentials ───────────────────────────────────────────────
        POSTGRES_SERVER   = credentials('fazri-postgres-server')
        POSTGRES_USER     = credentials('fazri-postgres-user')
        POSTGRES_PASSWORD = credentials('fazri-postgres-password')
        POSTGRES_DB       = credentials('fazri-postgres-db')
        POSTGRES_PORT     = credentials('fazri-postgres-port')
        NEO4J_URI         = credentials('fazri-neo4j-uri')
        NEO4J_USER        = credentials('fazri-neo4j-user')
        NEO4J_PASSWORD    = credentials('fazri-neo4j-password')
        REDIS_HOST        = credentials('fazri-redis-host')
        REDIS_PORT        = credentials('fazri-redis-port')
        SECRET_KEY        = credentials('fazri-secret-key')
        VERTEX_PROJECT_ID = credentials('fazri-vertex-project-id')
        VERTEX_LOCATION   = credentials('fazri-vertex-location')
        GITLAB_URL        = credentials('fazri-gitlab-url')
        GITLAB_TOKEN      = credentials('fazri-gitlab-token')
        GITLAB_PROJECT_ID = credentials('fazri-gitlab-project-id')
        AUTH_SERVICE_URL  = credentials('fazri-auth-service-url')
        SENTRY_DSN        = credentials('fazri-sentry-backend-dsn')
        SENTRY_AUTH_TOKEN = credentials('fazri-sentry-auth-token')

        // ── DeepFace credentials ──────────────────────────────────────────────
        DEEPFACE_SERVER_URL     = credentials('fazri-deepface-server-url')
        DEEPFACE_WEBHOOK_SECRET = credentials('fazri-deepface-webhook-secret')
        DEEPFACE_POSTGRES_URI   = credentials('fazri-deepface-postgres-uri')
        DEEPFACE_SENTRY_DSN     = credentials('fazri-deepface-sentry-dsn')
        AUTH_SENTRY_DSN         = credentials('fazri-auth-sentry-dsn')

        // ── Auth service credentials ──────────────────────────────────────────
        AUTH_DATABASE_URL    = credentials('fazri-auth-database-url')
        BETTER_AUTH_SECRET   = credentials('fazri-better-auth-secret')
        AUTH_TRUSTED_ORIGINS = credentials('fazri-auth-trusted-origins')
        AUTH_COOKIE_DOMAIN   = credentials('fazri-cookie-domain')

        // ── NPM (Nginx Proxy Manager) ─────────────────────────────────────────
        NPM_API_URL          = credentials('fazri-npm-api-url')
        NPM_EMAIL            = credentials('fazri-npm-email')
        NPM_PASSWORD         = credentials('fazri-npm-password')

        // ── Multi-tenant domain routing ───────────────────────────────────────
        FAZRI_BASE_DOMAIN    = credentials('fazri-base-domain')
        FAZRI_SERVER_IP      = credentials('fazri-server-ip')

        // ── Notification credentials ──────────────────────────────────────────
        DISCORD_WEBHOOK_URL  = credentials('fazri-discord-webhook-url')

        // ── Hikvision RFID ────────────────────────────────────────────────────
        HIKVISION_ENABLED       = credentials('fazri-hikvision-enabled')
        HIKVISION_BASE_URL      = credentials('fazri-hikvision-base-url')
        HIKVISION_USERNAME      = credentials('fazri-hikvision-username')
        HIKVISION_PASSWORD      = credentials('fazri-hikvision-password')
        HIKVISION_POLL_INTERVAL = credentials('fazri-hikvision-poll-interval')
        HIKVISION_DOOR_ZONE_MAP = credentials('fazri-hikvision-door-zone-map')

        // ── Aruba WiFi ────────────────────────────────────────────────────────
        ARUBA_ENABLED           = credentials('fazri-aruba-enabled')
        ARUBA_BASE_URL          = credentials('fazri-aruba-base-url')
        ARUBA_USERNAME          = credentials('fazri-aruba-username')
        ARUBA_PASSWORD          = credentials('fazri-aruba-password')
        ARUBA_POLL_INTERVAL     = credentials('fazri-aruba-poll-interval')
        ARUBA_AP_ZONE_MAP       = credentials('fazri-aruba-ap-zone-map')

        // ── Simulators (reuse existing DB/Redis credentials) ──────────────────
        // These feed the MovementCoordinator inside the simulator containers.
        SIM_POSTGRES_SERVER   = credentials('fazri-postgres-server')
        SIM_POSTGRES_USER     = credentials('fazri-postgres-user')
        SIM_POSTGRES_PASSWORD = credentials('fazri-postgres-password')
        SIM_POSTGRES_DB       = credentials('fazri-postgres-db')
        SIM_REDIS_HOST        = credentials('fazri-redis-host')
        SIM_REDIS_PORT        = credentials('fazri-redis-port')
        SIM_NUM_ENTITIES      = '10'
    }

    stages {

        // ─────────────────────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo "Checking out ${env.GIT_BRANCH}..."
                checkout scm
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Environment Check') {
            steps {
                sh '''
                    docker --version
                    docker compose version
                    node --version || true
                '''
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Set Environment') {
            steps {
                script {
                    if (env.BRANCH_NAME == 'master') {
                        env.DEPLOY_ENV          = 'production'
                        env.BACKEND_CONTAINER   = 'fazri-api'
                        env.AUTH_CONTAINER      = 'fazri-auth'
                        env.DEEPFACE_CONTAINER  = 'deepface-server'
                        env.BACKEND_PORT        = '8000'
                        env.AUTH_PORT           = '4002'
                    } else {
                        env.DEPLOY_ENV          = 'staging'
                        env.BACKEND_CONTAINER   = 'fazri-api-staging'
                        env.AUTH_CONTAINER      = 'fazri-auth-staging'
                        env.DEEPFACE_CONTAINER  = 'deepface-server-staging'
                        env.GO2RTC_CONTAINER    = 'go2rtc-staging'
                        env.BACKEND_PORT        = '8001'
                        env.AUTH_PORT           = '4003'
                    }
                    env.SANITIZED_BRANCH = env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '-').toLowerCase()
                    def shortSha         = env.GIT_COMMIT?.take(7) ?: 'unknown'
                    env.IMAGE_TAG        = "${env.SANITIZED_BRANCH}-${shortSha}"

                    echo 'Branch:            ' + env.BRANCH_NAME
                    echo 'Deploy target:     ' + env.DEPLOY_ENV
                    echo 'Image tag:         ' + env.IMAGE_TAG
                    echo 'Backend container: ' + env.BACKEND_CONTAINER + ' (' + env.BACKEND_PORT + ')'
                    echo 'Auth container:    ' + env.AUTH_CONTAINER    + ' (' + env.AUTH_PORT    + ')'
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Detect Changes') {
            steps {
                script {
                    def changedFiles = sh(
                        script: "git rev-parse HEAD~1 > /dev/null 2>&1 && git diff --name-only HEAD~1 HEAD || echo 'all'",
                        returnStdout: true
                    ).trim()

                    def isFirstRun = changedFiles == 'all'

                    env.BUILD_BACKEND  = (changedFiles.contains('apps/api/')          ||
                                          changedFiles.contains('Jenkinsfile')        ||
                                          isFirstRun) ? 'true' : 'false'

                    env.BUILD_AUTH     = (changedFiles.contains('apps/auth/')         ||
                                          changedFiles.contains('packages/')          ||
                                          changedFiles.contains('Jenkinsfile')        ||
                                          isFirstRun) ? 'true' : 'false'

                    env.BUILD_DEEPFACE = (changedFiles.contains('apps/deepface/')     ||
                                          changedFiles.contains('Jenkinsfile')        ||
                                          isFirstRun) ? 'true' : 'false'

                    env.BUILD_GO2RTC   = (changedFiles.contains('mediamtx/')          ||
                                          changedFiles.contains('Jenkinsfile')        ||
                                          isFirstRun) ? 'true' : 'false'

                    // Use concatenation instead of GString interpolation to avoid
                    // Jenkins masking these values when a credential shares the same string.
                    echo 'Changed files:\n' + changedFiles
                    echo 'Build backend:  ' + env.BUILD_BACKEND
                    echo 'Build auth:     ' + env.BUILD_AUTH
                    echo 'Build deepface: ' + env.BUILD_DEEPFACE
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Build both images while the live containers continue serving traffic.
        // ─────────────────────────────────────────────────────────────────────
        stage('Build Images') {
            parallel {

                stage('Build Backend Image') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        echo "Building backend image (live container still up)..."
                        sh '''
                            docker build -f apps/api/Dockerfile --target production \
                                -t ${BACKEND_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${BACKEND_IMAGE}:latest" || echo "") \
                                apps/api/
                        '''
                    }
                }

                stage('Build Auth Image') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        echo "Building auth service image (live container still up)..."
                        sh '''
                            docker build -f apps/auth/Dockerfile \
                                -t ${AUTH_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${AUTH_IMAGE}:latest" || echo "") \
                                .
                        '''
                    }
                }

                stage('Build DeepFace Image') {
                    when { expression { env.BUILD_DEEPFACE == 'true' } }
                    steps {
                        echo "Building DeepFace server image (live container still up)..."
                        sh '''
                            docker build -f apps/deepface/Dockerfile \
                                -t ${DEEPFACE_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${DEEPFACE_IMAGE}:latest" || echo "") \
                                apps/deepface/
                        '''
                    }
                }

                stage('Build go2rtc Image') {
                    when { expression { env.BUILD_GO2RTC == 'true' && env.BRANCH_NAME != 'master' } }
                    steps {
                        echo "Building go2rtc relay image..."
                        sh '''
                            docker build -f mediamtx/Dockerfile \
                                -t ${GO2RTC_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${GO2RTC_IMAGE}:latest" || echo "") \
                                mediamtx/
                        '''
                    }
                }

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Deploy and health-check each service in its own parallel branch.
        // If backend fails, auth still deploys and health-checks, and vice versa.
        // ─────────────────────────────────────────────────────────────────────
        stage('Deploy') {
            parallel {

                stage('Backend') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        sh '''
                            echo "Removing existing backend container..."
                            docker rm -f ${BACKEND_CONTAINER} 2>/dev/null || true
                        '''
                        withCredentials([file(credentialsId: 'fazri-gcp-service-account', variable: 'GCP_SA_FILE')]) {
                            sh '''
                                echo "Starting backend container..."
                                docker run -d \
                                    --name ${BACKEND_CONTAINER} \
                                    --restart unless-stopped \
                                    --network ${NETWORK_NAME} \
                                    -p ${BACKEND_PORT}:8000 \
                                    -e POSTGRES_SERVER="${POSTGRES_SERVER}" \
                                    -e POSTGRES_USER="${POSTGRES_USER}" \
                                    -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
                                    -e POSTGRES_DB="${POSTGRES_DB}" \
                                    -e POSTGRES_PORT="${POSTGRES_PORT}" \
                                    -e NEO4J_URI="${NEO4J_URI}" \
                                    -e NEO4J_USER="${NEO4J_USER}" \
                                    -e NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
                                    -e REDIS_HOST="${REDIS_HOST}" \
                                    -e REDIS_PORT="${REDIS_PORT}" \
                                    -e SECRET_KEY="${SECRET_KEY}" \
                                    -e USE_VERTEX_AI=true \
                                    -e VERTEX_PROJECT_ID="${VERTEX_PROJECT_ID}" \
                                    -e VERTEX_LOCATION="${VERTEX_LOCATION}" \
                                    -e CHATBOT_MODEL="gemini-2.5-flash" \
                                    -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json \
                                    -e GITLAB_URL="${GITLAB_URL}" \
                                    -e GITLAB_TOKEN="${GITLAB_TOKEN}" \
                                    -e GITLAB_PROJECT_ID="${GITLAB_PROJECT_ID}" \
                                    -e AUTH_SERVICE_URL="${AUTH_SERVICE_URL}" \
                                    -e AUTH_DATABASE_URL="${AUTH_DATABASE_URL}" \
                                    -e SENTRY_DSN="${SENTRY_DSN}" \
                                    -e SENTRY_ENVIRONMENT=${DEPLOY_ENV} \
                                    -e SENTRY_TRACES_SAMPLE_RATE=0.1 \
                                    -e SENTRY_ENABLED=true \
                                    -e DEEPFACE_SERVER_URL="${DEEPFACE_SERVER_URL}" \
                                    -e DEEPFACE_WEBHOOK_SECRET="${DEEPFACE_WEBHOOK_SECRET}" \
                                    -e DEEPFACE_CONFIDENCE_THRESHOLD="0.40" \
                                    -e DEEPFACE_LOW_CONFIDENCE_DISTANCE="0.35" \
                                    -e DEEPFACE_IMPOSSIBLE_TRAVEL_MINUTES="5" \
                                    -e DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS="300" \
                                    -e DEEPFACE_POSTGRES_URI="${DEEPFACE_POSTGRES_URI}" \
                                    -e DEEPFACE_ENABLED=true \
                                    -e DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL}" \
                                    -e GO2RTC_API_URL="http://${GO2RTC_CONTAINER}:1984" \
                                    -e GO2RTC_RTSP_URL="rtsp://${GO2RTC_CONTAINER}:8554" \
                                    -e GO2RTC_ENABLED=true \
                                    -e HIKVISION_ENABLED="${HIKVISION_ENABLED}" \
                                    -e HIKVISION_BASE_URL="${HIKVISION_BASE_URL}" \
                                    -e HIKVISION_USERNAME="${HIKVISION_USERNAME}" \
                                    -e HIKVISION_PASSWORD="${HIKVISION_PASSWORD}" \
                                    -e HIKVISION_POLL_INTERVAL_SECONDS="${HIKVISION_POLL_INTERVAL}" \
                                    -e HIKVISION_DOOR_ZONE_MAP="${HIKVISION_DOOR_ZONE_MAP}" \
                                    -e ARUBA_ENABLED="${ARUBA_ENABLED}" \
                                    -e ARUBA_BASE_URL="${ARUBA_BASE_URL}" \
                                    -e ARUBA_USERNAME="${ARUBA_USERNAME}" \
                                    -e ARUBA_PASSWORD="${ARUBA_PASSWORD}" \
                                    -e ARUBA_POLL_INTERVAL_SECONDS="${ARUBA_POLL_INTERVAL}" \
                                    -e ARUBA_AP_ZONE_MAP="${ARUBA_AP_ZONE_MAP}" \
                                    -e TESTING=false \
                                    -v app_data_${DEPLOY_ENV}:/app/augmented \
                                    -v app_ml_models_${DEPLOY_ENV}:/app/ml_models \
                                    -v app_logs_${DEPLOY_ENV}:/app/logs \
                                    ${BACKEND_IMAGE}:${IMAGE_TAG}

                                if ! docker ps --format '{{.Names}}' | grep -q "^${BACKEND_CONTAINER}$"; then
                                    echo "✗ Backend container failed to start"
                                    docker logs ${BACKEND_CONTAINER} 2>&1 || true
                                    exit 1
                                fi

                                echo "Copying GCP service account credentials..."
                                docker exec -u root ${BACKEND_CONTAINER} mkdir -p /app/credentials
                                docker cp ${GCP_SA_FILE} ${BACKEND_CONTAINER}:/app/credentials/service-account.json
                                docker exec -u root ${BACKEND_CONTAINER} chown appuser:appuser /app/credentials/service-account.json
                                echo "✓ Backend deployed"
                            '''
                        }
                        echo "Waiting for backend to be healthy..."
                        sh '''
                            sleep 10
                            for i in $(seq 1 12); do
                                if docker exec ${BACKEND_CONTAINER} \
                                    curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                                    echo "✓ Backend is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/12 — waiting..."
                                sleep 5
                            done
                            echo "✗ Backend health check failed after 60s"
                            docker logs ${BACKEND_CONTAINER} --tail=50
                            exit 1
                        '''
                    }
                }

                stage('Auth') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        sh '''
                            echo "Removing existing auth container..."
                            docker rm -f ${AUTH_CONTAINER} 2>/dev/null || true

                            echo "Starting auth service container..."
                            docker run -d \
                                --name ${AUTH_CONTAINER} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                -p ${AUTH_PORT}:4000 \
                                -e DATABASE_URL="${AUTH_DATABASE_URL}" \
                                -e BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET}" \
                                -e TRUSTED_ORIGINS="${AUTH_TRUSTED_ORIGINS}" \
                                -e AUTH_SERVICE_URL="${AUTH_SERVICE_URL}" \
                                -e COOKIE_DOMAIN="${AUTH_COOKIE_DOMAIN}" \
                                -e NPM_API_URL="${NPM_API_URL}" \
                                -e NPM_EMAIL="${NPM_EMAIL}" \
                                -e NPM_PASSWORD="${NPM_PASSWORD}" \
                                -e FAZRI_BASE_DOMAIN="${FAZRI_BASE_DOMAIN}" \
                                -e FAZRI_SERVER_IP="${FAZRI_SERVER_IP}" \
                                -e NODE_ENV=production \
                                -e PORT=4000 \
                                -e SENTRY_DSN="${AUTH_SENTRY_DSN}" \
                                -e SENTRY_ENVIRONMENT=${DEPLOY_ENV} \
                                -e SENTRY_TRACES_SAMPLE_RATE=0.1 \
                                -e SENTRY_ENABLED=true \
                                ${AUTH_IMAGE}:${IMAGE_TAG}

                            if ! docker ps --format '{{.Names}}' | grep -q "^${AUTH_CONTAINER}$"; then
                                echo "✗ Auth container failed to start"
                                docker logs ${AUTH_CONTAINER} 2>&1 || true
                                exit 1
                            fi

                            echo "✓ Auth service deployed"
                        '''
                        echo "Waiting for auth service to be healthy..."
                        sh '''
                            sleep 10
                            for i in $(seq 1 12); do
                                if docker exec ${AUTH_CONTAINER} \
                                    node -e "require('http').get('http://localhost:4000/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))" \
                                    > /dev/null 2>&1; then
                                    echo "✓ Auth service is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/12 — waiting..."
                                sleep 5
                            done
                            echo "✗ Auth service health check failed after 60s"
                            docker logs ${AUTH_CONTAINER} --tail=50
                            exit 1
                        '''
                    }
                }

                stage('DeepFace Server') {
                    when { expression { env.BUILD_DEEPFACE == 'true' } }
                    steps {
                        sh '''
                            echo "Removing existing DeepFace container..."
                            docker rm -f ${DEEPFACE_CONTAINER} 2>/dev/null || true

                            echo "Starting DeepFace server container..."
                            docker run -d \
                                --name ${DEEPFACE_CONTAINER} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                -e DEEPFACE_WEBHOOK_SECRET="${DEEPFACE_WEBHOOK_SECRET}" \
                                -e DEEPFACE_POSTGRES_URI="${DEEPFACE_POSTGRES_URI}" \
                                -e SENTRY_DSN="${DEEPFACE_SENTRY_DSN}" \
                                -e SENTRY_ENVIRONMENT=${DEPLOY_ENV} \
                                -e SENTRY_TRACES_SAMPLE_RATE=0.1 \
                                -e SENTRY_ENABLED=true \
                                -v deepface_models_${DEPLOY_ENV}:/app/models \
                                -v deepface_data_${DEPLOY_ENV}:/app/data \
                                ${DEEPFACE_IMAGE}:${IMAGE_TAG}

                            if ! docker ps --format '{{.Names}}' | grep -q "^${DEEPFACE_CONTAINER}$"; then
                                echo "✗ DeepFace container failed to start"
                                docker logs ${DEEPFACE_CONTAINER} 2>&1 || true
                                exit 1
                            fi

                            echo "✓ DeepFace server deployed"
                        '''
                        echo "Waiting for DeepFace server to be healthy..."
                        sh '''
                            sleep 10
                            for i in $(seq 1 18); do
                                if docker exec ${DEEPFACE_CONTAINER} \
                                    curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                                    echo "✓ DeepFace server is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/18 — waiting..."
                                sleep 5
                            done
                            echo "✗ DeepFace server health check failed after 90s"
                            docker logs ${DEEPFACE_CONTAINER} --tail=50
                            exit 1
                        '''
                    }
                }

                stage('go2rtc Relay') {
                    when { expression { env.BUILD_GO2RTC == 'true' && env.BRANCH_NAME != 'master' } }
                    steps {
                        sh '''
                            echo "Removing existing go2rtc container..."
                            docker stop ${GO2RTC_CONTAINER} 2>/dev/null || true
                            docker rm -f ${GO2RTC_CONTAINER} 2>/dev/null || true

                            echo "Starting go2rtc relay container..."
                            # Resolve the server public IP so go2rtc can advertise
                            # the correct ICE candidate to browsers (Docker internal
                            # IP 172.20.x.x is unreachable from the internet).
                            GO2RTC_HOST=$(curl -s --max-time 5 http://checkip.amazonaws.com \
                                || curl -s --max-time 5 https://ifconfig.me \
                                || ip route get 1.1.1.1 | awk '{print $7; exit}')
                            echo "go2rtc ICE host: ${GO2RTC_HOST}"
                            docker run -d \
                                --name ${GO2RTC_CONTAINER} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                -p 1984:1984 \
                                -p 8554:8554 \
                                -p 8555:8555/tcp \
                                -p 8555:8555/udp \
                                -e GO2RTC_HOST="${GO2RTC_HOST}" \
                                ${GO2RTC_IMAGE}:${IMAGE_TAG}

                            if ! docker ps --format '{{.Names}}' | grep -q "^${GO2RTC_CONTAINER}$"; then
                                echo "✗ go2rtc container failed to start"
                                docker logs ${GO2RTC_CONTAINER} 2>&1 || true
                                exit 1
                            fi

                            echo "✓ go2rtc relay deployed"
                        '''
                        echo "Waiting for go2rtc API to be healthy..."
                        sh '''
                            sleep 2
                            for i in $(seq 1 6); do
                                if docker exec ${GO2RTC_CONTAINER} \
                                    curl -sf http://localhost:1984/api > /dev/null 2>&1; then
                                    echo "✓ go2rtc API is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/6 — waiting..."
                                sleep 2
                            done
                            echo "✗ go2rtc health check failed after 12s"
                            docker logs ${GO2RTC_CONTAINER} --tail=30
                            exit 1
                        '''
                    }
                }

                stage('Simulators') {
                    when { expression { env.BUILD_BACKEND == 'true' && env.DEPLOY_ENV != 'production' } }
                    steps {
                        sh '''
                            echo "Removing existing simulator containers..."
                            docker rm -f fazri-hikvision-sim-${DEPLOY_ENV} 2>/dev/null || true
                            docker rm -f fazri-aruba-sim-${DEPLOY_ENV}     2>/dev/null || true

                            echo "Starting Hikvision simulator (movement coordinator)..."
                            docker run -d \
                                --name fazri-hikvision-sim-${DEPLOY_ENV} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                --no-healthcheck \
                                -p 9011:9001 \
                                -e HIKVISION_SIM_CONTINUOUS=1 \
                                -e HIKVISION_SIM_COORDINATOR=1 \
                                -e POSTGRES_SERVER="${SIM_POSTGRES_SERVER}" \
                                -e POSTGRES_USER="${SIM_POSTGRES_USER}" \
                                -e POSTGRES_PASSWORD="${SIM_POSTGRES_PASSWORD}" \
                                -e POSTGRES_DB="${SIM_POSTGRES_DB}" \
                                -e POSTGRES_PORT=5432 \
                                -e REDIS_HOST="${SIM_REDIS_HOST}" \
                                -e REDIS_PORT="${SIM_REDIS_PORT}" \
                                -e SIM_NUM_ENTITIES="${SIM_NUM_ENTITIES}" \
                                --entrypoint uvicorn \
                                ${BACKEND_IMAGE}:${IMAGE_TAG} \
                                simulators.hikvision_simulator:app --host 0.0.0.0 --port 9001

                            echo "Starting Aruba simulator..."
                            docker run -d \
                                --name fazri-aruba-sim-${DEPLOY_ENV} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                --no-healthcheck \
                                -p 9002:9002 \
                                -e REDIS_HOST="${SIM_REDIS_HOST}" \
                                -e REDIS_PORT="${SIM_REDIS_PORT}" \
                                --entrypoint uvicorn \
                                ${BACKEND_IMAGE}:${IMAGE_TAG} \
                                simulators.aruba_simulator:app --host 0.0.0.0 --port 9002

                            if ! docker ps --format '{{.Names}}' | grep -q "^fazri-hikvision-sim-${DEPLOY_ENV}$"; then
                                echo "✗ Hikvision simulator container failed to start"
                                docker logs fazri-hikvision-sim-${DEPLOY_ENV} 2>&1 || true
                                exit 1
                            fi
                            for i in $(seq 1 12); do
                                if docker exec fazri-hikvision-sim-${DEPLOY_ENV} \
                                    curl -sf http://localhost:9001/health > /dev/null 2>&1; then
                                    echo "✓ Hikvision simulator is healthy"
                                    break
                                fi
                                if [ $i -eq 12 ]; then
                                    echo "✗ Hikvision simulator health check failed after 60s"
                                    docker logs fazri-hikvision-sim-${DEPLOY_ENV} --tail=50
                                    exit 1
                                fi
                                echo "Hikvision sim attempt ${i}/12 — waiting..."
                                sleep 5
                            done

                            if ! docker ps --format '{{.Names}}' | grep -q "^fazri-aruba-sim-${DEPLOY_ENV}$"; then
                                echo "✗ Aruba simulator container failed to start"
                                docker logs fazri-aruba-sim-${DEPLOY_ENV} 2>&1 || true
                                exit 1
                            fi
                            for i in $(seq 1 12); do
                                if docker exec fazri-aruba-sim-${DEPLOY_ENV} \
                                    curl -sf http://localhost:9002/health > /dev/null 2>&1; then
                                    echo "✓ Aruba simulator is healthy"
                                    break
                                fi
                                if [ $i -eq 12 ]; then
                                    echo "✗ Aruba simulator health check failed after 60s"
                                    docker logs fazri-aruba-sim-${DEPLOY_ENV} --tail=50
                                    exit 1
                                fi
                                echo "Aruba sim attempt ${i}/12 — waiting..."
                                sleep 5
                            done
                        '''
                    }
                }

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Sentry Release') {
            parallel {

                stage('Sentry Release Backend') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        sh """
                            if command -v sentry-cli > /dev/null 2>&1; then
                                sentry-cli update 2>/dev/null || true
                            else
                                curl -sL https://sentry.io/get-cli/ | bash
                            fi

                            RELEASE_VERSION="fazri-analyzer-backend@${env.GIT_COMMIT}"

                            sentry-cli releases new "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-backend || true

                            sentry-cli releases set-commits "\$RELEASE_VERSION" --auto \
                                --org rayzrsole --project fazri-backend || true

                            sentry-cli releases deploys "\$RELEASE_VERSION" new \
                                --env ${DEPLOY_ENV} \
                                --org rayzrsole --project fazri-backend

                            sentry-cli releases finalize "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-backend

                            echo "✓ Sentry release (backend): \$RELEASE_VERSION (${DEPLOY_ENV})"
                        """
                    }
                }

                stage('Sentry Release Auth') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        sh """
                            if command -v sentry-cli > /dev/null 2>&1; then
                                sentry-cli update 2>/dev/null || true
                            else
                                curl -sL https://sentry.io/get-cli/ | bash
                            fi

                            RELEASE_VERSION="fazri-analyzer-auth@${env.GIT_COMMIT}"

                            sentry-cli releases new "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-auth || true

                            sentry-cli releases set-commits "\$RELEASE_VERSION" --auto \
                                --org rayzrsole --project fazri-auth || true

                            sentry-cli releases deploys "\$RELEASE_VERSION" new \
                                --env ${DEPLOY_ENV} \
                                --org rayzrsole --project fazri-auth

                            sentry-cli releases finalize "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-auth

                            echo "✓ Sentry release (auth): \$RELEASE_VERSION (${DEPLOY_ENV})"
                        """
                    }
                }

                stage('Sentry Release DeepFace') {
                    when { expression { env.BUILD_DEEPFACE == 'true' } }
                    steps {
                        sh """
                            if command -v sentry-cli > /dev/null 2>&1; then
                                sentry-cli update 2>/dev/null || true
                            else
                                curl -sL https://sentry.io/get-cli/ | bash
                            fi

                            RELEASE_VERSION="fazri-deepface-server@${env.GIT_COMMIT}"

                            sentry-cli releases new "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-deepface || true

                            sentry-cli releases set-commits "\$RELEASE_VERSION" --auto \
                                --org rayzrsole --project fazri-deepface || true

                            sentry-cli releases deploys "\$RELEASE_VERSION" new \
                                --env ${DEPLOY_ENV} \
                                --org rayzrsole --project fazri-deepface

                            sentry-cli releases finalize "\$RELEASE_VERSION" \
                                --org rayzrsole --project fazri-deepface

                            echo "✓ Sentry release (deepface): \$RELEASE_VERSION (${DEPLOY_ENV})"
                        """
                    }
                }

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Cleanup') {
            steps {
                sh '''
                    docker image prune -f || true
                    # Remove old tagged images ONLY for the current branch prefix.
                    # This prevents concurrent branch/PR jobs from deleting each other's images.
                    if [ "${BUILD_BACKEND}" = "true" ]; then
                        docker images ${BACKEND_IMAGE} --format "{{.Tag}}" \
                            | grep "^${SANITIZED_BRANCH}-" \
                            | grep -v "^${IMAGE_TAG}$" \
                            | xargs -r -I{} docker rmi ${BACKEND_IMAGE}:{} 2>/dev/null || true
                    fi
                    if [ "${BUILD_AUTH}" = "true" ]; then
                        docker images ${AUTH_IMAGE} --format "{{.Tag}}" \
                            | grep "^${SANITIZED_BRANCH}-" \
                            | grep -v "^${IMAGE_TAG}$" \
                            | xargs -r -I{} docker rmi ${AUTH_IMAGE}:{} 2>/dev/null || true
                    fi
                    if [ "${BUILD_DEEPFACE}" = "true" ]; then
                        docker images ${DEEPFACE_IMAGE} --format "{{.Tag}}" \
                            | grep "^${SANITIZED_BRANCH}-" \
                            | grep -v "^${IMAGE_TAG}$" \
                            | xargs -r -I{} docker rmi ${DEEPFACE_IMAGE}:{} 2>/dev/null || true
                    fi
                '''
            }
        }

    }

    post {
        success {
            script {
                def built = []
                if (env.BUILD_BACKEND  == 'true') built.add("backend (${env.BACKEND_CONTAINER})")
                if (env.BUILD_AUTH     == 'true') built.add("auth (${env.AUTH_CONTAINER})")
                if (env.BUILD_DEEPFACE == 'true') built.add("deepface (${env.DEEPFACE_CONTAINER})")
                echo '✓ Deployment successful! Built: ' + built.join(', ')
            }
        }
        failure {
            echo '✗ Deployment failed — check logs above'
            script {
                node('built-in') {
                    def isProd        = env.BRANCH_NAME == 'master'
                    def backendCtr    = env.BACKEND_CONTAINER  ?: (isProd ? 'fazri-api'           : 'fazri-api-staging')
                    def authCtr       = env.AUTH_CONTAINER     ?: (isProd ? 'fazri-auth'          : 'fazri-auth-staging')
                    def deepfaceCtr   = env.DEEPFACE_CONTAINER ?: (isProd ? 'deepface-server'     : 'deepface-server-staging')
                    sh "docker logs ${backendCtr}  --tail=30 2>&1 || true"
                    sh "docker logs ${authCtr}     --tail=30 2>&1 || true"
                    sh "docker logs ${deepfaceCtr} --tail=30 2>&1 || true"
                }
            }
        }
        always {
            echo 'Build #' + env.BUILD_NUMBER + ' on branch ' + env.GIT_BRANCH + ' — done.'
        }
    }
}

