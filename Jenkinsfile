pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        // ── Image / container names ───────────────────────────────────────────
        BACKEND_IMAGE_NAME  = 'fazri-analyzer-backend'
        AUTH_IMAGE_NAME     = 'fazri-analyzer-auth'
        CONTAINER_PORT      = '8000'
        AUTH_CONTAINER_PORT = '4000'
        NETWORK_NAME        = 'backend_fazri-network'
        DOCKER_BUILDKIT     = '1'
        IMAGE_TAG           = "${env.BUILD_NUMBER}"

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

        // ── Auth service credentials ──────────────────────────────────────────
        AUTH_DATABASE_URL      = credentials('fazri-auth-database-url')
        BETTER_AUTH_SECRET     = credentials('fazri-better-auth-secret')
        AUTH_TRUSTED_ORIGINS   = credentials('fazri-auth-trusted-origins')
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
                        env.DEPLOY_ENV            = 'production'
                        env.BACKEND_CONTAINER     = 'fazri-api'
                        env.AUTH_CONTAINER        = 'fazri-auth'
                        env.BACKEND_HOST_PORT     = '8000'
                        env.AUTH_HOST_PORT        = '4000'
                    } else {
                        env.DEPLOY_ENV            = 'staging'
                        env.BACKEND_CONTAINER     = 'fazri-api-staging'
                        env.AUTH_CONTAINER        = 'fazri-auth-staging'
                        env.BACKEND_HOST_PORT     = '8001'
                        env.AUTH_HOST_PORT        = '4001'
                    }
                    echo "Branch: ${env.BRANCH_NAME} → Deploy target: ${env.DEPLOY_ENV}"
                    echo "Backend container: ${env.BACKEND_CONTAINER} | Port: ${env.BACKEND_HOST_PORT}"
                    echo "Auth container:    ${env.AUTH_CONTAINER}    | Port: ${env.AUTH_HOST_PORT}"
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

                    env.BUILD_BACKEND = (changedFiles.contains('backend/') ||
                                         changedFiles.contains('Jenkinsfile')  ||
                                         isFirstRun) ? 'true' : 'false'

                    env.BUILD_AUTH    = (changedFiles.contains('auth/')    ||
                                         changedFiles.contains('Jenkinsfile')  ||
                                         isFirstRun) ? 'true' : 'false'

                    echo 'Changed files:\n' + changedFiles
                    echo 'Build backend: ' + env.BUILD_BACKEND
                    echo 'Build auth:    ' + env.BUILD_AUTH
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Build Images') {
            parallel {

                stage('Build Backend Image') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        echo "Building backend image..."
                        sh '''
                            docker build \
                                -f backend/Dockerfile \
                                --target production \
                                -t ${BACKEND_IMAGE_NAME}:${IMAGE_TAG} \
                                -t ${BACKEND_IMAGE_NAME}:latest \
                                backend/
                        '''
                    }
                }

                stage('Build Auth Image') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        echo "Building auth service image..."
                        sh '''
                            docker build \
                                -f auth/Dockerfile \
                                -t ${AUTH_IMAGE_NAME}:${IMAGE_TAG} \
                                -t ${AUTH_IMAGE_NAME}:latest \
                                auth/
                        '''
                    }
                }

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Deploy') {
            parallel {

                stage('Deploy Backend') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        script {
                            sh '''
                                echo "Removing existing backend container..."
                                docker stop ${BACKEND_CONTAINER} 2>/dev/null || true
                                docker rm -f ${BACKEND_CONTAINER} 2>/dev/null || true
                            '''

                            withCredentials([file(credentialsId: 'fazri-gcp-service-account', variable: 'GCP_SA_FILE')]) {
                                sh '''
                                    echo "Starting backend container..."

                                    docker run -d \
                                        --name ${BACKEND_CONTAINER} \
                                        --restart unless-stopped \
                                        --network ${NETWORK_NAME} \
                                        -p ${BACKEND_HOST_PORT}:${CONTAINER_PORT} \
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
                                        -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json \
                                        -e GITLAB_URL="${GITLAB_URL}" \
                                        -e GITLAB_TOKEN="${GITLAB_TOKEN}" \
                                        -e GITLAB_PROJECT_ID="${GITLAB_PROJECT_ID}" \
                                        -e AUTH_SERVICE_URL="${AUTH_SERVICE_URL}" \
                                        -e SENTRY_DSN="${SENTRY_DSN}" \
                                        -e SENTRY_ENVIRONMENT=${DEPLOY_ENV} \
                                        -e SENTRY_TRACES_SAMPLE_RATE=0.1 \
                                        -e SENTRY_ENABLED=true \
                                        -v app_data:/app/augmented \
                                        -v app_ml_models:/app/ml_models \
                                        -v app_logs:/app/logs \
                                        ${BACKEND_IMAGE_NAME}:${IMAGE_TAG}

                                    # Verify container started
                                    if ! docker ps --format '{{.Names}}' | grep -q "^${BACKEND_CONTAINER}$"; then
                                        echo "ERROR: Backend container failed to start"
                                        docker logs ${BACKEND_CONTAINER} 2>&1 || true
                                        exit 1
                                    fi

                                    echo "Copying GCP service account credentials..."
                                    docker exec -u root ${BACKEND_CONTAINER} mkdir -p /app/credentials
                                    docker cp ${GCP_SA_FILE} ${BACKEND_CONTAINER}:/app/credentials/service-account.json
                                    docker exec -u root ${BACKEND_CONTAINER} chown appuser:appuser /app/credentials/service-account.json
                                    echo "Backend deployed successfully"
                                '''
                            }
                        }
                    }
                }

                stage('Deploy Auth Service') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        sh '''
                            echo "Removing existing auth container..."
                            docker stop ${AUTH_CONTAINER} 2>/dev/null || true
                            docker rm -f ${AUTH_CONTAINER} 2>/dev/null || true

                            echo "Starting auth service container..."
                            docker run -d \
                                --name ${AUTH_CONTAINER} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                -p ${AUTH_HOST_PORT}:${AUTH_CONTAINER_PORT} \
                                -e DATABASE_URL="${AUTH_DATABASE_URL}" \
                                -e BETTER_AUTH_SECRET="${BETTER_AUTH_SECRET}" \
                                -e TRUSTED_ORIGINS="${AUTH_TRUSTED_ORIGINS}" \
                                -e PORT="${AUTH_CONTAINER_PORT}" \
                                ${AUTH_IMAGE_NAME}:${IMAGE_TAG}

                            # Verify container started
                            if ! docker ps --format '{{.Names}}' | grep -q "^${AUTH_CONTAINER}$"; then
                                echo "ERROR: Auth container failed to start"
                                docker logs ${AUTH_CONTAINER} 2>&1 || true
                                exit 1
                            fi

                            echo "Auth service deployed successfully"
                        '''
                    }
                }

            }
        }

        // ─────────────────────────────────────────────────────────────────────
        // Health-check both services before declaring success.
        // ─────────────────────────────────────────────────────────────────────
        stage('Health Checks') {
            parallel {

                stage('Backend Health') {
                    when { expression { env.BUILD_BACKEND == 'true' } }
                    steps {
                        sh '''
                            echo "Waiting for backend to be healthy..."
                            sleep 10
                            for i in $(seq 1 12); do
                                if docker exec ${BACKEND_CONTAINER} \
                                    curl -sf http://localhost:${CONTAINER_PORT}/health > /dev/null 2>&1; then
                                    echo "✓ Backend is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/12 — backend not ready yet..."
                                sleep 5
                            done
                            echo "✗ Backend health check failed after 60s"
                            docker logs ${BACKEND_CONTAINER} --tail=50
                            exit 1
                        '''
                    }
                }

                stage('Auth Service Health') {
                    when { expression { env.BUILD_AUTH == 'true' } }
                    steps {
                        sh '''
                            echo "Waiting for auth service to be healthy..."
                            sleep 10
                            for i in $(seq 1 12); do
                                if docker exec ${AUTH_CONTAINER} \
                                    node -e "require('http').get('http://localhost:${AUTH_CONTAINER_PORT}/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))" \
                                    > /dev/null 2>&1; then
                                    echo "✓ Auth service is healthy"
                                    exit 0
                                fi
                                echo "Attempt ${i}/12 — auth service not ready yet..."
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
        stage('Sentry Release Tracking') {
            when { expression { env.BUILD_BACKEND == 'true' } }
            steps {
                withCredentials([
                    string(credentialsId: 'fazri-sentry-auth-token', variable: 'SENTRY_AUTH_TOKEN')
                ]) {
                    sh """
                        echo "Creating Sentry release..."

                        if command -v sentry-cli > /dev/null 2>&1; then
                            sentry-cli update 2>/dev/null || true
                        else
                            curl -sL https://sentry.io/get-cli/ | bash
                        fi

                        RELEASE_VERSION="fazri-analyzer-backend@${env.GIT_COMMIT}"

                        sentry-cli releases new "\$RELEASE_VERSION" \
                            --org rayzrsole \
                            --project fazri-backend || true

                        sentry-cli releases set-commits "\$RELEASE_VERSION" --auto \
                            --org rayzrsole \
                            --project fazri-backend || true

                        sentry-cli releases deploys "\$RELEASE_VERSION" new \
                            --env ${DEPLOY_ENV} \
                            --org rayzrsole \
                            --project fazri-backend

                        sentry-cli releases finalize "\$RELEASE_VERSION" \
                            --org rayzrsole \
                            --project fazri-backend

                        echo "Sentry release created: \$RELEASE_VERSION (${DEPLOY_ENV})"
                    """
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────────
        stage('Cleanup') {
            steps {
                sh '''
                    echo "Pruning old backend images..."
                    docker images ${BACKEND_IMAGE_NAME} --format "{{.ID}} {{.Tag}}" | \
                        grep -v -E "^.* (${IMAGE_TAG}|latest)$" | \
                        awk '{print $1}' | xargs -r docker rmi -f 2>/dev/null || true

                    echo "Pruning old auth images..."
                    docker images ${AUTH_IMAGE_NAME} --format "{{.ID}} {{.Tag}}" | \
                        grep -v -E "^.* (${IMAGE_TAG}|latest)$" | \
                        awk '{print $1}' | xargs -r docker rmi -f 2>/dev/null || true

                    echo "Cleanup completed"
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
                echo """
                ====================================
                Deployment Successful!
                ====================================
                Built:   ${built.join(', ')}
                Build:   #${env.BUILD_NUMBER}
                Commit:  ${env.GIT_COMMIT}
                Env:     ${env.DEPLOY_ENV}
                ====================================
                """
            }
        }

        failure {
            echo "✗ Deployment failed — check logs above"
            sh '''
                if docker ps -a | grep -q ${BACKEND_CONTAINER:-fazri-api}; then
                    echo "=== Backend logs ==="
                    docker logs ${BACKEND_CONTAINER:-fazri-api} --tail=30 2>&1 || true
                fi
                if docker ps -a | grep -q ${AUTH_CONTAINER:-fazri-auth}; then
                    echo "=== Auth logs ==="
                    docker logs ${AUTH_CONTAINER:-fazri-auth} --tail=30 2>&1 || true
                fi
            '''
        }

        always {
            echo "Build #${env.BUILD_NUMBER} on branch ${env.GIT_BRANCH} — done."
        }
    }
}
