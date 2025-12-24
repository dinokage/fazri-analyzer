pipeline {
    agent any
    
    environment {
        // Docker configuration
        IMAGE_NAME = 'fazri-analyzer-frontend'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        CONTAINER_NAME = "${IMAGE_NAME}-prod"
        DOCKERFILE_PATH = 'Dockerfile.prod'
        
        // Container configuration
        CONTAINER_PORT = '3000'
        HOST_PORT = '3000'
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
        
        stage('Load Environment Variables') {
            steps {
                script {
                    // Try to load credentials, if not found, use defaults or fail gracefully
                    try {
                        withCredentials([
                            string(credentialsId: 'NEXT_PUBLIC_FASTAPI_BASE_URL', variable: 'FASTAPI_URL'),
                            string(credentialsId: 'NEXT_PUBLIC_CDN_URL', variable: 'CDN_URL')
                        ]) {
                            env.NEXT_PUBLIC_FASTAPI_BASE_URL = FASTAPI_URL
                            env.NEXT_PUBLIC_CDN_URL = CDN_URL
                        }
                    } catch (Exception e) {
                        echo "⚠️  Warning: Credentials not found. Using default values."
                        echo "Please add credentials in Jenkins: Manage Jenkins > Credentials"
                        echo "Required credential IDs:"
                        echo "  - NEXT_PUBLIC_FASTAPI_BASE_URL"
                        echo "  - NEXT_PUBLIC_CDN_URL"
                        
                        // Set default values or fail
                        env.NEXT_PUBLIC_FASTAPI_BASE_URL = 'http://localhost:8000'
                        env.NEXT_PUBLIC_CDN_URL = 'http://localhost:3000'
                        
                        // Uncomment to fail if credentials are missing:
                        // error("Required credentials not found: ${e.message}")
                    }
                    
                    echo "Using FASTAPI_BASE_URL: ${env.NEXT_PUBLIC_FASTAPI_BASE_URL}"
                    echo "Using CDN_URL: ${env.NEXT_PUBLIC_CDN_URL}"
                }
            }
        }
        
        stage('Cleanup Old Container') {
            steps {
                script {
                    sh """
                        echo "Cleaning up old containers and images..."
                        
                        # Stop and remove existing container if it exists
                        docker stop ${CONTAINER_NAME} 2>/dev/null || true
                        docker rm ${CONTAINER_NAME} 2>/dev/null || true
                        
                        # Remove old images (keep last 3)
                        docker images ${IMAGE_NAME} --format "{{.ID}} {{.CreatedAt}}" | \
                        tail -n +4 | awk '{print \$1}' | xargs -r docker rmi -f 2>/dev/null || true
                        
                        echo "Cleanup completed"
                    """
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    sh """
                        echo "Building Docker image..."
                        
                        docker build \
                            -f ${DOCKERFILE_PATH} \
                            --build-arg NEXT_PUBLIC_FASTAPI_BASE_URL=${env.NEXT_PUBLIC_FASTAPI_BASE_URL} \
                            --build-arg NEXT_PUBLIC_CDN_URL=${env.NEXT_PUBLIC_CDN_URL} \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            .
                        
                        echo "Docker image built successfully"
                    """
                }
            }
        }
        
        stage('Run Container') {
            steps {
                script {
                    sh """
                        echo "Starting container..."
                        
                        docker run -d \
                            --name ${CONTAINER_NAME} \
                            --restart unless-stopped \
                            -p ${HOST_PORT}:${CONTAINER_PORT} \
                            ${IMAGE_NAME}:${IMAGE_TAG}
                        
                        echo "Container started: ${CONTAINER_NAME}"
                    """
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    sh """
                        echo "Running health checks..."
                        
                        # Wait for container to start
                        sleep 10
                        
                        # Check if container is running
                        if ! docker ps | grep -q ${CONTAINER_NAME}; then
                            echo "❌ Container failed to start"
                            docker logs ${CONTAINER_NAME}
                            exit 1
                        fi
                        
                        # Check if application responds
                        max_attempts=12
                        attempt=0
                        
                        while [ \$attempt -lt \$max_attempts ]; do
                            if curl -f http://10.69.5.100:${HOST_PORT} > /dev/null 2>&1; then
                                echo "✅ Application is healthy!"
                                docker ps | grep ${CONTAINER_NAME}
                                exit 0
                            fi
                            attempt=\$((attempt + 1))
                            echo "⏳ Attempt \$attempt/\$max_attempts: Application not ready yet..."
                            sleep 5
                        done
                        
                        echo "❌ Health check failed after \$max_attempts attempts"
                        echo "Container logs:"
                        docker logs ${CONTAINER_NAME}
                        exit 1
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
                ✅ Deployment Successful!
                ====================================
                Image: ${IMAGE_NAME}:${IMAGE_TAG}
                Container: ${CONTAINER_NAME}
                URL: http://10.69.5.100:${HOST_PORT}
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
                ❌ Deployment Failed
                ====================================
                Build: #${env.BUILD_NUMBER}
                ====================================
                """
                
                // Only try to get logs if container might exist
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
        
        always {
            cleanWs(
                deleteDirs: true,
                patterns: [
                    [pattern: 'node_modules', type: 'INCLUDE'],
                    [pattern: '.next', type: 'INCLUDE']
                ]
            )
        }
    }
}
