pipeline {
    agent any

    environment {
        IMAGE_NAME = 'fazri-analyzer-backend'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        CONTAINER_NAME = 'fazri-api'
        CONTAINER_PORT = '8000'
        HOST_PORT = '8000'
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
                        'fazri-gitlab-project-id'
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
                    // Ensure GCP credentials directory exists
                    sh "mkdir -p ${GCP_CREDS_DIR}"

                    // Write GCP service account file from Jenkins secret file credential
                    withCredentials([file(credentialsId: 'fazri-gcp-service-account', variable: 'GCP_SA_FILE')]) {
                        sh "cp \$GCP_SA_FILE ${GCP_CREDS_DIR}/service-account.json && chmod 644 ${GCP_CREDS_DIR}/service-account.json"
                    }

                    // Stop and remove old container
                    sh """
                        echo "Stopping old container..."
                        docker stop ${CONTAINER_NAME} 2>/dev/null || true
                        docker rm ${CONTAINER_NAME} 2>/dev/null || true
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
                        string(credentialsId: 'fazri-gitlab-project-id', variable: 'GITLAB_PROJECT_ID')
                    ]) {
                        sh """
                            echo "Starting new container..."

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
                                -v app_data:/app/augmented \
                                -v app_ml_models:/app/ml_models \
                                -v app_logs:/app/logs \
                                -v ${GCP_CREDS_DIR}/service-account.json:/app/credentials/service-account.json:ro \
                                ${IMAGE_NAME}:${IMAGE_TAG}

                            echo "Container started: ${CONTAINER_NAME}"
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
                            if curl -sf http://localhost:${HOST_PORT}/health > /dev/null 2>&1; then
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
