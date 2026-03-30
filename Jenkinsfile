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

        // ── Auth service credentials ──────────────────────────────────────────
        AUTH_DATABASE_URL    = credentials('fazri-auth-database-url')
        BETTER_AUTH_SECRET   = credentials('fazri-better-auth-secret')
        AUTH_TRUSTED_ORIGINS = credentials('fazri-auth-trusted-origins')
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
                        env.DEPLOY_ENV        = 'production'
                        env.BACKEND_CONTAINER = 'fazri-api'
                        env.AUTH_CONTAINER    = 'fazri-auth'
                        env.BACKEND_PORT      = '8000'
                        env.AUTH_PORT         = '4002'
                    } else {
                        env.DEPLOY_ENV        = 'staging'
                        env.BACKEND_CONTAINER = 'fazri-api-staging'
                        env.AUTH_CONTAINER    = 'fazri-auth-staging'
                        env.BACKEND_PORT      = '8001'
                        env.AUTH_PORT         = '4003'
                    }
                    def sanitizedBranch = env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '-').toLowerCase()
                    def shortSha        = env.GIT_COMMIT?.take(7) ?: 'unknown'
                    env.IMAGE_TAG       = "${sanitizedBranch}-${shortSha}"

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
                    def baseline
                    def isFirstRun

                    if (env.GIT_PREVIOUS_SUCCESSFUL_COMMIT) {
                        baseline   = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT
                        isFirstRun = false
                    } else {
                        def mergeBase = sh(
                            script: "git merge-base origin/master HEAD 2>/dev/null || echo ''",
                            returnStdout: true
                        ).trim()
                        if (mergeBase) {
                            baseline   = mergeBase
                            isFirstRun = false
                        } else {
                            baseline   = null
                            isFirstRun = true
                        }
                    }

                    def changedFiles = isFirstRun ? 'all' : sh(
                        script: "git diff --name-only ${baseline} HEAD",
                        returnStdout: true
                    ).trim()

                    env.BUILD_BACKEND = (changedFiles.contains('backend/')    ||
                                         changedFiles.contains('Jenkinsfile') ||
                                         isFirstRun) ? 'true' : 'false'

                    env.BUILD_AUTH    = (changedFiles.contains('auth/')       ||
                                         changedFiles.contains('Jenkinsfile') ||
                                         isFirstRun) ? 'true' : 'false'

                    // Use concatenation instead of GString interpolation to avoid
                    // Jenkins masking these values when a credential shares the same string.
                    echo 'Changed files:\n' + changedFiles
                    echo 'Build backend: '  + env.BUILD_BACKEND
                    echo 'Build auth:    '  + env.BUILD_AUTH
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
                            docker build -f backend/Dockerfile --target production \
                                -t ${BACKEND_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${BACKEND_IMAGE}:latest" || echo "") \
                                backend/
                        '''
                    }
                }

                stage('Build Auth Image') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        echo "Building auth service image (live container still up)..."
                        sh '''
                            docker build -f auth/Dockerfile \
                                -t ${AUTH_IMAGE}:${IMAGE_TAG} \
                                $([ "${BRANCH_NAME}" = "master" ] && echo "-t ${AUTH_IMAGE}:latest" || echo "") \
                                auth/
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
                                -e PORT=4000 \
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

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Sentry Release') {
            when { expression { env.BUILD_BACKEND == 'true' || env.BUILD_AUTH == 'true' } }
            steps {
                sh """
                    if command -v sentry-cli > /dev/null 2>&1; then
                        sentry-cli update 2>/dev/null || true
                    else
                        curl -sL https://sentry.io/get-cli/ | bash
                    fi
                """
                script {
                    if (env.BUILD_BACKEND == 'true') {
                        sh """
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
                    if (env.BUILD_AUTH == 'true') {
                        sh """
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
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Cleanup') {
            steps {
                sh '''
                    docker image prune -f || true
                    # Remove old tagged images for built services, keeping only the current tag and latest
                    if [ "${BUILD_BACKEND}" = "true" ]; then
                        docker images ${BACKEND_IMAGE} --format "{{.Tag}}" \
                            | grep -v "^${IMAGE_TAG}$" | grep -v "^latest$" \
                            | xargs -r -I{} docker rmi ${BACKEND_IMAGE}:{} 2>/dev/null || true
                    fi
                    if [ "${BUILD_AUTH}" = "true" ]; then
                        docker images ${AUTH_IMAGE} --format "{{.Tag}}" \
                            | grep -v "^${IMAGE_TAG}$" | grep -v "^latest$" \
                            | xargs -r -I{} docker rmi ${AUTH_IMAGE}:{} 2>/dev/null || true
                    fi
                '''
            }
        }

    }

    post {
        success {
            script {
                def built = []
                if (env.BUILD_BACKEND == 'true') built.add("backend (${env.BACKEND_CONTAINER})")
                if (env.BUILD_AUTH    == 'true') built.add("auth (${env.AUTH_CONTAINER})")
                echo '✓ Deployment successful! Built: ' + built.join(', ')
            }
        }
        failure {
            echo '✗ Deployment failed — check logs above'
            script {
                node('built-in') {
                    def isProd      = env.BRANCH_NAME == 'master'
                    def backendCtr  = env.BACKEND_CONTAINER ?: (isProd ? 'fazri-api'  : 'fazri-api-staging')
                    def authCtr     = env.AUTH_CONTAINER    ?: (isProd ? 'fazri-auth' : 'fazri-auth-staging')
                    sh "docker logs ${backendCtr} --tail=30 2>&1 || true"
                    sh "docker logs ${authCtr}    --tail=30 2>&1 || true"
                }
            }
        }
        always {
            echo 'Build #' + env.BUILD_NUMBER + ' on branch ' + env.GIT_BRANCH + ' — done.'
        }
    }
}
