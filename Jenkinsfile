pipeline {
    agent any

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        CONTAINER_PORT = '8000'
        NETWORK_NAME = 'backend_fazri-network'
        GCP_CREDS_DIR = '/opt/fazri/credentials'
        DOCKER_BUILDKIT = '1'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    echo "Building commit: ${env.GIT_COMMIT}"
                }
            }
        }

        stage('Set Environment') {
            steps {
                script {
                    if (env.BRANCH_NAME == 'master') {
                        env.DEPLOY_ENV     = 'production'
                        env.IMAGE_NAME     = 'fazri-analyzer-backend'
                        env.CONTAINER_NAME = 'fazri-api'
                        env.HOST_PORT      = '8000'
                    } else {
                        env.DEPLOY_ENV     = 'staging'
                        env.IMAGE_NAME     = 'fazri-analyzer-backend-staging'
                        env.CONTAINER_NAME = 'fazri-api-staging'
                        env.HOST_PORT      = '8001'
                    }
                    echo "Branch: ${env.BRANCH_NAME} → Deploy target: ${env.DEPLOY_ENV}"
                    echo "Container: ${env.CONTAINER_NAME} | Port: ${env.HOST_PORT}"
                }
            }
        }

        stage('Detect Changes') {
            steps {
                script {
                    def backendChanged = true
                    try {
                        def changes = sh(
                            script: 'git diff --name-only HEAD~1 HEAD -- backend/ Jenkinsfile',
                            returnStdout: true
                        ).trim()
                        backendChanged = changes.length() > 0
                    } catch (Exception e) {
                        echo "Could not detect changes (first run?), proceeding with build"
                        backendChanged = true
                    }

                    if (!backendChanged) {
                        echo "No changes in backend/, skipping build"
                        currentBuild.result = 'NOT_BUILT'
                        error("No backend changes detected — skipping build")
                    }

                    echo "Backend changes detected, proceeding with build"
                }
            }
        }

        stage('Validate Credentials') {
            steps {
                script {
                    def missing = []
                    def requiredCreds = [
                        'fazri-postgres-server',
                        'fazri-postgres-user',
                        'fazri-postgres-password',
                        'fazri-postgres-db',
                        'fazri-postgres-port',
                        'fazri-neo4j-uri',
                        'fazri-neo4j-user',
                        'fazri-neo4j-password',
                        'fazri-redis-host',
                        'fazri-redis-port',
                        'fazri-secret-key',
                        'fazri-vertex-project-id',
                        'fazri-vertex-location',
                        'fazri-gitlab-url',
                        'fazri-gitlab-token',
                        'fazri-gitlab-project-id',
                        'fazri-nextauth-secret',
                        'fazri-sentry-backend-dsn',
                        'fazri-sentry-auth-token'
                    ]

                    for (credId in requiredCreds) {
                        try {
                            withCredentials([string(credentialsId: credId, variable: 'TEST_VAR')]) {
                                // credential exists
                            }
                        } catch (Exception e) {
                            missing.add(credId)
                        }
                    }

                    // Check secret file credential separately
                    try {
                        withCredentials([file(credentialsId: 'fazri-gcp-service-account', variable: 'TEST_FILE')]) {
                            // credential exists
                        }
                    } catch (Exception e) {
                        missing.add('fazri-gcp-service-account')
                    }

                    if (missing.size() > 0) {
                        echo "Missing Jenkins credentials:"
                        missing.each { echo "  - ${it}" }
                        error("${missing.size()} credential(s) missing. Add them in Jenkins > Manage Credentials before deploying.")
                    }

                    echo "All ${requiredCreds.size() + 1} credentials validated"
                }
            }
        }

        stage('Build Image') {
            steps {
                script {
                    sh """
                        echo "Building backend Docker image..."

                        docker build \
                            -f backend/Dockerfile \
                            --target production \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            backend/

                        echo "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
                    """
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    // Stop and remove old container with better error handling
                    sh """
                        echo "Checking for existing container..."

                        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                            echo "Found existing container ${CONTAINER_NAME}, removing it..."

                            # Stop the container (force stop if necessary)
                            echo "Stopping container..."
                            docker stop ${CONTAINER_NAME} || docker kill ${CONTAINER_NAME} || true

                            # Wait for container to fully stop
                            sleep 2

                            # Remove the container
                            echo "Removing container..."
                            docker rm -f ${CONTAINER_NAME} || true

                            # Verify removal
                            sleep 1
                            if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                                echo "ERROR: Container ${CONTAINER_NAME} still exists after removal attempt"
                                docker ps -a | grep ${CONTAINER_NAME} || true
                                exit 1
                            fi

                            echo "Container successfully removed"
                        else
                            echo "No existing container found, proceeding with fresh deployment"
                        fi
                    """

                    // Start new container with all env vars from Jenkins credentials
                    withCredentials([
                        // PostgreSQL
                        string(credentialsId: 'fazri-postgres-server', variable: 'POSTGRES_SERVER'),
                        string(credentialsId: 'fazri-postgres-user', variable: 'POSTGRES_USER'),
                        string(credentialsId: 'fazri-postgres-password', variable: 'POSTGRES_PASSWORD'),
                        string(credentialsId: 'fazri-postgres-db', variable: 'POSTGRES_DB'),
                        string(credentialsId: 'fazri-postgres-port', variable: 'POSTGRES_PORT'),
                        // Neo4j
                        string(credentialsId: 'fazri-neo4j-uri', variable: 'NEO4J_URI'),
                        string(credentialsId: 'fazri-neo4j-user', variable: 'NEO4J_USER'),
                        string(credentialsId: 'fazri-neo4j-password', variable: 'NEO4J_PASSWORD'),
                        // Redis
                        string(credentialsId: 'fazri-redis-host', variable: 'REDIS_HOST'),
                        string(credentialsId: 'fazri-redis-port', variable: 'REDIS_PORT'),
                        // App secrets
                        string(credentialsId: 'fazri-secret-key', variable: 'SECRET_KEY'),
                        // Vertex AI
                        string(credentialsId: 'fazri-vertex-project-id', variable: 'VERTEX_PROJECT_ID'),
                        string(credentialsId: 'fazri-vertex-location', variable: 'VERTEX_LOCATION'),
                        // GitLab integration
                        string(credentialsId: 'fazri-gitlab-url', variable: 'GITLAB_URL'),
                        string(credentialsId: 'fazri-gitlab-token', variable: 'GITLAB_TOKEN'),
                        string(credentialsId: 'fazri-gitlab-project-id', variable: 'GITLAB_PROJECT_ID'),
                        // NextAuth / JWT
                        string(credentialsId: 'fazri-nextauth-secret', variable: 'NEXTAUTH_SECRET'),
                        // Sentry
                        string(credentialsId: 'fazri-sentry-backend-dsn', variable: 'SENTRY_DSN'),
                        string(credentialsId: 'fazri-sentry-auth-token', variable: 'SENTRY_AUTH_TOKEN')
                    ]) {
                        sh """
                            echo "Starting new container..."

                            # Double-check no container exists before running
                            if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                                echo "ERROR: Container ${CONTAINER_NAME} still exists!"
                                docker ps -a | grep ${CONTAINER_NAME}
                                exit 1
                            fi

                            # Start the new container
                            docker run -d \
                                --name ${CONTAINER_NAME} \
                                --restart unless-stopped \
                                --network ${NETWORK_NAME} \
                                -p ${HOST_PORT}:${CONTAINER_PORT} \
                                -e POSTGRES_SERVER=\$POSTGRES_SERVER \
                                -e POSTGRES_USER=\$POSTGRES_USER \
                                -e POSTGRES_PASSWORD=\$POSTGRES_PASSWORD \
                                -e POSTGRES_DB=\$POSTGRES_DB \
                                -e POSTGRES_PORT=\$POSTGRES_PORT \
                                -e NEO4J_URI=\$NEO4J_URI \
                                -e NEO4J_USER=\$NEO4J_USER \
                                -e NEO4J_PASSWORD=\$NEO4J_PASSWORD \
                                -e REDIS_HOST=\$REDIS_HOST \
                                -e REDIS_PORT=\$REDIS_PORT \
                                -e SECRET_KEY=\$SECRET_KEY \
                                -e USE_VERTEX_AI=true \
                                -e VERTEX_PROJECT_ID=\$VERTEX_PROJECT_ID \
                                -e VERTEX_LOCATION=\$VERTEX_LOCATION \
                                -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json \
                                -e GITLAB_URL=\$GITLAB_URL \
                                -e GITLAB_TOKEN=\$GITLAB_TOKEN \
                                -e GITLAB_PROJECT_ID=\$GITLAB_PROJECT_ID \
                                -e NEXTAUTH_SECRET=\$NEXTAUTH_SECRET \
                                -e SENTRY_DSN=\$SENTRY_DSN \
                                -e SENTRY_ENVIRONMENT=${DEPLOY_ENV} \
                                -e SENTRY_TRACES_SAMPLE_RATE=0.1 \
                                -e SENTRY_ENABLED=true \
                                -v app_data:/app/augmented \
                                -v app_ml_models:/app/ml_models \
                                -v app_logs:/app/logs \
                                ${IMAGE_NAME}:${IMAGE_TAG}

                            # Verify container started
                            if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                                echo "ERROR: Container failed to start"
                                docker ps -a | grep ${CONTAINER_NAME} || echo "Container not found"
                                docker logs ${CONTAINER_NAME} 2>&1 || true
                                exit 1
                            fi

                            echo "Container started successfully: ${CONTAINER_NAME}"

                            # Wait a bit for container to initialize
                            echo "Waiting for container to initialize..."
                            sleep 3

                            # Check if container is still running after initial startup
                            if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                                echo "ERROR: Container started but then immediately crashed"
                                echo "Container status:"
                                docker ps -a | grep ${CONTAINER_NAME}
                                echo ""
                                echo "Container logs:"
                                docker logs ${CONTAINER_NAME} 2>&1
                                exit 1
                            fi
                        """
                    }

                    // Copy GCP service account into running container
                    withCredentials([file(credentialsId: 'fazri-gcp-service-account', variable: 'GCP_SA_FILE')]) {
                        sh """
                            echo "Copying GCP service account credentials..."

                            # Create credentials directory
                            if ! docker exec -u root ${CONTAINER_NAME} mkdir -p /app/credentials; then
                                echo "ERROR: Failed to create credentials directory"
                                echo "Container may have crashed. Checking status:"
                                docker ps -a | grep ${CONTAINER_NAME}
                                echo "Container logs:"
                                docker logs ${CONTAINER_NAME} 2>&1
                                exit 1
                            fi

                            # Copy credentials file
                            if ! docker cp \$GCP_SA_FILE ${CONTAINER_NAME}:/app/credentials/service-account.json; then
                                echo "ERROR: Failed to copy credentials file"
                                exit 1
                            fi

                            # Set ownership
                            if ! docker exec -u root ${CONTAINER_NAME} chown appuser:appuser /app/credentials/service-account.json; then
                                echo "ERROR: Failed to set credentials file ownership"
                                exit 1
                            fi

                            echo "Credentials copied successfully"
                        """
                    }
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    sh """
                        echo "Running health checks..."

                        # Wait for container to initialize
                        sleep 10

                        # Check if container is running
                        if ! docker ps | grep -q ${CONTAINER_NAME}; then
                            echo "Container failed to start"
                            docker logs ${CONTAINER_NAME}
                            exit 1
                        fi

                        # Poll health endpoint
                        max_attempts=12
                        attempt=0

                        while [ \$attempt -lt \$max_attempts ]; do
                            if docker exec ${CONTAINER_NAME} curl -sf http://localhost:${CONTAINER_PORT}/health > /dev/null 2>&1; then
                                echo "Application is healthy!"
                                docker ps | grep ${CONTAINER_NAME}
                                exit 0
                            fi
                            attempt=\$((attempt + 1))
                            echo "Attempt \$attempt/\$max_attempts: Application not ready yet..."
                            sleep 5
                        done

                        echo "Health check failed after \$max_attempts attempts"
                        echo "Container logs:"
                        docker logs ${CONTAINER_NAME}
                        exit 1
                    """
                }
            }
        }

        stage('Sentry Release Tracking') {
            steps {
                script {
                    withCredentials([
                        string(credentialsId: 'fazri-sentry-auth-token', variable: 'SENTRY_AUTH_TOKEN')
                    ]) {
                        sh """
                            echo "Creating Sentry release..."

                            # Install sentry-cli if not already installed
                            if ! command -v sentry-cli &> /dev/null; then
                                echo "Installing sentry-cli..."
                                curl -sL https://sentry.io/get-cli/ | bash
                            fi

                            # Set release version (using git commit SHA)
                            RELEASE_VERSION="fazri-analyzer-backend@${env.GIT_COMMIT}"

                            # Create release in Sentry
                            sentry-cli releases new "\$RELEASE_VERSION" \
                                --auth-token \$SENTRY_AUTH_TOKEN \
                                --org fazri-analyzer \
                                --project fazri-analyzer-backend || echo "Release already exists"

                            # Associate commits with the release
                            sentry-cli releases set-commits "\$RELEASE_VERSION" --auto \
                                --auth-token \$SENTRY_AUTH_TOKEN \
                                --org fazri-analyzer \
                                --project fazri-analyzer-backend || true

                            # Mark release as deployed
                            sentry-cli releases deploys "\$RELEASE_VERSION" new \
                                --env ${DEPLOY_ENV} \
                                --auth-token \$SENTRY_AUTH_TOKEN \
                                --org fazri-analyzer \
                                --project fazri-analyzer-backend

                            # Finalize the release
                            sentry-cli releases finalize "\$RELEASE_VERSION" \
                                --auth-token \$SENTRY_AUTH_TOKEN \
                                --org fazri-analyzer \
                                --project fazri-analyzer-backend

                            echo "Sentry release created: \$RELEASE_VERSION"
                            echo "Environment: ${DEPLOY_ENV}"
                        """
                    }
                }
            }
        }

        stage('Cleanup') {
            steps {
                script {
                    sh """
                        echo "Pruning old images..."

                        # Remove old images, keep current and latest
                        docker images ${IMAGE_NAME} --format "{{.ID}} {{.Tag}}" | \
                            grep -v -E "^.* (${IMAGE_TAG}|latest)\$" | \
                            awk '{print \$1}' | xargs -r docker rmi -f 2>/dev/null || true

                        echo "Cleanup completed"
                    """
                }
            }
        }
    }

    post {
        success {
            script {
                echo """
                ====================================
                Deployment Successful!
                ====================================
                Image: ${IMAGE_NAME}:${IMAGE_TAG}
                Container: ${CONTAINER_NAME}
                URL: http://localhost:${HOST_PORT}
                Build: #${env.BUILD_NUMBER}
                Commit: ${env.GIT_COMMIT}
                Environment: ${DEPLOY_ENV}
                Sentry: Enabled (${DEPLOY_ENV})
                ====================================
                """
            }
        }

        failure {
            script {
                echo """
                ====================================
                Deployment Failed
                ====================================
                Build: #${env.BUILD_NUMBER}
                ====================================
                """

                sh """
                    if docker ps -a | grep -q ${CONTAINER_NAME}; then
                        echo "Container logs:"
                        docker logs ${CONTAINER_NAME} 2>&1 || echo "Could not retrieve container logs"
                    else
                        echo "Container was not created"
                    fi
                """
            }
        }
    }
}
